import os
import json
import time
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
    "ChatGPT": ["chat.openai.com", "api.openai.com"],
    "Gemini":  ["gemini.google.com", "generativelanguage.googleapis.com"],
    "Claude":  ["claude.ai", "api.anthropic.com"],
}

MEMBER_REGIONS = {
    "1": [AtlasSource(type="probes", value="3588,51310,60259,28,7363,7449,3328,7549,17218,32,125,307,1058,4160,4851,3483,3671,12721,6408,7159,10456,202,6835,7523,34313,54871,60255,10507,25206,52650,15038,27310,55734,50128,55078,61588,6373,6884,6925", requested=39)],
    "2": [AtlasSource(type="probes", value="14720,19053,61465,22803,55484,63081,12159,35140,1004380,1121,6437,6692,4085,6565,6597,7087,50084,50168,13397,29049,55630,1001471,1012465,1012466,54785,55260,60888,12180,60886,61246,7256,23087,52645,1184,7719,10286,6389,7105,7691", requested=39)],
    "3": [AtlasSource(type="probes", value="20756,21031,1008859,4325,50344,52196,54286,54939,62023,6783,6946,6972,1113,1160,4958,801,6634,7374,16896,19551,21791,1127,7368,11529,1142,3756,4069,21087,24836,51343,1169,3715,7014,10357,20683,54280", requested=36)],
    "4": [AtlasSource(type="probes", value="7643,10342,15979,12334,33081,53308,4405,10443,10473,6452,6590,6643,6436,6574,6644,3660,4894,6454,23714,51354,51440,4969,6379,7692,7224,7728,10553,51140,4551,6875,10146,7672,13159,13288", requested=34)],
}

MEMBER_NAMES = {
    "1": "Aryan  (West / Central — 13 states / 39 Probes)",
    "2": "Ashay  (South / Midwest — 13 states / 39 Probes)",
    "3": "Krishi (North / Mid-Atlantic — 12 states / 36 Probes)",
    "4": "Urmil  (East Coast / New England — 12 states / 36 Probes)",
}

WAIT_TIME = 180  # seconds to wait for probes to complete

# ─── Auth ─────────────────────────────────────────────────────────────────────

def getApiKey():
    load_dotenv()
    apiKey = os.environ.get("RIPE_ATLAS_API_KEY")
    if not apiKey:
        apiKey = input("Please enter your RIPE Atlas API Key: ").strip()
    return apiKey

# ─── Measurement ──────────────────────────────────────────────────────────────

def triggerTraceroute(targetDomain, apiKey, sources):
    traceroute = Traceroute(
        af=4,
        target=targetDomain,
        description=f"AI Routing Project: Traceroute to {targetDomain}",
        protocol="ICMP",
    )
    atlasRequest = AtlasCreateRequest(
        start_time=datetime.utcnow(),
        key=apiKey,
        measurements=[traceroute],
        sources=sources,
        is_oneoff=True,
    )
    print(f"  Submitting measurement for {targetDomain}...")
    isSuccess, response = atlasRequest.create()
    if isSuccess:
        measurementId = response["measurements"][0]
        print(f"  Success! Measurement ID: {measurementId}")
        return measurementId
    print(f"  Failed: {response}")
    return None

def fetchResults(measurementId):
    print(f"  Fetching results for ID {measurementId}...")
    isSuccess, response = AtlasResultsRequest(msm_id=measurementId).create()
    if not isSuccess:
        print(f"  Failed to fetch results for {measurementId}.")
        return False, None
    if not response:
        print(f"  No results yet for {measurementId}.")
        return False, None
    filePath = f"data/ripe_results_{measurementId}.json"
    with open(filePath, "w") as f:
        json.dump(response, f, indent=4)
    print(f"  Saved → {filePath}")
    return True, response

# ─── Persistence ──────────────────────────────────────────────────────────────

def saveMeasurementMapping(measurementIds):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mappingFile = f"data/ripe_measurement_mapping_{timestamp}.json"
    with open(mappingFile, "w") as f:
        json.dump(measurementIds, f, indent=4)
    print(f"Measurement mapping saved → {mappingFile}")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def runCollection():
    print("AI Routing Project: Global RIPE Atlas Data Collection\n")

    apiKey = getApiKey()
    if not apiKey:
        print("[!] API Key is required. Exiting.")
        return

    print("Select your name to target your assigned US states:")
    for key, label in MEMBER_NAMES.items():
        print(f"  {key}. {label}")
    choice = input("Enter number (1-4): ").strip()

    sources = MEMBER_REGIONS.get(choice)
    if not sources:
        print("[!] Invalid choice. Exiting.")
        return

    # Phase 1: Trigger all measurements
    print("\n--- Phase 1: Triggering Measurements ---")
    measurementIds = {}
    for service, domains in TARGETS.items():
        measurementIds[service] = {}
        for domain in domains:
            mId = triggerTraceroute(domain, apiKey, sources)
            if mId:
                measurementIds[service][domain] = mId
            time.sleep(2)  # avoid rate limits

    if not any(measurementIds.values()):
        print("[!] No measurements were successfully created.")
        return

    print(f"\nMeasurement IDs:\n{json.dumps(measurementIds, indent=4)}")
    saveMeasurementMapping(measurementIds)

    # Phase 2: Wait then fetch results
    print(f"\n--- Phase 2: Waiting {WAIT_TIME}s for probes to complete ---")
    time.sleep(WAIT_TIME)

    print("\n--- Phase 3: Fetching Results ---")
    for service, domains in measurementIds.items():
        for domain, mId in domains.items():
            success, _ = fetchResults(mId)
            if not success:
                print(f"  [!] Could not fetch results for {domain} (ID: {mId}).")
            time.sleep(1)

    print("\nGlobal data collection complete!")


if __name__ == "__main__":
    runCollection()
