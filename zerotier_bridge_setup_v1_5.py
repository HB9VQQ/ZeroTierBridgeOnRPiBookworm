#!/usr/bin/env python3
"""
ZeroTier Bridge Setup Script for Raspberry Pi OS Bookworm
Automates the installation and configuration of ZeroTier as a network bridge

Author: Roland HB9VQQ
Version: 1.5.1
Date: November 2025
"""

import os
import sys
import subprocess
import re
import time
from pathlib import Path

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.ENDC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def check_root():
    """Check if script is running with root privileges"""
    if os.geteuid() != 0:
        print_error("This script must be run as root!")
        print_info("Please run: sudo python3 zerotier_bridge_setup.py")
        sys.exit(1)

def run_command(command, description="", check=True, shell=True, capture_output=True):
    """Run a shell command and return the result"""
    if description:
        print_info(description)
    
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {command}")
            if e.stderr:
                print(f"Error: {e.stderr}")
        return e

def backup_file(filepath):
    """Create a backup of a file before modifying it"""
    if os.path.exists(filepath):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup.{timestamp}"
        try:
            run_command(f"cp {filepath} {backup_path}", f"Backing up {filepath}")
            print_success(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            print_warning(f"Could not create backup: {e}")
            return None
    return None

def get_architecture():
    """Detect system architecture for package downloads"""
    result = run_command("dpkg --print-architecture", "Detecting system architecture")
    if result.returncode == 0:
        arch = result.stdout.strip()
        print_info(f"Detected architecture: {arch}")
        return arch
    return "armhf"  # Default for Raspberry Pi

def download_package_direct(package_url, output_path):
    """Download a package file from a direct URL"""
    print_info(f"Downloading from: {package_url}")
    
    result = run_command(
        f"wget -q --show-progress -O {output_path} {package_url}",
        check=False,
        capture_output=False
    )
    
    if result.returncode == 0 and os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        if file_size > 1000:  # At least 1KB
            print_success(f"Downloaded successfully ({file_size} bytes)")
            return True
    
    return False

def download_deb_package_improved(package_name, arch):
    """Download .deb package with improved fallback logic"""
    print_info(f"Attempting to download {package_name}...")
    
    # Create temp directory
    temp_dir = "/tmp/zerotier_packages"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Known working package URLs for Debian Bookworm
    known_packages = {
        'bridge-utils': {
            'armhf': 'http://ftp.debian.org/debian/pool/main/b/bridge-utils/bridge-utils_1.7.1-1_armhf.deb',
            'arm64': 'http://ftp.debian.org/debian/pool/main/b/bridge-utils/bridge-utils_1.7.1-1_arm64.deb',
        },
        'ifupdown': {
            'armhf': 'http://ftp.debian.org/debian/pool/main/i/ifupdown/ifupdown_0.8.41_armhf.deb',
            'arm64': 'http://ftp.debian.org/debian/pool/main/i/ifupdown/ifupdown_0.8.41_arm64.deb',
        }
    }
    
    # Try known URL first
    if package_name in known_packages and arch in known_packages[package_name]:
        known_url = known_packages[package_name][arch]
        output_file = f"{temp_dir}/{os.path.basename(known_url)}"
        
        print_info(f"Trying known working version...")
        if download_package_direct(known_url, output_file):
            return output_file
    
    # Try to search for package using apt-cache
    print_info("Searching for package URL via apt-cache...")
    result = run_command(
        f"apt-cache show {package_name} | grep Filename:",
        check=False
    )
    
    if result.returncode == 0 and result.stdout.strip():
        filename = result.stdout.strip().split()[-1]
        # Try different mirrors
        mirrors = [
            "http://ftp.debian.org/debian/",
            "http://deb.debian.org/debian/",
            "http://ftp.ch.debian.org/debian/",
            "http://ftp.de.debian.org/debian/"
        ]
        
        for mirror in mirrors:
            package_url = f"{mirror}{filename}"
            output_file = f"{temp_dir}/{os.path.basename(filename)}"
            
            if download_package_direct(package_url, output_file):
                return output_file
    
    # Last resort: try snapshots.debian.org for stable version
    print_info("Trying Debian snapshot archive...")
    snapshot_urls = {
        'ifupdown': {
            'armhf': 'http://snapshot.debian.org/archive/debian/20231201T084046Z/pool/main/i/ifupdown/ifupdown_0.8.41_armhf.deb',
            'arm64': 'http://snapshot.debian.org/archive/debian/20231201T084046Z/pool/main/i/ifupdown/ifupdown_0.8.41_arm64.deb',
        }
    }
    
    if package_name in snapshot_urls and arch in snapshot_urls[package_name]:
        snapshot_url = snapshot_urls[package_name][arch]
        output_file = f"{temp_dir}/{os.path.basename(snapshot_url)}"
        
        if download_package_direct(snapshot_url, output_file):
            return output_file
    
    print_error(f"Could not download {package_name}")
    return None

def install_deb_package(deb_file):
    """Install a .deb package using dpkg"""
    if not os.path.exists(deb_file):
        print_error(f"Package file not found: {deb_file}")
        return False
    
    print_info(f"Installing {os.path.basename(deb_file)}...")
    
    # Install the package
    result = run_command(
        f"dpkg -i {deb_file}",
        check=False
    )
    
    if result.returncode != 0:
        print_warning("Package installation had errors, trying to fix dependencies...")
        # Try to fix broken dependencies
        run_command("apt-get install -f -y", check=False)
        
        # Try installing again
        result = run_command(f"dpkg -i {deb_file}", check=False)
        
    if result.returncode == 0:
        print_success(f"Successfully installed {os.path.basename(deb_file)}")
        return True
    else:
        print_error(f"Failed to install {os.path.basename(deb_file)}")
        return False

def install_packages():
    """Install required packages with improved fallback"""
    print_header("Installing Required Packages")
    
    # Update package list
    print_info("Updating package lists...")
    result = run_command("apt-get update", check=False)
    
    if result.returncode != 0:
        print_warning("Package list update had issues, continuing anyway...")
    
    # Get system architecture
    arch = get_architecture()
    
    # Packages to install
    packages = ['bridge-utils', 'ifupdown']
    installation_failed = []
    
    for package in packages:
        print_info(f"\n--- Installing {package} ---")
        
        # Check if already installed
        check = run_command(f"dpkg -l | grep '^ii.*{package}'", check=False)
        if check.returncode == 0:
            print_success(f"{package} is already installed")
            continue
        
        # Try apt-get first
        print_info(f"Attempting to install {package} via apt-get...")
        result = run_command(
            f"apt-get install -y {package}",
            check=False
        )
        
        if result.returncode == 0:
            print_success(f"Successfully installed {package} via apt-get")
            continue
        
        # apt-get failed, try direct download
        print_warning(f"apt-get failed for {package}, trying direct download...")
        
        deb_file = download_deb_package_improved(package, arch)
        
        if deb_file:
            if install_deb_package(deb_file):
                print_success(f"Successfully installed {package} via direct download")
            else:
                installation_failed.append(package)
        else:
            installation_failed.append(package)
    
    # Report failed installations
    if installation_failed:
        print_warning(f"\nFailed to install: {', '.join(installation_failed)}")
        print_info("You can try installing manually after the script completes:")
        for pkg in installation_failed:
            print(f"  sudo apt-get install -y {pkg}")
        print()
    
    # Install ZeroTier
    print_info("\n--- Installing ZeroTier ---")
    
    # Check if ZeroTier is already installed
    if os.path.exists('/usr/sbin/zerotier-cli'):
        print_success("ZeroTier is already installed")
    else:
        print_info("Installing ZeroTier via official script...")
        result = run_command(
            "curl -s https://install.zerotier.com/ | bash",
            check=False
        )
        
        if result.returncode == 0:
            print_success("ZeroTier installed successfully")
        else:
            print_error("Failed to install ZeroTier")
            print_error("Cannot continue without ZeroTier")
            sys.exit(1)
    
    print_success("\nPackage installation complete!")
    
    # Final check for critical packages
    if 'ifupdown' in installation_failed:
        print_warning("\nWARNING: ifupdown failed to install!")
        print_info("The bridge configuration requires ifupdown.")
        print_info("After this script, try: sudo apt-get install -y ifupdown")
        response = input(f"\n{Colors.WARNING}Continue anyway? (yes/no): {Colors.ENDC}").strip().lower()
        if response not in ['yes', 'y']:
            sys.exit(1)

def detect_network_manager():
    """Detect if NetworkManager is active"""
    result = run_command("systemctl is-active NetworkManager", check=False)
    return result.returncode == 0

def handle_network_manager():
    """Handle NetworkManager if it's running"""
    if detect_network_manager():
        print_warning("NetworkManager is active - this conflicts with manual bridge configuration")
        print_info("For bridge configuration to work, we need to disable NetworkManager")
        
        response = input(f"\n{Colors.WARNING}Disable NetworkManager? (yes/no): {Colors.ENDC}").strip().lower()
        
        if response in ['yes', 'y']:
            print_info("Disabling NetworkManager...")
            run_command("systemctl stop NetworkManager")
            run_command("systemctl disable NetworkManager")
            print_success("NetworkManager disabled")
            return True
        else:
            print_error("Cannot continue with NetworkManager active")
            print_info("Please manually disable NetworkManager or use a system without it")
            sys.exit(1)
    
    return False

def configure_dhcpcd():
    """Configure dhcpcd to ignore bridge interfaces"""
    print_header("Configuring dhcpcd")
    
    dhcpcd_conf = "/etc/dhcpcd.conf"
    
    # Check if dhcpcd.conf exists
    if not os.path.exists(dhcpcd_conf):
        print_warning(f"{dhcpcd_conf} does not exist")
        
        # Check if NetworkManager is running
        handle_network_manager()
        
        # Create dhcpcd.conf regardless of NetworkManager status
        print_info("Creating minimal dhcpcd.conf...")
        try:
            with open(dhcpcd_conf, 'w') as f:
                f.write("# dhcpcd configuration for ZeroTier bridge\n")
                f.write("# Created by zerotier_bridge_setup.py\n\n")
            print_success(f"Created {dhcpcd_conf}")
        except Exception as e:
            print_error(f"Could not create {dhcpcd_conf}: {e}")
            return False
    
    # Backup the file
    backup_file(dhcpcd_conf)
    
    # Check if already configured
    try:
        with open(dhcpcd_conf, 'r') as f:
            content = f.read()
    except Exception as e:
        print_error(f"Could not read {dhcpcd_conf}: {e}")
        return False
    
    if 'denyinterfaces eth0' in content and 'denyinterfaces zt' in content:
        print_success("dhcpcd is already configured correctly")
        return True
    
    # Add denyinterfaces
    print_info("Adding denyinterfaces to dhcpcd.conf...")
    
    try:
        with open(dhcpcd_conf, 'a') as f:
            f.write("\n# ZeroTier Bridge Configuration\n")
            f.write("# Prevent dhcpcd from managing bridge interfaces\n")
            f.write("denyinterfaces eth0\n")
            f.write("denyinterfaces zt*\n")
        
        print_success("dhcpcd configured successfully")
        return True
    except Exception as e:
        print_error(f"Failed to configure dhcpcd: {e}")
        return False

def get_user_input():
    """Get configuration parameters from user"""
    print_header("Configuration Parameters")
    
    config = {}
    
    # Get physical interface
    print_info("Available network interfaces:")
    run_command("ip link show | grep -E '^[0-9]+:' | awk '{print $2}' | sed 's/://'", 
                capture_output=False)
    
    default_interface = "eth0"
    config['physical_interface'] = input(f"\nPhysical interface to bridge [{default_interface}]: ").strip() or default_interface
    
    # Get bridge IP
    print_info("\nCurrent IP configuration:")
    run_command(f"ip addr show {config['physical_interface']}", capture_output=False)
    
    while True:
        bridge_ip = input("\nStatic IP for bridge (e.g., 192.168.1.2): ").strip()
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', bridge_ip):
            config['bridge_ip'] = bridge_ip
            break
        print_error("Invalid IP address format")
    
    # Get netmask
    default_netmask = "255.255.255.0"
    config['netmask'] = input(f"Netmask [{default_netmask}]: ").strip() or default_netmask
    
    # Get gateway
    while True:
        gateway = input("Gateway IP (e.g., 192.168.1.1): ").strip()
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', gateway):
            config['gateway'] = gateway
            break
        print_error("Invalid IP address format")
    
    # Get DNS
    default_dns = "8.8.8.8 8.8.4.4"
    config['dns'] = input(f"DNS servers [{default_dns}]: ").strip() or default_dns
    
    # Get ZeroTier Network ID
    print_info("\nYou can join the ZeroTier network now or skip and do it manually later.")
    print_info("To join now, you need your ZeroTier Network ID (16-character hex string)")
    print_info("Example: a84ac5c10a1b2c3d")
    
    zt_network = input("\nZeroTier Network ID (or press Enter to skip): ").strip()
    config['zerotier_network'] = zt_network if len(zt_network) == 16 else None
    
    # Summary
    print_header("Configuration Summary")
    print(f"Physical Interface: {config['physical_interface']}")
    print(f"Bridge IP: {config['bridge_ip']}")
    print(f"Netmask: {config['netmask']}")
    print(f"Gateway: {config['gateway']}")
    print(f"DNS: {config['dns']}")
    if config['zerotier_network']:
        print(f"ZeroTier Network: {config['zerotier_network']}")
    else:
        print("ZeroTier Network: Will join manually later")
    
    confirm = input(f"\n{Colors.WARNING}Proceed with these settings? (yes/no): {Colors.ENDC}").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print_info("Configuration cancelled. Exiting.")
        sys.exit(0)
    
    return config

def configure_network_interfaces(config):
    """Configure /etc/network/interfaces"""
    print_header("Configuring Network Interfaces")
    
    interfaces_file = "/etc/network/interfaces"
    
    # Backup
    backup_file(interfaces_file)
    
    # Create new configuration
    interfaces_config = f"""# /etc/network/interfaces
# Configured by zerotier_bridge_setup.py

# Loopback interface
auto lo
iface lo inet loopback

# Physical interface - no IP configuration (manual mode)
auto {config['physical_interface']}
iface {config['physical_interface']} inet manual

# Bridge interface
auto br0
iface br0 inet static
    address {config['bridge_ip']}
    netmask {config['netmask']}
    gateway {config['gateway']}
    dns-nameservers {config['dns']}
    bridge_ports {config['physical_interface']}
    bridge_stp off
    bridge_fd 0
    bridge_maxwait 0
"""
    
    try:
        with open(interfaces_file, 'w') as f:
            f.write(interfaces_config)
        
        print_success(f"{interfaces_file} configured successfully")
        return True
    except Exception as e:
        print_error(f"Failed to write {interfaces_file}: {e}")
        return False

def join_zerotier_network(network_id):
    """Join a ZeroTier network"""
    print_header("Joining ZeroTier Network")
    
    if not network_id:
        print_warning("No network ID provided, skipping...")
        return None
    
    print_info(f"Joining network {network_id}...")
    
    result = run_command(f"zerotier-cli join {network_id}", check=False)
    
    if result.returncode == 0:
        print_success(f"Successfully joined network {network_id}")
        
        # Wait a moment for the interface to appear
        time.sleep(2)
        
        # Get ZeroTier interface name
        result = run_command("ip link show | grep 'zt' | awk '{print $2}' | sed 's/:$//'", check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            zt_interface = result.stdout.strip().split('\n')[0]
            print_info(f"ZeroTier interface: {zt_interface}")
            return zt_interface
    else:
        print_error("Failed to join ZeroTier network")
    
    return None

def get_zerotier_info():
    """Get ZeroTier node information"""
    result = run_command("zerotier-cli info", check=False)
    
    if result.returncode == 0:
        # Parse output: "200 info 1234567890 1.16.0 ONLINE"
        parts = result.stdout.strip().split()
        if len(parts) >= 3:
            return {
                'node_id': parts[2],
                'version': parts[3] if len(parts) > 3 else 'unknown',
                'status': parts[4] if len(parts) > 4 else 'unknown'
            }
    
    return None

def configure_zerotier_managed(zt_interface):
    """Configure ZeroTier allowManaged setting"""
    print_header("Configuring ZeroTier Managed Routes")
    
    if not zt_interface:
        print_warning("No ZeroTier interface provided, skipping...")
        return False
    
    print_info("Setting allowManaged=0 for bridge mode...")
    
    # Get ZeroTier node info to find network ID
    result = run_command("zerotier-cli listnetworks", check=False)
    
    if result.returncode != 0:
        print_error("Could not list ZeroTier networks")
        return False
    
    # Parse network ID from output
    network_id = None
    for line in result.stdout.split('\n'):
        if zt_interface in line:
            # Extract 16-character network ID
            match = re.search(r'\b([a-f0-9]{16})\b', line)
            if match:
                network_id = match.group(1)
                break
    
    if not network_id:
        print_error("Could not determine ZeroTier network ID")
        return False
    
    print_info(f"Found network ID: {network_id}")
    
    # Set allowManaged
    result = run_command(
        f"zerotier-cli set {network_id} allowManaged=0",
        check=False
    )
    
    if result.returncode == 0:
        print_success("allowManaged set to 0")
        return True
    else:
        print_error("Failed to set allowManaged")
        return False

def create_cron_job(zt_interface):
    """Create cron job to add ZeroTier interface to bridge at boot"""
    print_header("Configuring Auto-Start")
    
    if not zt_interface:
        print_warning("No ZeroTier interface provided, you'll need to manually add it to crontab")
        print_info("After joining ZeroTier network, add this to root's crontab:")
        print(f"\n{Colors.OKCYAN}@reboot sleep 60 && brctl addif br0 ZEROTIER_INTERFACE{Colors.ENDC}\n")
        return False
    
    cron_command = f"@reboot sleep 45 && /usr/sbin/brctl addif br0 {zt_interface} >> /tmp/bridge-setup.log 2>&1"
    
    print_info("Adding cron job to root's crontab...")
    
    # Get current crontab
    result = run_command("crontab -l", check=False)
    current_cron = result.stdout if result.returncode == 0 else ""
    
    # Check if already exists
    if cron_command in current_cron:
        print_success("Cron job already exists")
        return True
    
    # Add new cron job
    new_cron = current_cron + f"\n{cron_command}\n"
    
    # Write new crontab
    result = run_command(
        f"echo '{new_cron}' | crontab -",
        check=False
    )
    
    if result.returncode == 0:
        print_success("Cron job added successfully")
        print_info(f"Command: {cron_command}")
        return True
    else:
        print_error("Failed to add cron job")
        return False

def print_portal_instructions(config):
    """Print instructions for ZeroTier portal configuration"""
    print_header("ZeroTier Portal Configuration")
    
    zt_info = get_zerotier_info()
    
    print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}\n")
    
    if zt_info:
        print(f"1. Log in to ZeroTier Central: https://my.zerotier.com")
        print(f"2. Go to your network")
        print(f"3. Scroll to 'Members' section")
        print(f"4. Find your device:")
        print(f"   Node ID: {Colors.OKCYAN}{zt_info['node_id']}{Colors.ENDC}")
        print(f"5. Click on the wrench/settings icon to edit device settings")
        print(f"6. In the device settings:")
        print(f"   ✓ Check 'Allow Ethernet Bridging'")
        print(f"   ✓ Check 'Do Not Auto-Assign IPs'")
        print(f"7. Check the 'Auth' checkbox to authorize this device")
        print(f"8. Do NOT assign a Managed IP to this device")
        print(f"   (Leave the managed IP field empty/unassigned)")
        print(f"\n9. Configure Managed Routes in network settings (at top of page):")
        print(f"   Add route: {config['bridge_ip'].rsplit('.', 1)[0]}.0/24 via {config['bridge_ip']}")
        print(f"   Example: If your LAN is 192.168.1.0/24, route traffic via {config['bridge_ip']}")
    else:
        print_warning("Could not get ZeroTier node information")
        print("Complete these steps after reboot:")
        print("1. Run: sudo zerotier-cli info")
        print("2. Note your Node ID")
        print("3. Log in to https://my.zerotier.com")
        print("4. Find your device in Members section")
        print("5. Edit device: Enable 'Allow Ethernet Bridging' and 'Do Not Auto-Assign IPs'")
        print("6. Authorize device (do NOT assign a Managed IP)")
        print("7. Add Managed Route in network settings")
    
    print(f"\n{Colors.WARNING}CRITICAL: Do NOT assign a Managed IP to this bridge device!{Colors.ENDC}")
    print("The bridge already has a static IP from your LAN.")

def print_final_instructions(config, zt_interface):
    """Print final instructions"""
    print_header("Setup Complete - Final Steps")
    
    print(f"{Colors.BOLD}What happens next:{Colors.ENDC}\n")
    
    print("1. Reboot your Raspberry Pi:")
    print(f"   {Colors.OKCYAN}sudo reboot{Colors.ENDC}\n")
    
    print("2. After reboot (wait 60 seconds), verify the configuration:\n")
    
    print(f"   {Colors.BOLD}# Check bridge status{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}brctl show{Colors.ENDC}")
    print(f"   Expected: br0 contains {config['physical_interface']}", end='')
    if zt_interface:
        print(f" and {zt_interface}")
    else:
        print(" and zt* interface")
    print()
    
    print(f"   {Colors.BOLD}# Check IP configuration{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}ip addr show{Colors.ENDC}")
    print(f"   Expected:")
    print(f"   - br0 has IP {config['bridge_ip']}")
    print(f"   - {config['physical_interface']} has NO IP")
    if zt_interface:
        print(f"   - {zt_interface} has NO IP")
    else:
        print(f"   - zt* interface has NO IP")
    print()
    
    print(f"   {Colors.BOLD}# Check ZeroTier{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}sudo zerotier-cli listnetworks{Colors.ENDC}")
    print()
    
    print("3. Configure the ZeroTier portal (see instructions above)\n")
    
    print("4. Test from a ZeroTier client:")
    print("   - Connect another device to your ZeroTier network")
    print("   - Try to ping devices on your LAN")
    print(f"   - Try to ping your gateway: {config['gateway']}\n")
    
    print(f"{Colors.BOLD}Troubleshooting:{Colors.ENDC}\n")
    print("If bridge doesn't work after reboot:")
    print(f"1. Check bridge: {Colors.OKCYAN}brctl show{Colors.ENDC}")
    print(f"2. Manually add ZT interface: {Colors.OKCYAN}sudo brctl addif br0 zt*{Colors.ENDC}")
    print(f"3. Check dhcpcd isn't interfering: {Colors.OKCYAN}systemctl status dhcpcd{Colors.ENDC}")
    print(f"4. Review logs: {Colors.OKCYAN}journalctl -xe{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}Setup script completed successfully!{Colors.ENDC}")

def main():
    """Main setup function"""
    print_header("ZeroTier Bridge Setup for Raspberry Pi OS Bookworm")
    print(f"{Colors.BOLD}Version 1.5.1{Colors.ENDC}")
    print("This script will configure your Raspberry Pi as a ZeroTier network bridge\n")
    
    # Check prerequisites
    check_root()
    
    # Get configuration from user
    config = get_user_input()
    
    # Install packages
    install_packages()
    
    # Configure dhcpcd
    if not configure_dhcpcd():
        print_error("Failed to configure dhcpcd")
        sys.exit(1)
    
    # Configure network interfaces
    if not configure_network_interfaces(config):
        print_error("Failed to configure network interfaces")
        sys.exit(1)
    
    # Join ZeroTier network if requested
    zt_interface = None
    if config['zerotier_network']:
        zt_interface = join_zerotier_network(config['zerotier_network'])
        
        if zt_interface:
            # Configure allowManaged
            configure_zerotier_managed(zt_interface)
            
            # Create cron job
            create_cron_job(zt_interface)
    
    # Print portal configuration instructions
    print_portal_instructions(config)
    
    # Print final instructions
    print_final_instructions(config, zt_interface)
    
    print(f"\n{Colors.WARNING}Remember to reboot: sudo reboot{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Setup cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
