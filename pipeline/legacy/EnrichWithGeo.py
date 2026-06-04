"""
EnrichWithGeo.py — Add country-level geolocation to every traceroute hop.

Reads all ripe_results_*.json files under data/US/ and data/international/,
resolves each hop IP to a country via ip-api.com (free, no key required),
and writes the enriched data alongside the originals.

Output filenames: geo_enriched_ripe_results_<measurementId>.json
(same directory as the source file)

The geo fields added to every packet that has a 'from' IP:
    country       — full country name  e.g. "France"
    country_code  — ISO 3166-1 alpha-2 e.g. "FR"
    city          — city name          e.g. "Paris"
    isp           — ISP/org name       e.g. "Orange S.A."
    asn           — ASN string         e.g. "AS3215"  (if not already present)

After running this script, use AnalyzeJurisdictions.py to compute
border-crossing sequences and surveillance-jurisdiction exposure.

Run from the project root:
    python scripts/EnrichWithGeo.py
"""

import os
import json
import glob
import time
import requests
from collections import defaultdict

# ─── Configuration ────────────────────────────────────────────────────────────

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_ROOT, "data")

# Directories to scan — add more here if needed
SCAN_DIRS = [
    os.path.join(DATA_DIR, "US"),
    os.path.join(DATA_DIR, "international"),
]

IPAPI_URL    = "http://ip-api.com/batch"
IPAPI_FIELDS = "status,query,country,countryCode,city,isp,as"
BATCH_SIZE   = 100    # ip-api.com maximum per POST
BATCH_DELAY  = 1.5    # seconds between batches  (free tier: 45 req/min → stay at ~40)

# IPs in these ranges are private/loopback — skip geo lookup entirely
SKIP_PREFIXES = (
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
    "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
    "172.30.", "172.31.", "192.168.", "127.", "::1", "fc", "fd",
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def isPrivate(ip):
    return any(ip.startswith(p) for p in SKIP_PREFIXES)

def collectUniqueIps(jsonFiles):
    """Walk all result files and gather every unique public hop IP."""
    ips = set()
    for path in jsonFiles:
        with open(path) as f:
            data = json.load(f)
        for probe in data:
            for hop in probe.get("result", []):
                for packet in hop.get("result", []):
                    ip = packet.get("from")
                    if ip and not isPrivate(ip):
                        ips.add(ip)
    return ips

# ─── Geolocation lookup ───────────────────────────────────────────────────────

def lookupBatch(ips):
    """
    POST up to 100 IPs to ip-api.com/batch.
    Returns {ip: geo_dict} for successfully resolved IPs.
    """
    payload = [{"query": ip, "fields": IPAPI_FIELDS} for ip in ips]
    try:
        resp    = requests.post(IPAPI_URL, json=payload, timeout=20)
        results = resp.json()
        return {
            r["query"]: r
            for r in results
            if r.get("status") == "success"
        }
    except Exception as e:
        print(f"\n  [!] Batch lookup failed: {e}")
        return {}

def buildGeoCache(uniqueIps):
    """Resolve all IPs in BATCH_SIZE chunks, respecting the rate limit."""
    ips      = list(uniqueIps)
    total    = len(ips)
    nBatches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    geoCache = {}

    print(f"  Querying ip-api.com: {total} IPs across {nBatches} batch(es) "
          f"(~{nBatches * BATCH_DELAY:.0f}s) ...")

    for i in range(0, total, BATCH_SIZE):
        batch   = ips[i : i + BATCH_SIZE]
        results = lookupBatch(batch)
        geoCache.update(results)
        resolved_so_far = i + len(batch)
        print(f"  [{resolved_so_far:>5}/{total}] resolved", end="\r")
        if resolved_so_far < total:
            time.sleep(BATCH_DELAY)

    hit_rate = len(geoCache) / total * 100 if total else 0
    print(f"\n  Resolved {len(geoCache)}/{total} IPs ({hit_rate:.1f}% hit rate).")
    return geoCache

# ─── Enrichment ───────────────────────────────────────────────────────────────

def enrichFile(filePath, geoCache):
    """
    Annotate every packet in filePath that has a 'from' IP with geo fields.
    Writes result to geo_enriched_ripe_results_<id>.json in the same directory.
    """
    with open(filePath) as f:
        data = json.load(f)

    annotated = 0
    for probe in data:
        for hop in probe.get("result", []):
            for packet in hop.get("result", []):
                ip = packet.get("from")
                if not ip or isPrivate(ip):
                    continue
                geo = geoCache.get(ip)
                if not geo:
                    continue
                packet["country"]      = geo.get("country", "")
                packet["country_code"] = geo.get("countryCode", "")
                packet["city"]         = geo.get("city", "")
                packet["isp"]          = geo.get("isp", "")
                # Add ASN only if not already enriched by EnrichRipeData.py
                if "asn" not in packet and geo.get("as"):
                    # ip-api returns "AS3215 Orange S.A." — strip to just the number
                    packet["asn"] = geo["as"].split()[0]
                annotated += 1

    if "enriched_ripe_results_" in filePath:
        outPath = filePath.replace("enriched_ripe_results_", "geo_enriched_ripe_results_")
    else:
        outPath = filePath.replace("ripe_results_", "geo_enriched_ripe_results_")
    with open(outPath, "w") as f:
        json.dump(data, f, indent=4)

    return outPath, annotated

# ─── Stats helper ─────────────────────────────────────────────────────────────

def printJurisdictionPreview(jsonFiles, geoCache):
    """
    Quick sanity check: for each enriched file show the unique countries
    seen across all hops so the user can immediately see jurisdiction traversal.
    """
    print("\n  Quick jurisdiction preview (countries seen per file):")
    for path in sorted(jsonFiles)[:6]:   # show first 6 as a sample
        with open(path) as f:
            data = json.load(f)
        countries = set()
        for probe in data:
            for hop in probe.get("result", []):
                for packet in hop.get("result", []):
                    ip = packet.get("from")
                    if ip and ip in geoCache:
                        cc = geoCache[ip].get("countryCode", "")
                        if cc:
                            countries.add(cc)
        rel = os.path.relpath(path)
        print(f"    {rel:<55}  {sorted(countries)}")
    if len(jsonFiles) > 6:
        print(f"    ... and {len(jsonFiles) - 6} more files")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    print("AI Routing Project — Geolocation Enrichment (RQ3)\n")

    # ── Gather result files ───────────────────────────────────────────────────
    jsonFiles = []
    for scanDir in SCAN_DIRS:
        if not os.path.isdir(scanDir):
            continue
        found = glob.glob(
            os.path.join(scanDir, "**", "enriched_ripe_results_*.json"),
            recursive=True,
        )
        if not found:
            found = glob.glob(
                os.path.join(scanDir, "**", "ripe_results_*.json"),
                recursive=True,
            )
        jsonFiles.extend(found)
        label = os.path.relpath(scanDir)
        print(f"  {label:<30} {len(found):>4} file(s)")

    if not jsonFiles:
        print("\n[!] No result files found.")
        print("    Run RipeAtlasCollection.py or InternationalCollection.py first.")
        return

    print(f"\n  Total: {len(jsonFiles)} file(s) to enrich.\n")

    # ── Collect unique IPs ────────────────────────────────────────────────────
    print("1. Collecting unique public hop IPs ...")
    uniqueIps = collectUniqueIps(jsonFiles)
    print(f"   Found {len(uniqueIps)} unique public IPs "
          f"(private/loopback IPs skipped).\n")

    # ── Resolve geolocation ───────────────────────────────────────────────────
    print("2. Resolving geolocation via ip-api.com ...")
    geoCache = buildGeoCache(uniqueIps)

    # ── Enrich files ──────────────────────────────────────────────────────────
    print("\n3. Writing enriched files ...")
    totalAnnotated = 0
    for filePath in sorted(jsonFiles):
        outPath, count = enrichFile(filePath, geoCache)
        totalAnnotated += count
        rel = os.path.relpath(outPath)
        print(f"   {rel}  ({count} packets annotated)")

    print(f"\n   Total packets annotated: {totalAnnotated}")

    # ── Quick preview ─────────────────────────────────────────────────────────
    printJurisdictionPreview(jsonFiles, geoCache)

    print("\nDone.")
    print("Enriched files saved as geo_enriched_ripe_results_*.json")
    print("Next: write AnalyzeJurisdictions.py to compute border-crossing stats.")


if __name__ == "__main__":
    main()
