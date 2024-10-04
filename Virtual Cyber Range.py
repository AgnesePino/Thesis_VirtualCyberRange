import psutil
import socket
import subprocess
import os

# Funzione per eseguire un comando di sistema e gestire eventuali errori
def run_command(command, check=True, use_sudo=False):
    if use_sudo:
        command = f"sudo {command}"
    try:
        result = subprocess.run(command, shell=True, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Output: {result.stdout.decode().strip()}")
        if result.stderr:
            print(f"Error Output: {result.stderr.decode().strip()}")
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        if e.stderr:
            print(f"Error Output: {e.stderr.decode().strip()}")

def create_config_sh(ip_address, team=None):
	return f"""#!/bin/bash
	# Configurazione specifica per vulnbox del team {team}
	ip addr add {ip_address} dev enp5s0
	ip route add {ip_address.replace('.1', '.2')} dev enp5s0
	ip route add default via {ip_address.replace('.1', '.2')}
    # Configurazione DNS
    echo -e "[Resolve]\\nDNS=8.8.8.8\\n" > /etc/systemd/resolved.conf
    systemctl restart systemd-resolved
	"""
# Funzione per copiare ed eseguire il file config.sh nella VM
def copy_and_run_config_sh(vm_name, config_content):
    config_filename = "config.sh"
    
    # Scrivi il file config.sh localmente
    with open(config_filename, "w") as config_file:
        config_file.write(config_content)
    
    # Copia il file nella macchina virtuale
    command = f"incus file push {config_filename} {vm_name}/root/{config_filename}"
    run_command(command, use_sudo=True)
    
    # Rendi il file eseguibile
    command = f"incus exec {vm_name} -- chmod +x /root/{config_filename}"
    run_command(command, use_sudo=True)
    
    # Esegui lo script config.sh
    command = f"incus exec {vm_name} -- /root/{config_filename}"
    run_command(command, use_sudo=True)

def vm_exists(vm_name):
    result = subprocess.run(f"incus list | grep {vm_name}", shell=True, stdout=subprocess.PIPE)
    return result.returncode == 0

# Funzione per configurare una VM generica
def setup_vm(vm_name, vm_ip):
    
    # Controlla se la VM esiste già
    if not vm_exists(vm_name):
        # Creazione della VM se non esiste
        command = f"incus init images:ubuntu/22.04 {vm_name} --vm"
        run_command(command, use_sudo=True)
    else:
        print(f"La VM {vm_name} esiste già. Skip creazione.")
    
    # Controlla se il dispositivo di rete è già configurato
    result = subprocess.run(f"incus config device show {vm_name} | grep enp5s0", shell=True, stdout=subprocess.PIPE)
    if result.returncode != 0:
        # Configura l'interfaccia di rete solo se non esiste già
        command = f"incus config device add {vm_name} enp5s0 nic nictype=routed host_name={vm_name}_tap ipv4.host_address={vm_ip} mtu=1500"
        run_command(command, use_sudo=True)
    else:
        print(f"Il dispositivo di rete enp5s0 è già configurato su {vm_name}. Skip configurazione.")
    
    # Avvia la VM se non è già in esecuzione
    command = f"incus start {vm_name}"
    run_command(command, use_sudo=True)

    # Creazione del file config.sh per la VM generica e esecuzione
    config_sh_content = create_config_sh(vm_ip)
    copy_and_run_config_sh(vm_name, config_sh_content)
    
    print(f"Macchina {vm_name} con IP {vm_ip} configurata con successo!")



# Funzione che preleva l'ip locale e l'interfaccia
def get_ip_and_interface():
    interfaces = psutil.net_if_addrs()  # Ottiene tutte le interfacce e i loro indirizzi
    for interface_name, interface_addresses in interfaces.items():
        for address in interface_addresses:
            if address.family == socket.AF_INET:  # Verifica che l'indirizzo sia IPv4 (usando socket.AF_INET)
                ip_address = address.address
                if ip_address != "127.0.0.1":  # Ignora l'indirizzo di loopback
                    return interface_name, ip_address
    return None, None



# Funzione per generare un IP per le VM
def generate_vm_ip(team):
    return f"10.60.{team}.1"



# Funzione per generare un IP per i player di ogni team
def generate_team_ip(team, player):
    return f"10.80.{team}.{player+1}"



# Funzione per generare chiavi WireGuard (Private/Public)
def generate_wireguard_keys():
    private_key = subprocess.check_output("wg genkey", shell=True).decode('utf-8').strip()
    public_key = subprocess.check_output(f"echo {private_key} | wg pubkey", shell=True).decode('utf-8').strip()
    return private_key, public_key

# Funzione per creare la configurazione del server WireGuard
def create_wireguard_server_config(interface, listen_port, private_key_server):
    return f"""[Interface]
Address = {interface}/32
ListenPort = {listen_port}
PrivateKey = {private_key_server}
"""



# Funzione per creare la configurazione del peer (client) nel file server
def create_peer_config(public_key_client, ip_address):
    return f"""[Peer]
PublicKey = {public_key_client}
AllowedIPs = {ip_address}/32
"""



# Funzione per creare la configurazione individuale di ogni client (giocatore)
def create_client_config(private_key_client, public_key_server, client_ip, server_ip, listen_port,vm_ip):
    return f"""[Interface]
PrivateKey = {private_key_client}
Address = {client_ip}/32

[Peer]
PublicKey = {public_key_server}
Endpoint = {server_ip}:{listen_port}
AllowedIPs = {vm_ip}/16, 10.10.0.1/32
PersistentKeepalive = 21
"""



def setup_wireguard_for_team(team, server_ip, players_per_team, listen_port_base, vm_ip):
    num = 0  # Puoi incrementare questo numero in base al numero di team configurati
    listen_port = listen_port_base + num
    
    # Configurazione WireGuard per il team
    private_key_server, public_key_server = generate_wireguard_keys()
    server_interface = f"10.80.{team}.1"
    
    # Configurazione del server WireGuard per il team
    server_config = create_wireguard_server_config(server_interface, listen_port, private_key_server)
    
    # Creazione dei peer per ogni giocatore nel team
    for player in range(1, players_per_team + 1):
        private_key_client, public_key_client = generate_wireguard_keys()
        client_ip = generate_team_ip(team, player)
        
        # Aggiungi il peer (client) alla configurazione del server
        server_config += create_peer_config(public_key_client, client_ip)
        
        # Genera il file di configurazione per il client
        client_config = create_client_config(private_key_client, public_key_server, client_ip, server_ip, listen_port, vm_ip)
        
        # Salva il file di configurazione per il client
        client_filename = f"client_configs/team{team}_player{player}.conf"
        with open(client_filename, "w") as client_file:
            client_file.write(client_config)
        
        # Attiva la configurazione WireGuard per il client
        command = f"wg-quick up {client_filename}"
        run_command(command, use_sudo=True)
        
        print(f"Configurazione generata per team {team}, player {player}: {client_filename}")
    
    # Salva il file di configurazione del server per il team
    server_filename = f"server_configs/team{team}_server.conf"
    with open(server_filename, "w") as server_file:
        server_file.write(server_config)
    
    # Attiva la configurazione WireGuard per il server
    command = f"wg-quick up {server_filename}"
    run_command(command, use_sudo=True)
    
    num += 1  # Incrementa il numero per differenziare le porte
    print(f"Configurazione server WireGuard generata per team {team}: {server_filename}")




# Funzione principale per gestire sia le macchine virtuali che la configurazione di WireGuard
def setup_infrastructure(num_teams, players_per_team):
    interface_name, server_ip = get_ip_and_interface()
    listen_port_base = 51820  # Porta di partenza, ogni team avrà una porta diversa
    
    # Creazione e configurazione della macchina gamesystem
    setup_vm("gamesystem", "10.10.0.1")
    
    # Creazione delle directory per salvare le configurazioni
    os.makedirs("server_configs", exist_ok=True)
    os.makedirs("client_configs", exist_ok=True)

    # Step 4: Creazione dello script per configurare le interfacce TAP
    tap_script_content = "#!/bin/bash\nsudo iptables -t nat -A POSTROUTING -o wlo1 -j MASQUERADE\n"
    for team in range(1, num_teams + 1):
        vm_ip = generate_vm_ip(team)
        tap_script_content += f"sudo iptables -t nat -A POSTROUTING -d 10.60.{team}.1 -j SNAT --to-source 10.254.0.1\n"
        tap_script_content += f"ip addr add 10.60.{team}.2 dev vulnbox{team}_tap\n"
        tap_script_content += f"ip route add 10.60.{team}.1 dev vulnbox{team}_tap\n"
    tap_script_content += f"ip addr add 10.10.0.2 dev gamesystem_tap"
    tap_script_content += f"ip route add 10.10.0.1 dev gamesystem_tap"

    with open("tap-script.sh", "w") as file:
        file.write(tap_script_content)
    
    run_command("chmod +x tap-script.sh")
    run_command("./tap-script.sh")
    num=0

    # Creazione delle VM e configurazione delle interfacce
    for team in range(1, num_teams + 1):
        vm_name = f"vulnbox{team}"
        vm_ip = generate_vm_ip(team)
        
        # Creazione della VM
        setup_vm(vm_name, vm_ip)

        # Configurazione WireGuard per il team
        setup_wireguard_for_team(team, server_ip, players_per_team, listen_port_base, vm_ip)

    print("Infrastruttura configurata con successo!")

# Esegui lo script
if __name__ == "__main__":
    num_teams = int(input("Inserisci il numero di team: "))
    players_per_team = int(input("Inserisci il numero di giocatori per team: "))

    setup_infrastructure(num_teams, players_per_team)



