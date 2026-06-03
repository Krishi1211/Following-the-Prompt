import os
import json
import time
import requests
import subprocess

ROOT = "/Users/krishi1211/Downloads/CN/Project/Following-the-Prompt"
CACHE_PATH = os.path.join(ROOT, "outputs", "geo_cache.json")
CAIDA_FILE = os.path.join(ROOT, "latest.as-org2info.txt")

SKIP_PREFIXES = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
    "172.30.", "172.31.", "192.168.", "127.", "::1", "fc", "fd",
)

def is_private(ip):
    if not ip:
        return True
    return any(ip.startswith(p) for p in SKIP_PREFIXES) or ip == "0.0.0.0"

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4)
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_caida():
    orgIdToName = {}
    asnToOrgId  = {}
    if os.path.exists(CAIDA_FILE):
        try:
            with open(CAIDA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|")
                    if len(parts) == 5:
                        orgIdToName[parts[0]] = parts[2]
                    elif len(parts) == 6:
                        asnToOrgId[parts[0]] = parts[3]
        except Exception as e:
            print(f"Error loading CAIDA file: {e}")
    return orgIdToName, asnToOrgId

def lookup_caida_org(asn, asnToOrgId, orgIdToName):
    asn_clean = str(asn).replace("AS", "").strip()
    orgId = asnToOrgId.get(asn_clean)
    return orgIdToName.get(orgId, "Unknown Org") if orgId else "Unknown Org"

def query_cymru_dns(ip):
    try:
        reversedIp = ".".join(ip.split(".")[::-1])
        result = subprocess.run(
            ["dig", "+short", "TXT", f"{reversedIp}.origin.asn.cymru.com"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip().strip('"')
        if output:
            asn = output.split("|")[0].strip().split()[0]
            return f"AS{asn}"
        return "Unknown"
    except Exception:
        return "Unknown"

def resolve_ips(ips):
    """
    Resolves a list of unique IPs. Utilizes outputs/geo_cache.json.
    Returns the updated cache.
    """
    cache = load_cache()
    orgIdToName, asnToOrgId = load_caida()
    
    # Identify which IPs need resolution (not private and not in cache)
    to_resolve = []
    for ip in ips:
        if is_private(ip):
            cache[ip] = {
                "private": True,
                "lat": None,
                "lon": None,
                "asn": "Private",
                "org_name": "Private",
                "isp": "Private",
                "city": "Private",
                "country": "Private"
            }
        elif ip not in cache:
            to_resolve.append(ip)

    if not to_resolve:
        print(f"All {len(ips)} IPs are cached or private.")
        return cache

    print(f"Resolving {len(to_resolve)} new IPs via ip-api.com...")
    
    batch_size = 100
    delay = 1.5
    url = "http://ip-api.com/batch"
    fields = "status,query,country,countryCode,city,isp,as,lat,lon"

    for i in range(0, len(to_resolve), batch_size):
        batch = to_resolve[i : i + batch_size]
        payload = [{"query": ip, "fields": fields} for ip in batch]
        
        try:
            resp = requests.post(url, json=payload, timeout=20)
            results = resp.json()
            
            for res in results:
                ip = res.get("query")
                if not ip:
                    continue
                
                if res.get("status") == "success":
                    asn_str = "Unknown"
                    org_name = "Unknown"
                    as_field = res.get("as", "")
                    if as_field:
                        parts = as_field.split()
                        if parts:
                            asn_str = parts[0]
                            org_name = " ".join(parts[1:])
                    
                    # Fallback for ASN organization
                    if asn_str != "Unknown" and org_name == "Unknown":
                        org_name = lookup_caida_org(asn_str, asnToOrgId, orgIdToName)
                    
                    cache[ip] = {
                        "private": False,
                        "lat": res.get("lat"),
                        "lon": res.get("lon"),
                        "asn": asn_str,
                        "org_name": org_name,
                        "isp": res.get("isp", "Unknown"),
                        "city": res.get("city", "Unknown"),
                        "country": res.get("country", "Unknown")
                    }
                else:
                    # Failed lookup
                    cache[ip] = {
                        "private": False,
                        "lat": None,
                        "lon": None,
                        "asn": "Unknown",
                        "org_name": "Unknown",
                        "isp": "Unknown",
                        "city": "Unknown",
                        "country": "Unknown"
                    }
        except Exception as e:
            print(f"Batch lookup failed: {e}")
            # Ensure we don't crash; write partial unknown to resolve later
            for ip in batch:
                if ip not in cache:
                    cache[ip] = {
                        "private": False,
                        "lat": None,
                        "lon": None,
                        "asn": "Unknown",
                        "org_name": "Unknown",
                        "isp": "Unknown",
                        "city": "Unknown",
                        "country": "Unknown"
                    }
        
        print(f"  Resolved {min(i + batch_size, len(to_resolve))}/{len(to_resolve)} IPs")
        if i + batch_size < len(to_resolve):
            time.sleep(delay)

    # Secondary fallback lookup for remaining "Unknown" ASNs via Cymru DNS
    print("Performing fallback ASN resolutions for unknowns...")
    unknown_asns = [ip for ip in ips if ip in cache and cache[ip]["asn"] == "Unknown"]
    if unknown_asns:
        for idx, ip in enumerate(unknown_asns):
            asn = query_cymru_dns(ip)
            if asn != "Unknown":
                cache[ip]["asn"] = asn
                cache[ip]["org_name"] = lookup_caida_org(asn, asnToOrgId, orgIdToName)
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(unknown_asns)} fallback lookups")

    save_cache(cache)
    return cache
