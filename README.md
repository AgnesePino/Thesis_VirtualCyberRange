# Thesis_VirtualCyberRange
This script automates the setup of a virtual network environment using virtual machines (VMs) and WireGuard VPN tunnels. The infrastructure is designed for a Capture the Flag (CTF) competition, where each team has a dedicated VM (vulnbox) and WireGuard configuration to securely connect to the game server (gamesystem).

Prerequisites
Incus/LXD: The script uses incus commands to manage the VMs. Ensure incus is installed and configured on your system.
WireGuard: This tool is used to create secure tunnels for VPN communication between the VMs and the players.
psutil: Used to fetch system information like network interfaces and IP addresses.
sudo: The script requires elevated privileges to run various network commands (e.g., setting up iptables, configuring VMs).
Features
Automatic VM Creation: Sets up VMs for each team using Ubuntu 22.04 images.
Network Configuration: Assigns IP addresses, creates routing rules, and configures the network interfaces for each VM.
WireGuard Configuration: Generates WireGuard keys and configurations for both the server and clients (players).
Infrastructure Customization: Allows the user to specify the number of teams and players per team, with dynamic IP allocation.
Script Workflow
Setup Game Server:

Initializes the gamesystem VM, configures its network interface, and assigns it a static IP.
Configure Teams and Players:

For each team, a VM (vulnbox) is created and configured with a static IP.
For each player in a team, a WireGuard client configuration is generated, allowing them to connect to the vulnbox VM securely.
WireGuard VPN Setup:

WireGuard server and client configurations are generated dynamically.
Server configurations include peer entries for each player in the team.
Client configurations allow players to connect to the VPN and communicate with their respective team’s vulnbox and the game server.
Tap Script:

A tap script is generated to manage network routing for the VMs. This ensures traffic is properly routed through the virtual interfaces.
How to Run
Clone or download this repository.

Install the required dependencies:
sudo apt install lxd wireguard psutil

Ensure incus (or LXD) is properly initialized and configured. You can do this by running:
sudo incus init

Run the script:
python3 setup_infrastructure.py
You will be prompted to enter the number of teams and the number of players per team. Based on your inputs, the script will create the infrastructure.

Configuration Files
Client Configurations: WireGuard client configuration files for each player will be saved in the client_configs/ directory.
Server Configurations: WireGuard server configurations for each team will be saved in the server_configs/ directory.
Tap Script: A tap-script.sh file will be generated to handle the tap interfaces and IP routing.
Example Use Case
For a CTF with 3 teams and 2 players per team:

3 VMs will be created (one for each team), each with a unique vulnbox configuration.
Each VM will have its own WireGuard server, and each player will receive a unique WireGuard client configuration.
Customization
You can customize the following:

VM images: The script uses the Ubuntu 22.04 image, but this can be changed in the setup_infrastructure function.
Network Configuration: IP address ranges can be modified in the generate_vm_ip and generate_team_ip functions.
WireGuard Configuration: You can tweak the WireGuard settings (e.g., PersistentKeepalive, AllowedIPs) in the relevant configuration functions.
Troubleshooting
VM Not Starting: If a VM doesn't start or throws an error, ensure that incus is correctly installed and that your system has enough resources to run the VMs.
WireGuard Connection Issues: Ensure that the WireGuard service is running on both the server and client machines. You can use wg show to debug active connections.

License
This project is open-source and distributed under the MIT License.
