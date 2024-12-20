import os
import base64
import xml.etree.ElementTree as ET
import json
import argparse

def parse_unl_config(file_path, output_folder):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"XML parsing error in file {file_path}: {e}")
        return

    topology = {"nodes": {}, "routers": {}}

    # Create a mapping of `network_id` to their names
    network_map = {}
    for network in root.findall(".//network"):
        network_id = network.get('id')
        network_name = network.get('name', f"Network_{network_id}")
        network_map[network_id] = network_name

    # Look for the <configs> section
    configs_section = None
    for elem in root.iter():
        if elem.tag == 'configs':
            configs_section = elem
            break

    # Initialize router configurations
    router_configs = {}
    if configs_section is not None:
        # Decode base64 configurations, only if <configs> exists
        for config in configs_section.findall('config'):
            config_id = config.get('id')
            encoded_config = config.text

            try:
                decoded_config = base64.b64decode(encoded_config).decode('utf-8')
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                print(f"Decoding error for node {config_id}: {e}")
                continue

            router_config_dict = parse_config_text(decoded_config)
            router_configs[config_id] = router_config_dict
    else:
        print(f"Warning: <configs> section missing in file {file_path}")

    # Add node information and organize it by "nodes"
    for node in root.findall(".//node"):
        node_id = node.get('id')
        node_name = node.get('name', 'Unknown')
        icon = node.get('icon', '')
        interfaces = {}

        for interface in node.findall(".//interface"):
            interface_id = interface.get('id')
            interface_name = interface.get('name', f"e{len(interfaces)}")
            network_id = interface.get('network_id')
            network_name = network_map.get(network_id, "Unknown Network")

            interfaces[interface_name] = {
                "id": interface_id,
                "name": interface_name,
                "network_id": network_id,
                "network_name": network_name
            }

        topology["nodes"][node_id] = {
            "name": node_name,
            "icon": icon,
            "interfaces": interfaces
        }

        # If it is a router, based on its icon, add it to the "routers" section
        if icon == "Router.png":
            if node_id in router_configs:
                router_configs[node_id]["name"] = node_name
                topology["routers"][node_id] = router_configs[node_id]
            else:
                topology["routers"][node_id] = {
                    "config": "Missing configuration",
                    "name": node_name
                }

    # Determine the output file name
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(output_folder, f"{base_name}.json")

    # Save to a JSON file
    os.makedirs(output_folder, exist_ok=True)
    with open(output_file, "w") as json_file:
        json.dump(topology, json_file, indent=4)
    print(f"JSON file saved: {output_file}")

def parse_config_text(config_text):
    config_dict = {
        "version": None,
        "hostname": None,
        "interfaces": {},
        "routing": {
            "rip": {
                "version": None,
                "redistribute_connected": False,
                "redistribute_static": False,
                "flash_update_threshold": None,
                "network": None
            }
        },
        "static_routes": [],
        "dhcp_pools": {},
        "protocols": {"ip_forward": None},
        "lines": {
            "console": {"logging_synchronous": False},
            "vty": {"login": False, "transport_input": None},
        },
        "settings": {
            "service_timestamps": {},
            "password_encryption": False,
            "clock_timezone": None,
        },
    }

    lines = config_text.splitlines()
    current_interface = None
    current_pool = None
    in_rip_section = False

    for line in lines:
        line = line.strip()

        if line.startswith("version") and not in_rip_section:
            config_dict["version"] = line.split()[1]

        elif line.startswith("router rip"):
            in_rip_section = True
            config_dict["routing"]["rip"]["version"] = 2

        elif in_rip_section and line.startswith("!"):
            in_rip_section = False

        elif in_rip_section:
            if "redistribute connected" in line:
                config_dict["routing"]["rip"]["redistribute_connected"] = True
            elif "redistribute static" in line:
                config_dict["routing"]["rip"]["redistribute_static"] = True
            elif line.startswith("network"):
                config_dict["routing"]["rip"]["network"] = line.split()[1]
            elif "flash-update-threshold" in line:
                config_dict["routing"]["rip"]["flash_update_threshold"] = line.split()[-1]

        elif line.startswith("ip route"):
            config_dict["static_routes"].append(line.split("ip route")[1].strip())
        elif line.startswith("ipv6 route"):
            config_dict["static_routes"].append(line.split("ipv6 route")[1].strip())

        elif line.startswith("ip dhcp pool"):
            current_pool = line.split("ip dhcp pool")[1].strip()
            config_dict["dhcp_pools"][current_pool] = {}
        elif current_pool and line.startswith("network"):
            config_dict["dhcp_pools"][current_pool]["network"] = line.split("network")[1].strip()
        elif current_pool and line.startswith("default-router"):
            config_dict["dhcp_pools"][current_pool]["default_router"] = line.split("default-router")[1].strip()
        elif current_pool and line.startswith("dns-server"):
            config_dict["dhcp_pools"][current_pool]["dns_server"] = line.split("dns-server")[1].strip()
        elif current_pool and line == "!":
            current_pool = None

        elif line.startswith("hostname"):
            config_dict["hostname"] = line.split()[1]

        elif line.startswith("service timestamps"):
            parts = line.split()
            if "debug" in parts:
                config_dict["settings"]["service_timestamps"]["debug"] = " ".join(parts[2:])
            if "log" in parts:
                config_dict["settings"]["service_timestamps"]["log"] = " ".join(parts[2:])
        elif line == "no service password-encryption":
            config_dict["settings"]["password_encryption"] = False
        elif line.startswith("clock timezone"):
            config_dict["settings"]["clock_timezone"] = " ".join(line.split()[2:])

        elif line.startswith("interface"):
            current_interface = line.split()[1]
            config_dict["interfaces"][current_interface] = {}
        elif current_interface:
            if line == "no shutdown":
                config_dict["interfaces"][current_interface]["status"] = "no shutdown"
            elif "description" in line:
                config_dict["interfaces"][current_interface]["description"] = line.split("description")[1].strip()
            elif "ip address dhcp" in line:
                config_dict["interfaces"][current_interface]["ip_address"] = "dhcp"
            elif "ip address" in line:
                config_dict["interfaces"][current_interface]["ip_address"] = " ".join(line.split()[2:])
            elif "ipv6 address" in line:
                config_dict["interfaces"][current_interface]["ipv6_address"] = line.split()[2]
            elif line == "shutdown":
                config_dict["interfaces"][current_interface]["status"] = "shutdown"

        elif line == "ip forward-protocol nd":
            config_dict["protocols"]["ip_forward"] = "nd"

        elif line.startswith("line con"):
            config_dict["lines"]["console"]["logging_synchronous"] = "logging synchronous" in line
        elif line.startswith("line vty"):
            config_dict["lines"]["vty"]["login"] = "login" in line
            config_dict["lines"]["vty"]["transport_input"] = line.split()[-1] if "transport input" in line else None

    return config_dict

def parse_unl_files_in_folder(source_folder, output_folder):
    if not os.path.exists(source_folder):
        print(f"The source folder '{source_folder}' does not exist.")
        return

    unl_files = [f for f in os.listdir(source_folder) if f.endswith(".unl")]

    if not unl_files:
        print(f"No .unl files found in the folder '{source_folder}'.")
        return

    print(f"Found {len(unl_files)} .unl file(s) in the folder '{source_folder}'.")

    for unl_file in unl_files:
        file_path = os.path.join(source_folder, unl_file)
        parse_unl_config(file_path, output_folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse .unl files and save as JSON.")
    parser.add_argument("--source-dir", required=True, help="Folder containing the .unl files.")
    parser.add_argument("--output-dir", required=True, help="Folder where JSON files will be saved.")

    args = parser.parse_args()

    parse_unl_files_in_folder(args.source_dir, args.output_dir)
