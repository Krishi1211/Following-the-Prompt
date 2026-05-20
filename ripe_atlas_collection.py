import os
import json
import time
from datetime import datetime
from ripe.atlas.cousteau import (
    Traceroute,
    AtlasSource,
    AtlasCreateRequest,
    AtlasResultsRequest
)

# Define the targets to measure (same as local_collection.py)
TARGETS = {
    "ChatGPT": ["chat.openai.com", "api.openai.com"],
    "Gemini": ["gemini.google.com", "generativelanguage.googleapis.com"],
    "Claude": ["claude.ai", "api.anthropic.com"]
}

def get_api_key():
    # Try to get from environment first
    api_key = "c9d40cfb-822e-405c-8e58-31d5255380df"
    if not api_key:
        api_key = input("Please enter your RIPE Atlas API Key: ").strip()
    return api_key

def trigger_ripe_traceroutes(target_domain, api_key, sources):
    """
    Triggers a traceroute measurement from global RIPE Atlas probes to the target domain.
    """
    traceroute = Traceroute(
        af=4, # IPv4
        target=target_domain,
        description=f"AI Routing Project: Traceroute to {target_domain}",
        protocol="ICMP",
    )

    atlas_request = AtlasCreateRequest(
        start_time=datetime.utcnow(),
        key=api_key,
        measurements=[traceroute],
        sources=sources,
        is_oneoff=True
    )

    print(f"Submitting measurement request for {target_domain}...")
    (is_success, response) = atlas_request.create()
    
    if is_success:
        measurement_id = response['measurements'][0]
        print(f"Success! Measurement ID: {measurement_id}")
        return measurement_id
    else:
        print(f"Failed to create measurement: {response}")
        return None

def fetch_results(measurement_id):
    """
    Fetches the results for a completed measurement ID.
    """
    print(f"Fetching results for Measurement ID {measurement_id}...")
    kwargs = {
        "msm_id": measurement_id
    }
    # For one-off measurements, it might take a couple of minutes to collect all results
    is_success, response = AtlasResultsRequest(**kwargs).create()
    
    if is_success:
        if not response:
            print(f"No results yet for {measurement_id}.")
            return False, None
            
        filename = f"ripe_results_{measurement_id}.json"
        with open(filename, "w") as f:
            json.dump(response, f, indent=4)
        print(f"Results saved to {filename}")
        return True, response
    else:
        print(f"Failed to fetch results for {measurement_id}.")
        return False, None

def run_collection():
    print("AI Routing Project: Global RIPE Atlas Data Collection")
    api_key = get_api_key()
    if not api_key:
        print("API Key is required to proceed.")
        return

    print("\nSelect your name to target your assigned US States:")
    print("1. Aryan  (West / Central - 13 states / 39 Probes)")
    print("2. Ashay  (South / Midwest - 13 states / 39 Probes)")
    print("3. Krishi (North / Mid-Atlantic - 12 states / 36 Probes)")
    print("4. Urmil  (East Coast / New England - 12 states / 36 Probes)")
    choice = input("Enter the number of your name (1-4): ").strip()
    
    # Specific US probes per state explicitly requested
    member_regions = {
        "1": [AtlasSource(type="probes", value="3588,51310,60259,28,7363,7449,3328,7549,17218,32,125,307,1058,4160,4851,3483,3671,12721,6408,7159,10456,202,6835,7523,34313,54871,60255,10507,25206,52650,15038,27310,55734,50128,55078,61588,6373,6884,6925", requested=39)],
        "2": [AtlasSource(type="probes", value="14720,19053,61465,22803,55484,63081,12159,35140,1004380,1121,6437,6692,4085,6565,6597,7087,50084,50168,13397,29049,55630,1001471,1012465,1012466,54785,55260,60888,12180,60886,61246,7256,23087,52645,1184,7719,10286,6389,7105,7691", requested=39)],
        "3": [AtlasSource(type="probes", value="20756,21031,1008859,4325,50344,52196,54286,54939,62023,6783,6946,6972,1113,1160,4958,801,6634,7374,16896,19551,21791,1127,7368,11529,1142,3756,4069,21087,24836,51343,1169,3715,7014,10357,20683,54280", requested=36)],
        "4": [AtlasSource(type="probes", value="7643,10342,15979,12334,33081,53308,4405,10443,10473,6452,6590,6643,6436,6574,6644,3660,4894,6454,23714,51354,51440,4969,6379,7692,7224,7728,10553,51140,4551,6875,10146,7672,13159,13288", requested=34)]
    }
    
    sources = member_regions.get(choice)
    if not sources:
        print("Invalid choice. Exiting.")
        return

    # Phase 1: Trigger all measurements
    measurement_ids = {}
    for service, domains in TARGETS.items():
        measurement_ids[service] = {}
        for domain in domains:
            m_id = trigger_ripe_traceroutes(domain, api_key, sources)
            if m_id:
                measurement_ids[service][domain] = m_id
            # Slight delay between creating requests to avoid rate limits
            time.sleep(2)

    if not any(measurement_ids.values()):
        print("No measurements were successfully created.")
        return

    print("\nAll measurements triggered successfully.")
    print("Measurement IDs mapping:")
    print(json.dumps(measurement_ids, indent=4))
    
    # Save the mapping just in case the script crashes before fetching
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mapping_file = f"ripe_measurement_mapping_{timestamp}.json"
    with open(mapping_file, "w") as f:
        json.dump(measurement_ids, f, indent=4)
    print(f"Saved measurement mapping to {mapping_file}")

    # Phase 2: Wait and Fetch Results
    wait_time = 180 # Wait 3 minutes for one-off measurements to complete
    print(f"\nWaiting {wait_time} seconds for RIPE Atlas probes to execute the traceroutes...")
    time.sleep(wait_time)

    print("\nFetching results...")
    for service, domains in measurement_ids.items():
        for domain, m_id in domains.items():
            success, _ = fetch_results(m_id)
            if not success:
                print(f"Could not fetch full results for {domain} ({m_id}). You may need to fetch manually later using fetch_results({m_id}).")
            time.sleep(1) # Polite delay
            
    print("\nGlobal data collection complete!")

if __name__ == "__main__":
    run_collection()
