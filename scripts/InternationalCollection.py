"""
InternationalCollection.py — RIPE Atlas collection from international regions (RQ3).

Dispatches one-off ICMP traceroutes to AI API endpoints from probes in
India, Pakistan, Kenya, France, UK, and South Africa. Probes are selected
at runtime by querying the RIPE Atlas API, maximising ASN diversity within
each country.

Results saved to: data/international/<country>/ripe_results_<measurementId>.json

Run from the project root:
    python scripts/InternationalCollection.py
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from ripe.atlas.cousteau import (
    Traceroute,
    AtlasSource,
    AtlasCreateRequest,
    AtlasResultsRequest,
)

# ─── Configuration ────────────────────────────────────────────────────────────

TARGETS = {
    "ChatGPT": "api.openai.com",
    "Gemini":  "generativelanguage.googleapis.com",
    "Claude":  "api.anthropic.com",
}

# Countries to measure — probe cap is per-country.
# Pakistan and Kenya have very few probes available globally so we take all of them.
COUNTRIES = {
    "India":        {"code": "IN", "cap": 10},
    "Pakistan":     {"code": "PK", "cap": 10},   # only 4 exist — takes all
    "Kenya":        {"code": "KE", "cap": 15},   # ~11 exist — takes all
    "France":       {"code": "FR", "cap": 10},
    "UK":           {"code": "GB", "cap": 10},
    "South Africa": {"code": "ZA", "cap": 10},
}

WAIT_TIME = 180   # seconds to wait for probes to execute before fetching

DATA_DIR  = "data"
INTL_DIR  = os.path.join(DATA_DIR, "international")

# ─── Auth ─────────────────────────────────────────────────────────────────────

def getApiKey():
    load_dotenv()
    key = os.environ.get("RIPE_ATLAS_API_KEY")
    if not key:
        key = input("Please enter your RIPE Atlas API Key: ").strip()
    return key

# ─── Probe Selection ──────────────────────────────────────────────────────────

def fetchDiverseProbes(countryCode, cap):
    """
    Query RIPE Atlas for connected public probes in a country.
    Selects up to `cap` probes, picking at most one per ASN to maximise
    network diversity. Falls back to including probes with unknown ASNs
    if needed to meet the cap.
    """
    url = (
        f"https://atlas.ripe.net/api/v2/probes/"
        f"?country_code={countryCode}&status=1&is_public=true&limit=500"
    )
    try:
        resp   = requests.get(url, timeout=15)
        probes = resp.json().get("results", [])
    except Exception as e:
        print(f"  [!] Failed to fetch probes for {countryCode}: {e}")
        return []

    seen_asns  = set()
    first_pass = []   # one per unique ASN
    overflow   = []   # extras (same ASN) used only if we're still under cap

    for probe in probes:
        asn = probe.get("asn_v4") or probe.get("asn_v6")
        if asn and asn not in seen_asns:
            first_pass.append(str(probe["id"]))
            seen_asns.add(asn)
        else:
            overflow.append(str(probe["id"]))

    selected = first_pass[:cap]
    if len(selected) < cap:
        selected += overflow[: cap - len(selected)]

    return selected

# ─── Measurement ──────────────────────────────────────────────────────────────

def triggerTraceroute(targetDomain, apiKey, probeIds):
    sources = [AtlasSource(
        type="probes",
        value=",".join(probeIds),
        requested=len(probeIds),
    )]
    traceroute = Traceroute(
        af=4,
        target=targetDomain,
        description=f"AI Routing RQ3: Traceroute to {targetDomain}",
        protocol="ICMP",
    )
    req = AtlasCreateRequest(
        start_time=datetime.utcnow(),
        key=apiKey,
        measurements=[traceroute],
        sources=sources,
        is_oneoff=True,
    )
    print(f"    Submitting → {targetDomain} ...")
    isSuccess, response = req.create()
    if isSuccess:
        mid = response["measurements"][0]
        print(f"    Success — ID: {mid}")
        return mid
    print(f"    Failed: {response}")
    return None

def fetchAndSave(measurementId, country):
    print(f"    Fetching ID {measurementId} ...")
    isSuccess, response = AtlasResultsRequest(msm_id=measurementId).create()

    if not isSuccess or not response:
        status = "failed" if not isSuccess else "no results yet"
        print(f"    [{status}] — try fetching manually later.")
        return False

    countryDir = os.path.join(INTL_DIR, country)
    os.makedirs(countryDir, exist_ok=True)
    filePath = os.path.join(countryDir, f"ripe_results_{measurementId}.json")
    with open(filePath, "w") as f:
        json.dump(response, f, indent=4)
    print(f"    [{country}] {len(response)} result(s) → {filePath}")
    return True

# ─── Persistence ──────────────────────────────────────────────────────────────

def saveMappingFile(measurementIds, probeIds):
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload   = {
        "measurements": measurementIds,
        "probes_used":  probeIds,
    }
    path = os.path.join(DATA_DIR, f"ripe_intl_mapping_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=4)
    print(f"\nMapping saved → {path}")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def runCollection():
    print("AI Routing Project — International RIPE Atlas Collection (RQ3)\n")

    apiKey = getApiKey()
    if not apiKey:
        print("[!] API key required. Exiting.")
        return

    # ── Phase 0: Probe discovery ───────────────────────────────────────────────
    print("--- Selecting probes (ASN-diverse) ---")
    countryProbeIds = {}

    for country, cfg in COUNTRIES.items():
        probeIds = fetchDiverseProbes(cfg["code"], cfg["cap"])
        if not probeIds:
            print(f"  {country}: no probes found — skipping.")
            continue
        countryProbeIds[country] = probeIds
        print(f"  {country:<15} {len(probeIds):>2} probes  "
              f"[{', '.join(probeIds[:4])}{'...' if len(probeIds) > 4 else ''}]")

    if not countryProbeIds:
        print("[!] No countries available. Exiting.")
        return

    # ── Phase 1: Trigger all measurements ────────────────────────────────────
    print("\n--- Phase 1: Triggering measurements ---")
    # measurementIds[country][service] = {"measurement_id": int, "domain": str}
    measurementIds = {}

    for country, probeIds in countryProbeIds.items():
        print(f"\n[{country}]  ({len(probeIds)} probes)")
        measurementIds[country] = {}
        for service, domain in TARGETS.items():
            mid = triggerTraceroute(domain, apiKey, probeIds)
            if mid:
                measurementIds[country][service] = {
                    "measurement_id": mid,
                    "domain":         domain,
                }
            time.sleep(2)   # avoid rate-limiting

    saveMappingFile(measurementIds, countryProbeIds)

    # ── Phase 2: Wait ─────────────────────────────────────────────────────────
    print(f"\n--- Phase 2: Waiting {WAIT_TIME}s for probes to complete ---")
    time.sleep(WAIT_TIME)

    # ── Phase 3: Fetch results ────────────────────────────────────────────────
    print("\n--- Phase 3: Fetching results ---")
    for country, services in measurementIds.items():
        print(f"\n[{country}]")
        for service, info in services.items():
            mid    = info["measurement_id"]
            domain = info["domain"]
            print(f"  {service} / {domain}")
            fetchAndSave(mid, country)
            time.sleep(1)

    print(f"\nCollection complete. Results under: {INTL_DIR}/<country>/")
    print("Next step: run EnrichWithGeo.py to add country-level hop geolocation.")


if __name__ == "__main__":
    runCollection()
