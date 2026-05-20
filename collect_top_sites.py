import subprocess
import socket
import json
import time
from datetime import datetime
import os

def get_dns_info(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except Exception as e:
        return str(e)

def run_traceroute(domain):
    try:
        print(f"  -> Running traceroute to {domain}...")
        result = subprocess.run(['traceroute', '-m', '30', '-q', '1', '-w', '2', domain], 
                                capture_output=True, text=True, timeout=60)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return str(e)

def collect_data():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    network_name = "comcast"
    
    # Load targets from JSON
    with open("top_sites.json", "r") as f:
        targets = json.load(f)

    results = {
        "timestamp": datetime.now().isoformat(),
        "network": network_name,
        "targets": {}
    }
    
    for category, domains in targets.items():
        results["targets"][category] = {}
        for domain in domains:
            print(f"[{network_name}] Testing {category} - {domain}...")
            ip = get_dns_info(domain)
            trace = run_traceroute(domain)
            
            results["targets"][category][domain] = {
                "resolved_ip": ip,
                "traceroute": trace
            }
            time.sleep(1) # Polite delay
            
    # Save the output to a JSON file
    filename = f"local_collection_top_sites_{network_name}_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nData collection complete. Results saved to {filename}")

if __name__ == "__main__":
    collect_data()
