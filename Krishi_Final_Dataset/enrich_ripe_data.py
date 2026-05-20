import json
import glob
import subprocess
import concurrent.futures
import os

print("1. Parsing CAIDA AS2Org Dataset...")
as_org_file = "../latest.as-org2info.txt"

org_id_to_name = {}
asn_to_org_id = {}

with open(as_org_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split('|')
        
        # Format: org_id|changed|org_name|country|source
        if len(parts) == 5:
            org_id_to_name[parts[0]] = parts[2]
            
        # Format: aut|changed|aut_name|org_id|opaque_id|source
        elif len(parts) == 6:
            asn_to_org_id[parts[0]] = parts[3]

def get_org_for_asn(asn):
    asn = str(asn).replace('AS', '')
    if asn in asn_to_org_id:
        org_id = asn_to_org_id[asn]
        return org_id_to_name.get(org_id, "Unknown Org")
    return "Unknown Org"

def get_asn_for_ip(ip):
    try:
        reversed_ip = '.'.join(ip.split('.')[::-1])
        query = f"{reversed_ip}.origin.asn.cymru.com"
        result = subprocess.run(['dig', '+short', 'TXT', query], capture_output=True, text=True)
        output = result.stdout.strip().strip('"')
        if output:
            parts = [p.strip() for p in output.split('|')]
            asn = parts[0].split()[0] # Sometimes returns multiple ASNs, take first
            return asn
        return "Unknown"
    except:
        return "Unknown"

print("2. Finding unique IPs across all JSONs...")
json_files = glob.glob("ripe_results_*.json")
unique_ips = set()

for file in json_files:
    with open(file, 'r') as f:
        data = json.load(f)
        for probe in data:
            if "result" in probe:
                for hop in probe["result"]:
                    if "result" in hop:
                        for packet in hop["result"]:
                            if "from" in packet:
                                unique_ips.add(packet["from"])

print(f"Found {len(unique_ips)} unique IPs. Resolving ASNs via Cymru (this might take a minute)...")
ip_cache = {}

# Batch resolve using ThreadPool
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    future_to_ip = {executor.submit(get_asn_for_ip, ip): ip for ip in unique_ips}
    for future in concurrent.futures.as_completed(future_to_ip):
        ip = future_to_ip[future]
        try:
            asn = future.result()
            org = get_org_for_asn(asn)
            ip_cache[ip] = {"asn": asn, "org_name": org}
        except Exception as exc:
            ip_cache[ip] = {"asn": "Unknown", "org_name": "Unknown"}

print("3. Enriching JSON files with BGP and CAIDA data...")
for file in json_files:
    print(f"Enriching {file}...")
    with open(file, 'r') as f:
        data = json.load(f)
        
    for probe in data:
        if "result" in probe:
            for hop in probe["result"]:
                if "result" in hop:
                    for packet in hop["result"]:
                        if "from" in packet:
                            ip = packet["from"]
                            if ip in ip_cache:
                                packet["asn"] = ip_cache[ip]["asn"]
                                packet["org_name"] = ip_cache[ip]["org_name"]
                                
    # Save enriched file
    enriched_name = f"enriched_{file}"
    with open(enriched_name, 'w') as f:
        json.dump(data, f, indent=4)

print("✅ All data successfully enriched! (Saved as 'enriched_*.json')")



