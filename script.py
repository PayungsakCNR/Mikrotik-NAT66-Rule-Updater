import os
from dotenv import load_dotenv
import requests
import json
from requests.auth import HTTPBasicAuth


load_dotenv()

# MikroTik API credentials
HOST = "<mikrotik-ipv4-address>:<www-port>"
USERNAME = os.getenv('MIKROTIK_WEB_API_ADMIN')
PASSWORD = os.getenv('MIKROTIK_WEB_API_PASSWORD')

# MikroTik REST API URL
BASE_URL = f"http://{HOST}/rest"

# Disable SSL warnings (only use for testing)
requests.packages.urllib3.disable_warnings()

def get_ipv6_addresses():
    """Retrieve all IPv6 addresses from MikroTik"""
    response = requests.get(f"{BASE_URL}/ipv6/address", auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False)

    #print(response.json())

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching IPv6 addresses: {response.text}")
        return []

def find_ipv6_for_interface():
    TARGET_INTERFACE = "bridge3-ais-fibre-v6" #Change to your bridge interface name
    """Find IPv6 address for the specified interface"""
    addresses = get_ipv6_addresses()

    for addr in addresses:
        if addr.get("interface") == TARGET_INTERFACE and addr.get("comment") == "AIS-Fibre-v6-Pool":
            #print(f"Interface: {addr['interface']}, IPv6 Address: {addr['address']}")
            if addr["address"].startswith("2405:9800:"): ##Check correct AIS Fibre Prefix
                return addr["address"]
            else:
                return "fc00::1/64" ##Return dummy address.

def get_ipv6_nat_rules():
    """Retrieve IPv6 NAT rules from MikroTik"""
    response = requests.get(f"{BASE_URL}/ipv6/firewall/nat", auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching rules: {response.text}")
        return []

def update_ipv6_nat_rule(rule_id,src_nat66_prefix):
    """Update the specified IPv6 NAT rule"""
    update_data = {
        "to-address": src_nat66_prefix,
    }

    response = requests.patch(f"{BASE_URL}/ipv6/firewall/nat/{rule_id}", 
                              auth=HTTPBasicAuth(USERNAME, PASSWORD),
                              headers={"Content-Type": "application/json"},
                              data=json.dumps(update_data),
                              verify=False)

    if response.status_code == 200:
        print(f"Updated rule {rule_id} successfully.")
    else:
        print(f"Error updating rule: {response.text}")
        print("HTTP Res Code : " + response.status_code)

def main():
    print("Address from Interface:")
    print(find_ipv6_for_interface())
    ais_fibre_v6_address = find_ipv6_for_interface()
    src_nat66_prefix = ais_fibre_v6_address[:-4] + "/64"
    print("AIS Fibre Prefix : " + src_nat66_prefix)

    # Get IPv6 NAT rules
    rules = get_ipv6_nat_rules()

    for rule in rules:
        if rule.get("chain") == "srcnat" and rule.get("comment") == "SRC-NAT66-AIS-FIBRE":
            rule_id = rule[".id"]  # Get rule ID
            print("Prefix from NAT66 Rule : " + rule["to-address"])
            if(src_nat66_prefix.startswith("2405:9800") and rule["to-address"] != src_nat66_prefix):
                print(f"Updating rule ID: {rule_id}")
                update_ipv6_nat_rule(rule_id,src_nat66_prefix)
                return
            else:
                print("Same prefix from interface and nat rule , Do not update NAT66 rule !!")
                return

    print("No IPv6 srcnat rule found.")

if __name__ == "__main__":
    main()
