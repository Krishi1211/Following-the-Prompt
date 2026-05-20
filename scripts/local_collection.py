import subprocess
import socket
import json
import time
from datetime import datetime
import os

# Define the targets to measure
TARGETS = {
    "ChatGPT": ["chat.openai.com", "api.openai.com"],
    "Gemini": ["gemini.google.com", "generativelanguage.googleapis.com"],
    "Claude": ["claude.ai", "api.anthropic.com"]
}

def get_dns_info(domain):
    try:
        # Get the IP address the domain resolves to on this network
        ip = socket.gethostbyname(domain)
        return ip
    except Exception as e:
        return str(e)

def run_traceroute(domain):
    try:
        # Run standard mac/linux traceroute
        # -m 30: max 30 hops
        # -q 1: 1 probe per hop (speeds it up)
        # -w 2: wait 2 secs for response
        print(f"  -> Running traceroute to {domain}...")
        result = subprocess.run(['traceroute', '-m', '30', '-q', '1', '-w', '2', domain], 
                                capture_output=True, text=True, timeout=60)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return str(e)

def collect_local_data(network_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "timestamp": datetime.now().isoformat(),
        "network": network_name,
        "targets": {}
    }
    
    for service, domains in TARGETS.items():
        results["targets"][service] = {}
        for domain in domains:
            print(f"[{network_name}] Testing {service} - {domain}...")
            ip = get_dns_info(domain)
            trace = run_traceroute(domain)
            
            results["targets"][service][domain] = {
                "resolved_ip": ip,
                "traceroute": trace
            }
            time.sleep(2) # Polite delay
            
    # Save the output to a JSON file
    filename = f"local_collection_{network_name}_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nData collection complete. Results saved to {filename}")

if __name__ == "__main__":
    print("AI Routing Project: Local Data Collection")
    network = input("Enter current network name (e.g., college_wifi, xfinity, tmobile): ").strip()
    if not network:
        network = "unknown_network"
    collect_local_data(network)
