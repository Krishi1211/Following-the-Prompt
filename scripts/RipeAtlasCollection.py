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
    "ChatGPT": ["api.openai.com"],
    "Gemini":  ["generativelanguage.googleapis.com"],
    "Claude":  ["api.anthropic.com"],
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

# Probe ID → US State mapping, derived from generate_state_probes.py
# Each member's probes were assigned 3 per state in the order listed below.
PROBE_STATE_MAP = {
    "1": {  # Aryan — West / Central
        "3588":  "Alaska",      "51310": "Alaska",      "60259": "Alaska",
        "28":    "Nevada",      "7363":  "Nevada",      "7449":  "Nevada",
        "3328":  "Utah",        "7549":  "Utah",        "17218": "Utah",
        "32":    "California",  "125":   "California",  "307":   "California",
        "1058":  "Washington",  "4160":  "Washington",  "4851":  "Washington",
        "3483":  "Oregon",      "3671":  "Oregon",      "12721": "Oregon",
        "6408":  "Arizona",     "7159":  "Arizona",     "10456": "Arizona",
        "202":   "Colorado",    "6835":  "Colorado",    "7523":  "Colorado",
        "34313": "Oklahoma",    "54871": "Oklahoma",    "60255": "Oklahoma",
        "10507": "Kansas",      "25206": "Kansas",      "52650": "Kansas",
        "15038": "Nebraska",    "27310": "Nebraska",    "55734": "Nebraska",
        "50128": "Iowa",        "55078": "Iowa",        "61588": "Iowa",
        "6373":  "Missouri",    "6884":  "Missouri",    "6925":  "Missouri",
    },
    "2": {  # Ashay — South / Midwest
        "14720":   "Hawaii",       "19053":   "Hawaii",       "61465":   "Hawaii",
        "22803":   "New Mexico",   "55484":   "New Mexico",   "63081":   "New Mexico",
        "12159":   "Wyoming",      "35140":   "Wyoming",      "1004380": "Wyoming",
        "1121":    "Texas",        "6437":    "Texas",        "6692":    "Texas",
        "4085":    "Illinois",     "6565":    "Illinois",     "6597":    "Illinois",
        "7087":    "Arkansas",     "50084":   "Arkansas",     "50168":   "Arkansas",
        "13397":   "Louisiana",    "29049":   "Louisiana",    "55630":   "Louisiana",
        "1001471": "Mississippi",  "1012465": "Mississippi",  "1012466": "Mississippi",
        "54785":   "Alabama",      "55260":   "Alabama",      "60888":   "Alabama",
        "12180":   "Tennessee",    "60886":   "Tennessee",    "61246":   "Tennessee",
        "7256":    "Kentucky",     "23087":   "Kentucky",     "52645":   "Kentucky",
        "1184":    "Indiana",      "7719":    "Indiana",      "10286":   "Indiana",
        "6389":    "Michigan",     "7105":    "Michigan",     "7691":    "Michigan",
    },
    "3": {  # Krishi — North / Mid-Atlantic
        "20756":  "Montana",       "21031":  "Montana",       "1008859": "Montana",
        "4325":   "North Dakota",  "50344":  "North Dakota",  "52196":   "North Dakota",
        "54286":  "South Dakota",  "54939":  "South Dakota",  "62023":   "South Dakota",
        "6783":   "New York",      "6946":   "New York",      "6972":    "New York",
        "1113":   "Virginia",      "1160":   "Virginia",      "4958":    "Virginia",
        "801":    "Minnesota",     "6634":   "Minnesota",     "7374":    "Minnesota",
        "16896":  "Wisconsin",     "19551":  "Wisconsin",     "21791":   "Wisconsin",
        "1127":   "Ohio",          "7368":   "Ohio",          "11529":   "Ohio",
        "1142":   "Pennsylvania",  "3756":   "Pennsylvania",  "4069":    "Pennsylvania",
        "21087":  "West Virginia", "24836":  "West Virginia", "51343":   "West Virginia",
        "1169":   "Maryland",      "3715":   "Maryland",      "7014":    "Maryland",
        "10357":  "Delaware",      "20683":  "Delaware",      "54280":   "Delaware",
    },
    "4": {  # Urmil — East Coast / New England
        # 34 probes across 12 states; Rhode Island and Massachusetts have 2 probes each
        "7643":  "Idaho",           "10342": "Idaho",           "15979": "Idaho",
        "12334": "Maine",           "33081": "Maine",           "53308": "Maine",
        "4405":  "Vermont",         "10443": "Vermont",         "10473": "Vermont",
        "6452":  "Florida",         "6590":  "Florida",         "6643":  "Florida",
        "6436":  "New Jersey",      "6574":  "New Jersey",      "6644":  "New Jersey",
        "3660":  "Georgia",         "4894":  "Georgia",         "6454":  "Georgia",
        "23714": "South Carolina",  "51354": "South Carolina",  "51440": "South Carolina",
        "4969":  "North Carolina",  "6379":  "North Carolina",  "7692":  "North Carolina",
        "7224":  "Connecticut",     "7728":  "Connecticut",     "10553": "Connecticut",
        "51140": "Rhode Island",    "4551":  "Rhode Island",
        "6875":  "Massachusetts",   "10146": "Massachusetts",
        "7672":  "New Hampshire",   "13159": "New Hampshire",   "13288": "New Hampshire",
    },
}

WAIT_TIME = 180  # seconds to wait for probes to complete

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_ROOT, "data")

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

def fetchResults(measurementId, probeStateMap):
    """
    Fetches results for a measurement and saves them split by US state under
    data/US/<state>/ripe_results_<measurementId>.json
    """
    print(f"  Fetching results for ID {measurementId}...")
    isSuccess, response = AtlasResultsRequest(msm_id=measurementId).create()

    if not isSuccess:
        print(f"  Failed to fetch results for {measurementId}.")
        return False, None
    if not response:
        print(f"  No results yet for {measurementId}.")
        return False, None

    # Group probe results by state using prb_id
    stateResults = {}
    unknownResults = []

    for probeResult in response:
        probeId = str(probeResult.get("prb_id", ""))
        state   = probeStateMap.get(probeId)
        if state:
            stateResults.setdefault(state, []).append(probeResult)
        else:
            unknownResults.append(probeResult)

    if unknownResults:
        print(f"  [!] {len(unknownResults)} probe(s) had no state mapping — saved to Unknown/")
        stateResults["Unknown"] = unknownResults

    # Write one file per state: data/US/<state>/ripe_results_<id>.json
    for state, results in stateResults.items():
        stateDir = os.path.join(DATA_DIR, "US", state)
        os.makedirs(stateDir, exist_ok=True)
        filePath = os.path.join(stateDir, f"ripe_results_{measurementId}.json")
        with open(filePath, "w") as f:
            json.dump(results, f, indent=4)
        print(f"  [{state}] {len(results)} probe result(s) → {filePath}")

    return True, response

# ─── Persistence ──────────────────────────────────────────────────────────────

def saveMeasurementMapping(measurementIds):
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    mappingFile  = os.path.join(DATA_DIR, f"ripe_measurement_mapping_{timestamp}.json")
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

    probeStateMap = PROBE_STATE_MAP.get(choice, {})

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

    # Phase 2: Wait for probes to execute
    print(f"\n--- Phase 2: Waiting {WAIT_TIME}s for probes to complete ---")
    time.sleep(WAIT_TIME)

    # Phase 3: Fetch and split results by state
    print("\n--- Phase 3: Fetching Results ---")
    for service, domains in measurementIds.items():
        for domain, mId in domains.items():
            print(f"\n[{service}] {domain}")
            success, _ = fetchResults(mId, probeStateMap)
            if not success:
                print(f"  [!] Could not fetch results for {domain} (ID: {mId}).")
            time.sleep(1)

    print("\nCollection complete. Results saved under: data/US/<state>/")


if __name__ == "__main__":
    runCollection()
