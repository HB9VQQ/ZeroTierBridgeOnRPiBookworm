# ZeroTier Bridge Troubleshooting Guide

**Version:** 1.5.1 | **Author:** Roland HB9VQQ

## Diagnostic Overview

When troubleshooting bridge issues, check in this order:

1. Bridge configuration (brctl)
2. IP address assignment
3. ZeroTier connectivity
4. Routing configuration
5. ZeroTier Portal settings

## Issue 1: ZeroTier Interface Not in Bridge

### Symptoms
```bash
$ brctl show
bridge name     bridge id               STP enabled     interfaces
br0             8000.xxxxxxxxxxxx       no              eth0
```
ZeroTier interface (zt*) is missing from the bridge.

### Diagnosis

**Check if ZeroTier is running:**
```bash
sudo systemctl status zerotier-one
sudo zerotier-cli listnetworks
```

**Check auto-start log:**
```bash
cat /tmp/bridge-setup.log
```

**Check cron job:**
```bash
sudo crontab -l | grep brctl
```

Expected output:
```
@reboot sleep 45 && /usr/sbin/brctl addif br0 ztxxxxxxxx >> /tmp/bridge-setup.log 2>&1
```

### Solutions

**Immediate fix (manual):**
```bash
# Find ZeroTier interface name
ip link show | grep zt

# Add to bridge (replace ztxxxxxxxx with actual name)
sudo brctl addif br0 ztc7e0d196
```

**Permanent fix if cron job is missing:**
```bash
# Get ZeroTier interface name
ZT_IF=$(ip link show | grep zt | awk '{print $2}' | tr -d ':')

# Add cron job
(sudo crontab -l 2>/dev/null; echo "@reboot sleep 45 && /usr/sbin/brctl addif br0 $ZT_IF >> /tmp/bridge-setup.log 2>&1") | sudo crontab -
```

**Fix if cron job exists but doesn't work:**
```bash
# Check if brctl path is correct
which brctl

# Should output: /usr/sbin/brctl

# Check cron job uses full path
sudo crontab -l | grep brctl

# If it doesn't use /usr/sbin/brctl, update it
sudo crontab -e
# Change: @reboot sleep 45 && brctl addif br0 ztxxxxxxxx
# To:     @reboot sleep 45 && /usr/sbin/brctl addif br0 ztxxxxxxxx >> /tmp/bridge-setup.log 2>&1
```

## Issue 2: dhcpcd Interference

### Symptoms
- Bridge loses IP after reboot
- Physical interface (eth0) gets an IP instead of bridge
- Intermittent connectivity issues

### Diagnosis

**Check dhcpcd configuration:**
```bash
cat /etc/dhcpcd.conf | grep -A2 denyinterfaces
```

Should show:
```
denyinterfaces br0
denyinterfaces eth0  # (or your physical interface)
```

**Check if dhcpcd is interfering:**
```bash
systemctl status dhcpcd
journalctl -u dhcpcd | tail -20
```

### Solutions

**Fix dhcpcd configuration:**
```bash
sudo nano /etc/dhcpcd.conf
```

Add at the top of the file:
```
# Don't manage bridge interfaces
denyinterfaces br0
denyinterfaces eth0
```

**Restart dhcpcd:**
```bash
sudo systemctl restart dhcpcd
sudo systemctl restart networking
```

**If problem persists, disable dhcpcd entirely:**
```bash
sudo systemctl disable dhcpcd
sudo systemctl stop dhcpcd
sudo reboot
```

## Issue 3: No IP Address on Bridge

### Symptoms
```bash
$ ip addr show br0
3: br0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    link/ether xx:xx:xx:xx:xx:xx
    # No inet address listed
```

### Diagnosis

**Check interfaces configuration:**
```bash
cat /etc/network/interfaces.d/bridge
```

Should contain:
```
auto br0
iface br0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    bridge_ports eth0
    bridge_stp off
    bridge_fd 0
    bridge_maxwait 0
```

**Check if configuration is loaded:**
```bash
sudo systemctl status networking
journalctl -u networking | tail -20
```

### Solutions

**Recreate bridge configuration:**
```bash
sudo nano /etc/network/interfaces.d/bridge
```

Add the configuration shown above (adjust IPs for your network).

**Bring up the interface:**
```bash
sudo ifdown br0 2>/dev/null
sudo ifup br0
```

**If that doesn't work, reboot:**
```bash
sudo reboot
```

## Issue 4: Physical Interface Has IP Instead of Bridge

### Symptoms
```bash
$ ip addr show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 192.168.1.xxx/24 brd 192.168.1.255 scope global eth0
```

The physical interface should NOT have an IP address.

### Diagnosis

This is usually caused by dhcpcd or NetworkManager managing the interface.

**Check what's managing the interface:**
```bash
# Check dhcpcd
systemctl status dhcpcd

# Check NetworkManager
systemctl status NetworkManager
```

### Solutions

**Remove IP from physical interface:**
```bash
sudo ip addr flush dev eth0
```

**Fix dhcpcd (see Issue 2)**

**Prevent NetworkManager from managing it:**
```bash
sudo nano /etc/NetworkManager/NetworkManager.conf
```

Add:
```
[keyfile]
unmanaged-devices=interface-name:eth0
```

Then:
```bash
sudo systemctl restart NetworkManager
```

## Issue 5: Can't Reach LAN from ZeroTier

### Symptoms
- ZeroTier network shows as connected
- Can ping bridge IP from ZeroTier client
- Cannot ping LAN devices or gateway

### Diagnosis

**Check routing on bridge:**
```bash
ip route
```

Should show:
```
default via 192.168.1.1 dev br0
192.168.1.0/24 dev br0 proto kernel scope link src 192.168.1.100
```

**Check ZeroTier managed routes:**
```bash
sudo zerotier-cli listnetworks
```

allowManaged should be 0.

**Check from ZeroTier client:**
```bash
# On the client device
ip route | grep 192.168.1
traceroute 192.168.1.1
```

### Solutions

**Verify ZeroTier Portal configuration:**

1. Go to https://my.zerotier.com
2. Navigate to your network and scroll to Members
3. Click on your bridge device (wrench icon to edit)
4. **Device Settings:**
   - ✓ Allow Ethernet Bridging (checked)
   - ✓ Do Not Auto-Assign IPs (checked)
   - ✓ Authorized (Auth checked)
   - ✗ **NO Managed IP assigned** (must be empty)
5. **Network Settings** (at top of page):
   - Managed Route configured: `192.168.1.0/24` via `192.168.1.100`

**Set allowManaged=0:**
```bash
# Get network ID
sudo zerotier-cli listnetworks

# Set allowManaged (replace NETWORK_ID)
sudo zerotier-cli set NETWORK_ID allowManaged=0
```

**Check IP forwarding (if needed):**
```bash
# Check if IP forwarding is enabled
cat /proc/sys/net/ipv4/ip_forward

# Should be 1, if not:
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Make permanent
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Issue 6: ZeroTier Network Shows "Access Denied"

### Symptoms
```bash
$ sudo zerotier-cli listnetworks
200 listnetworks <nwid> <name> <mac> <status> <type> <dev> <ZT assigned ips>
ACCESS_DENIED
```

### Solutions

**Authorize in ZeroTier Portal:**
1. Go to https://my.zerotier.com
2. Navigate to your network
3. Scroll to Members section
4. Find your device (Node ID: `sudo zerotier-cli info`)
5. Check the "Auth" checkbox

**Wait a moment, then check:**
```bash
sudo zerotier-cli listnetworks
```

Should now show "OK" status.

## Issue 7: Connection Lost After Some Time

### Symptoms
- Bridge works initially after reboot
- Connection lost after minutes/hours
- Bridge interface still shows in `brctl show`

### Diagnosis

**Check if dhcpcd is re-claiming interfaces:**
```bash
journalctl -u dhcpcd --since "1 hour ago"
```

**Check for IP conflicts:**
```bash
# On bridge
ip addr show
arp -a
```

### Solutions

**Ensure dhcpcd stays disabled for bridge interfaces:**
```bash
# Verify configuration
cat /etc/dhcpcd.conf | grep -B2 -A2 denyinterfaces

# If not present, add:
sudo nano /etc/dhcpcd.conf
```

Add at the top:
```
denyinterfaces br0
denyinterfaces eth0
denyinterfaces zt*
```

**Restart services:**
```bash
sudo systemctl restart dhcpcd
sudo systemctl restart networking
```

**Check for IP conflicts on LAN:**
Ensure your bridge IP (e.g., 192.168.1.100) is:
- Static (not in DHCP range)
- Not assigned to another device
- Reserved in your router's DHCP settings

## Issue 8: Bridge Works But Very Slow

### Symptoms
- Connection established
- Very high latency (>100ms to LAN devices)
- Packet loss

### Diagnosis

**Check bridge STP (Spanning Tree Protocol):**
```bash
brctl show
brctl showstp br0
```

**Check for duplex/speed issues:**
```bash
ethtool eth0
```

### Solutions

**Disable STP if enabled:**
```bash
sudo brctl stp br0 off
```

Make permanent in `/etc/network/interfaces.d/bridge`:
```
bridge_stp off
```

**Check physical connection:**
```bash
# Check for errors
ethtool -S eth0 | grep error

# Check link status
ethtool eth0 | grep Speed
```

## Issue 9: Script Installation Failed

### Symptoms
- Package installation errors
- "Package not found" errors
- Download failures

### Solutions

**Update package lists:**
```bash
sudo apt update
```

**Try manual package installation:**
```bash
# Install ZeroTier
curl -s https://install.zerotier.com | sudo bash

# Install bridge-utils
sudo apt install -y bridge-utils

# Install ifupdown
sudo apt install -y ifupdown
```

**If still failing, use direct package downloads:**
The script has built-in fallback URLs. Check:
```bash
# Check architecture
dpkg --print-architecture

# Manually download and install
wget http://ftp.debian.org/debian/pool/main/b/bridge-utils/bridge-utils_1.7.1-1_armhf.deb
sudo dpkg -i bridge-utils_1.7.1-1_armhf.deb
sudo apt-get install -f -y
```

## Diagnostic Commands Reference

### Essential Commands
```bash
# Bridge status
brctl show
brctl showstp br0

# Interface status
ip link show
ip addr show

# Routing
ip route
netstat -rn

# ZeroTier
sudo zerotier-cli info
sudo zerotier-cli listnetworks
sudo zerotier-cli peers

# Services
systemctl status zerotier-one
systemctl status networking
systemctl status dhcpcd

# Logs
journalctl -xe
journalctl -u zerotier-one
journalctl -u networking
cat /tmp/bridge-setup.log

# Cron
sudo crontab -l
```

### Network Testing
```bash
# From bridge device
ping 192.168.1.1        # Gateway
ping 8.8.8.8            # Internet
traceroute 192.168.1.1

# From ZeroTier client
ping [bridge-ip]        # Bridge
ping [gateway-ip]       # LAN gateway
ping [lan-device-ip]    # LAN device
traceroute [lan-device-ip]
```

## Complete Configuration Verification

Run this complete verification script:

```bash
#!/bin/bash
echo "=== Bridge Configuration ==="
brctl show

echo -e "\n=== IP Configuration ==="
ip addr show br0
ip addr show eth0
ip link show | grep zt

echo -e "\n=== Routing ==="
ip route

echo -e "\n=== ZeroTier Status ==="
sudo zerotier-cli info
sudo zerotier-cli listnetworks

echo -e "\n=== Services ==="
systemctl is-active zerotier-one
systemctl is-active networking

echo -e "\n=== dhcpcd Configuration ==="
grep -A2 denyinterfaces /etc/dhcpcd.conf

echo -e "\n=== Cron Job ==="
sudo crontab -l | grep brctl

echo -e "\n=== Auto-start Log ==="
cat /tmp/bridge-setup.log
```

Save as `verify-bridge.sh`, make executable, and run:
```bash
chmod +x verify-bridge.sh
./verify-bridge.sh
```

## Getting Help

If you've tried all troubleshooting steps and still have issues:

1. Run the verification script above
2. Collect logs: `journalctl -xe > system.log`
3. Note your exact configuration (network IPs, interface names)
4. Document the exact error messages you're seeing
5. Check if you can ping the bridge from LAN devices

## Common Misconfigurations

❌ **Assigning Managed IP in ZeroTier Portal**
- Bridge device must have NO Managed IP
- Only route configuration should point through the bridge

❌ **Wrong gateway in bridge config**
- Gateway must be your actual LAN router IP
- Must be reachable from the bridge IP

❌ **Bridge IP in DHCP range**
- Bridge must have static IP outside DHCP range
- Reserve this IP in your router

❌ **Firewall blocking traffic**
- Some routers block traffic from unrecognized devices
- May need to add bridge MAC to allowed devices

❌ **Missing route in ZeroTier**
- Must have Managed Route: LAN_SUBNET via BRIDGE_IP
- Example: 192.168.1.0/24 via 192.168.1.100
