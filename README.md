# ZeroTier Bridge Setup for Raspberry Pi

**Automated bridge configuration for Raspberry Pi OS Bookworm**


## Overview

This Python script automates the complete setup of a ZeroTier network bridge on Raspberry Pi OS Bookworm (Debian 12). It configures your Raspberry Pi to act as a transparent bridge between your ZeroTier virtual network and your local LAN, allowing ZeroTier clients secure access to your local network devices.

**Author:** Roland HB9VQQ  
**Version:** 1.5.1  
**Date:** November 2025

## What Is a ZeroTier Bridge?

A ZeroTier bridge allows devices connected to your ZeroTier virtual network to access devices on your local physical network (LAN) as if they were directly connected. This is useful for:

- **Remote access** to home/office LAN devices
- **IoT device management** from anywhere
- **Security camera access** without port forwarding
- **Network printer access** remotely
- **Smart home control** over ZeroTier

```
[ZeroTier Client] ←→ [Internet] ←→ [Raspberry Pi Bridge] ←→ [Local LAN]
                                          ↓
                                    Transparent access to:
                                    - Printers
                                    - Cameras
                                    - IoT devices
                                    - Smart home systems
                                    - Any LAN device
```

## Key Features

- ✅ **Fully automated setup** - No manual configuration needed
- ✅ **Smart package management** - Falls back to direct downloads if needed
- ✅ **Automatic boot configuration** - Bridge starts automatically after reboot
- ✅ **Comprehensive error handling** - Detailed logging and troubleshooting
- ✅ **Safe backups** - All modified files are backed up automatically
- ✅ **dhcpcd conflict resolution** - Properly handles Bookworm's networking
- ✅ **Production ready** - Battle-tested cron job with proper logging

## Quick Start

### Prerequisites

- Raspberry Pi with Raspberry Pi OS Bookworm installed
- Root/sudo access
- Internet connection
- ZeroTier account and network ID from [my.zerotier.com](https://my.zerotier.com)

### Installation

1. **Run the script:**
   ```bash
   sudo python3 zerotier_bridge_setup_v1_5.py
   ```

2. **Follow the prompts** to enter your network configuration

3. **Configure ZeroTier Portal**

4. **Reboot:**
   ```bash
   sudo reboot
   ```



### Verification

After reboot (wait 60 seconds), verify the setup:

```bash
# Check bridge
brctl show

# Check IPs
ip addr show

# Check ZeroTier
sudo zerotier-cli listnetworks
```


## How It Works

### 1. Package Installation
- Installs ZeroTier-One client
- Installs bridge-utils (brctl)
- Installs ifupdown for network management
- Falls back to direct downloads if standard installation fails

### 2. Network Bridge Configuration
- Creates bridge interface (br0)
- Configures static IP on bridge
- Adds physical interface (eth0) to bridge
- Configures routing through your gateway

### 3. dhcpcd Configuration
- Prevents dhcpcd from managing bridge interfaces
- Avoids IP conflicts and network instability
- Ensures proper network startup order

### 4. ZeroTier Integration
- Joins specified ZeroTier network
- Disables ZeroTier managed routes (allowManaged=0)
- Adds ZeroTier interface to bridge
- Creates auto-start script for boot

### 5. Automatic Startup
- Creates cron job to add ZeroTier interface at boot
- Uses full path `/usr/sbin/brctl` to avoid PATH issues
- Includes logging to `/tmp/bridge-setup.log`
- 45-second delay ensures services are ready

## Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Raspberry Pi                        │
│                                                              │
│  ┌────────────┐                                             │
│  │   eth0     │ (No IP)                                     │
│  └─────┬──────┘                                             │
│        │                                                     │
│  ┌─────▼──────────────────────────────┐                    │
│  │          Bridge (br0)               │                    │
│  │      IP: 192.168.1.100             │                    │
│  │      Gateway: 192.168.1.1          │                    │
│  └─────┬──────────────────────────────┘                    │
│        │                                                     │
│  ┌─────▼──────┐                                             │
│  │  ztxxxxxx  │ (No IP)                                     │
│  └────────────┘                                             │
│                                                              │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               │                               │
       ┌───────▼────────┐             ┌────────▼─────────┐
       │  Physical LAN   │             │  ZeroTier Cloud  │
       │  192.168.1.0/24 │             │   Network        │
       └─────────────────┘             └──────────────────┘
```

## Configuration Example

Typical home network setup:

| Setting | Example Value | Description |
|---------|--------------|-------------|
| Physical Interface | `eth0` | Ethernet connection to router |
| Bridge IP | `192.168.1.100` | Static IP for the bridge |
| Gateway | `192.168.1.1` | Your router's IP |
| Netmask | `255.255.255.0` | Standard home network mask |
| ZeroTier Network ID | `1234567890abcdef` | Your ZeroTier network ID |

**ZeroTier Portal Settings:**

**Device Settings (click wrench icon to edit device):**
- Allow Ethernet Bridging: ✅ Checked
- Do Not Auto-Assign IPs: ✅ Checked
- Device Authorization: ✅ Authorized
- Managed IP: ❌ **None** (must be empty)

**Network Settings (at top of page):**
- Managed Route: `192.168.1.0/24` via `192.168.1.100`

## What Gets Modified

The script modifies the following system files (all with automatic backups):

```
/etc/dhcpcd.conf                    # dhcpcd configuration
/etc/network/interfaces.d/bridge    # Bridge configuration
/var/lib/cron/tabs/root             # Root crontab (auto-start)
ZeroTier allowManaged setting       # Set to 0 for bridge mode
```

## Troubleshooting

Having issues? Check these common problems:

| Issue | Quick Fix | Documentation |
|-------|-----------|---------------|
| ZT interface not in bridge | `sudo brctl addif br0 ztxxxxxx` | [Troubleshooting Guide](TROUBLESHOOTING.md#issue-1-zerotier-interface-not-in-bridge) |
| No IP on bridge | Check `/etc/network/interfaces.d/bridge` | [Troubleshooting Guide](TROUBLESHOOTING.md#issue-3-no-ip-address-on-bridge) |
| Can't reach LAN | Verify ZeroTier Portal config | [Troubleshooting Guide](TROUBLESHOOTING.md#issue-5-cant-reach-lan-from-zerotier) |
| dhcpcd interference | Check `/etc/dhcpcd.conf` | [Troubleshooting Guide](TROUBLESHOOTING.md#issue-2-dhcpcd-interference) |

## Requirements

### Hardware
- Raspberry Pi (any model with Ethernet/WiFi)
- SD card with Raspberry Pi OS Bookworm
- Network connection (Ethernet recommended for bridge)

### Software
- Raspberry Pi OS Bookworm (Debian 12)
- Python 3 (pre-installed)
- Root/sudo access
- Active internet connection during setup

### Network
- ZeroTier account (free at [my.zerotier.com](https://my.zerotier.com))
- ZeroTier network created
- Static IP address available outside DHCP range
- Access to router settings (recommended)

## Security Considerations

⚠️ **Important Security Notes:**

1. **Network Access:** This bridge gives ZeroTier clients access to your entire LAN
2. **Authentication:** Ensure only trusted devices are authorized in ZeroTier
3. **Firewall:** Consider configuring iptables for additional security
4. **Updates:** Keep ZeroTier and system packages updated
5. **Monitoring:** Regularly review authorized devices in ZeroTier Central

## Limitations

- Bridge mode requires a static IP
- Physical interface must have stable connection
- ZeroTier managed IPs cannot be used on bridge device
- Some advanced routing may require manual configuration

## Best Practices

✅ **Do:**
- Use a static IP outside your DHCP range
- Reserve the bridge IP in your router
- Regularly check authorized ZeroTier devices
- Keep the system updated
- Monitor the auto-start log after reboots

❌ **Don't:**
- Assign a Managed IP to the bridge device in ZeroTier Portal
- Use an IP that's in your DHCP range
- Modify bridge configuration without backups
- Disable automatic updates for ZeroTier

### Useful Commands

```bash
# Quick status check
sudo zerotier-cli info
sudo zerotier-cli listnetworks
brctl show
ip addr show br0

# Logs
cat /tmp/bridge-setup.log
journalctl -u zerotier-one
journalctl -u networking

# Manual fixes
sudo brctl addif br0 ztxxxxxx      # Add ZT interface
sudo ifdown br0 && sudo ifup br0   # Restart bridge
```

## Acknowledgments

- ZeroTier for providing excellent SDN technology
- Raspberry Pi community for extensive networking documentation
- Contributors and testers who helped refine this script

## Author

**Roland HB9VQQ**
- Amateur Radio Operator & Network Engineer
- Developer of propagation analysis tools
- Creator of technical documentation for amateur radio applications

---

*Last Updated: November 2025*
