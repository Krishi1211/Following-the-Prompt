import json
import subprocess

sample = {
  "prb_id": 1008859,
  "msm_id": 171902971,
  "timestamp": 1779148291,
  "src": "206.127.64.139",
  "dst": "172.64.150.28",
  "hops": [
    {"h": 1, "ip": "206.127.64.129", "rtt": 0.96},
    {"h": 2, "ip": "206.127.109.180", "rtt": 0.52},
    {"h": 3, "ip": "209.133.55.242", "rtt": 15.57},
    {"h": 4, "ip": "*"},
    {"h": 5, "ip": "64.125.31.52", "rtt": 35.35, "mpls": [271546, 173888]},
    {"h": 6, "ip": "64.125.25.235", "rtt": 38.38, "mpls": [173888]},
    {"h": 7, "ip": "64.125.25.75", "rtt": 35.04},
    {"h": 8, "ip": "208.184.122.49", "rtt": 35.57},
    {"h": 9, "ip": "141.101.73.110", "rtt": 35.00},
    {"h": 10, "ip": "141.101.73.161", "rtt": 38.66},
    {"h": 11, "ip": "172.64.150.28", "rtt": 35.32}
  ]
}

as_org_file = "../latest.as-org2info.txt"
org_id_to_name = {}
asn_to_org_id = {}
with open(as_org_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split('|')
        if len(parts) == 5:
            org_id_to_name[parts[0]] = parts[2]
        elif len(parts) == 6:
            asn_to_org_id[parts[0]] = parts[3]

def get_org(asn):
    asn = str(asn).replace('AS', '')
    if asn in asn_to_org_id:
        return org_id_to_name.get(asn_to_org_id[asn], "Unknown Org")
    return "Unknown Org"

def get_asn(ip):
    try:
        reversed_ip = '.'.join(ip.split('.')[::-1])
        query = f"{reversed_ip}.origin.asn.cymru.com"
        res = subprocess.run(['dig', '+short', 'TXT', query], capture_output=True, text=True).stdout.strip().strip('"')
        if res:
            return res.split('|')[0].strip().split()[0]
        return "Unknown"
    except:
        return "Unknown"

for hop in sample["hops"]:
    ip = hop["ip"]
    if ip != "*":
        asn = get_asn(ip)
        hop["asn"] = asn
        hop["org_name"] = get_org(asn)

print(json.dumps(sample, indent=2))
