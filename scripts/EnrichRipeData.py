import json
import glob
import re
import subprocess
import concurrent.futures
import os

# ─── Configuration ────────────────────────────────────────────────────────────

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAIDA_FILE = os.path.join(_ROOT, "latest.as-org2info.txt")
DATA_DIR   = os.path.join(_ROOT, "data")

# ─── CAIDA Dataset ────────────────────────────────────────────────────────────

def loadCaidaDataset(filePath):
    orgIdToName = {}
    asnToOrgId  = {}
    with open(filePath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) == 5:               # org record
                orgIdToName[parts[0]] = parts[2]
            elif len(parts) == 6:             # ASN record
                asnToOrgId[parts[0]] = parts[3]
    return orgIdToName, asnToOrgId

def lookupOrgForAsn(asn, asnToOrgId, orgIdToName):
    asn = str(asn).replace("AS", "")
    orgId = asnToOrgId.get(asn)
    return orgIdToName.get(orgId, "Unknown Org") if orgId else "Unknown Org"

# ─── IP → ASN Lookup (Cymru DNS) ─────────────────────────────────────────────

def queryAsnForIp(ip):
    """Returns the ASN string for an IP via Team Cymru's DNS service."""
    try:
        reversedIp = ".".join(ip.split(".")[::-1])
        result = subprocess.run(
            ["dig", "+short", "TXT", f"{reversedIp}.origin.asn.cymru.com"],
            capture_output=True, text=True,
        )
        output = result.stdout.strip().strip('"')
        if output:
            return output.split("|")[0].strip().split()[0]
        return "Unknown"
    except Exception:
        return "Unknown"

def queryAsnAndOrgForIp(ip):
    """Full lookup: returns (asn, bgpPrefix, orgName) using only Cymru DNS."""
    try:
        reversedIp = ".".join(ip.split(".")[::-1])
        asnOutput = subprocess.run(
            ["dig", "+short", "TXT", f"{reversedIp}.origin.asn.cymru.com"],
            capture_output=True, text=True,
        ).stdout.strip().strip('"')

        asn, prefix = "Unknown", ""
        if asnOutput:
            parts  = [p.strip() for p in asnOutput.split("|")]
            asn    = parts[0].split()[0]
            prefix = parts[1] if len(parts) > 1 else ""

        orgOutput = subprocess.run(
            ["dig", "+short", "TXT", f"AS{asn}.asn.cymru.com"],
            capture_output=True, text=True,
        ).stdout.strip().strip('"')

        orgName = ""
        if orgOutput:
            orgParts = [p.strip() for p in orgOutput.split("|")]
            if len(orgParts) >= 5:
                orgName = orgParts[4]

        return asn, prefix, orgName
    except Exception as e:
        return "Error", "", str(e)

# ─── IP Extraction ────────────────────────────────────────────────────────────

def extractIpsFromTraceroute(tracerouteText):
    """Extract unique IPv4 addresses from raw traceroute stdout, preserving order."""
    ipPattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
    seen = {}
    for line in tracerouteText.splitlines():
        for ip in ipPattern.findall(line):
            seen.setdefault(ip, None)
    return list(seen)

# ─── Enrichment Pipeline ──────────────────────────────────────────────────────

def collectUniqueIps(jsonFiles):
    uniqueIps = set()
    for filePath in jsonFiles:
        with open(filePath, "r") as f:
            data = json.load(f)
        for probe in data:
            for hop in probe.get("result", []):
                for packet in hop.get("result", []):
                    if "from" in packet:
                        uniqueIps.add(packet["from"])
    return uniqueIps

def buildIpCache(uniqueIps, asnToOrgId, orgIdToName):
    ipCache = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futureToIp = {executor.submit(queryAsnForIp, ip): ip for ip in uniqueIps}
        for future in concurrent.futures.as_completed(futureToIp):
            ip = futureToIp[future]
            try:
                asn = future.result()
                org = lookupOrgForAsn(asn, asnToOrgId, orgIdToName)
                ipCache[ip] = {"asn": asn, "org_name": org}
            except Exception:
                ipCache[ip] = {"asn": "Unknown", "org_name": "Unknown"}
    return ipCache

def enrichFile(filePath, ipCache):
    with open(filePath, "r") as f:
        data = json.load(f)
    for probe in data:
        for hop in probe.get("result", []):
            for packet in hop.get("result", []):
                ip = packet.get("from")
                if ip and ip in ipCache:
                    packet["asn"]      = ipCache[ip]["asn"]
                    packet["org_name"] = ipCache[ip]["org_name"]
    enrichedName = os.path.basename(filePath).replace("ripe_results_", "enriched_ripe_results_")
    enrichedPath = os.path.join(os.path.dirname(filePath), enrichedName)
    with open(enrichedPath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"  Saved → {enrichedPath}")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(CAIDA_FILE):
        print(f"[!] CAIDA dataset not found: '{CAIDA_FILE}'")
        print("    Download from https://www.caida.org/catalog/datasets/as-organizations/")
        print("    and place it in the project root as 'latest.as-org2info.txt'.")
        return

    print("1. Parsing CAIDA AS2Org dataset...")
    orgIdToName, asnToOrgId = loadCaidaDataset(CAIDA_FILE)

    print("2. Collecting unique IPs from result files...")
    jsonFiles = glob.glob(os.path.join(DATA_DIR, "**", "ripe_results_*.json"), recursive=True)
    if not jsonFiles:
        print(f"[!] No raw RIPE result files found in {DATA_DIR}")
        return

    uniqueIps = collectUniqueIps(jsonFiles)
    print(f"   Found {len(uniqueIps)} unique IPs — resolving ASNs via Cymru DNS...")

    ipCache = buildIpCache(uniqueIps, asnToOrgId, orgIdToName)

    print("3. Writing enriched JSON files...")
    for filePath in jsonFiles:
        print(f"  Enriching {filePath}...")
        enrichFile(filePath, ipCache)

    print("\nDone. All files enriched (saved as 'enriched_ripe_results_*.json').")


if __name__ == "__main__":
    main()
