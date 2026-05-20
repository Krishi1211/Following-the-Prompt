import requests
import reverse_geocoder as rg
import json
import time

STATE_MAPPING = {
    'Alaska': 'Aryan', 'Nevada': 'Aryan', 'Utah': 'Aryan', 'California': 'Aryan', 'Washington': 'Aryan',
    'Oregon': 'Aryan', 'Arizona': 'Aryan', 'Colorado': 'Aryan', 'Oklahoma': 'Aryan', 'Kansas': 'Aryan',
    'Nebraska': 'Aryan', 'Iowa': 'Aryan', 'Missouri': 'Aryan',
    
    'Hawaii': 'Ashay', 'New Mexico': 'Ashay', 'Wyoming': 'Ashay', 'Texas': 'Ashay', 'Illinois': 'Ashay',
    'Arkansas': 'Ashay', 'Louisiana': 'Ashay', 'Mississippi': 'Ashay', 'Alabama': 'Ashay', 'Tennessee': 'Ashay',
    'Kentucky': 'Ashay', 'Indiana': 'Ashay', 'Michigan': 'Ashay',
    
    'Montana': 'Krishi', 'North Dakota': 'Krishi', 'South Dakota': 'Krishi', 'New York': 'Krishi', 'Virginia': 'Krishi',
    'Minnesota': 'Krishi', 'Wisconsin': 'Krishi', 'Ohio': 'Krishi', 'Pennsylvania': 'Krishi', 'West Virginia': 'Krishi',
    'Maryland': 'Krishi', 'Delaware': 'Krishi',
    
    'Idaho': 'Urmil', 'Maine': 'Urmil', 'Vermont': 'Urmil', 'Florida': 'Urmil', 'New Jersey': 'Urmil',
    'Georgia': 'Urmil', 'South Carolina': 'Urmil', 'North Carolina': 'Urmil', 'Connecticut': 'Urmil', 'Rhode Island': 'Urmil',
    'Massachusetts': 'Urmil', 'New Hampshire': 'Urmil'
}

PROBES_PER_STATE = 3

def fetch_us_probes():
    # Fetch connected, public US probes
    url = "https://atlas.ripe.net/api/v2/probes/?country_code=US&status=1&is_public=true&limit=1000"
    all_probes = []
    
    while url:
        print(f"Fetching {url}...")
        try:
            resp = requests.get(url)
            data = resp.json()
            all_probes.extend(data['results'])
            url = data.get('next')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            break
        
    return all_probes

def main():
    probes = fetch_us_probes()
    print(f"Found {len(probes)} US probes.")
    
    # Filter probes with geometry
    probes_with_geo = [p for p in probes if p.get('geometry') and p['geometry'].get('coordinates')]
    print(f"{len(probes_with_geo)} probes with coordinates.")
    
    coords = [(p['geometry']['coordinates'][1], p['geometry']['coordinates'][0]) for p in probes_with_geo]
    
    print("Reverse geocoding...")
    results = rg.search(coords)
    
    state_to_probes = {s: [] for s in STATE_MAPPING.keys()}
    
    for probe, geo_res in zip(probes_with_geo, results):
        state = geo_res.get('admin1')
        if state in state_to_probes:
            state_to_probes[state].append(str(probe['id']))
            
    # Assign to students
    student_to_probes = {
        'Aryan': [],
        'Ashay': [],
        'Krishi': [],
        'Urmil': []
    }
    
    for state, p_list in state_to_probes.items():
        if len(p_list) == 0:
            print(f"WARNING: No probes found for {state}")
        
        # Take up to 3
        selected = p_list[:PROBES_PER_STATE]
        student = STATE_MAPPING[state]
        student_to_probes[student].extend(selected)
        
        if len(selected) < PROBES_PER_STATE:
            print(f"WARNING: Only {len(selected)} probes found for {state}")
            
    with open("student_probes.json", "w") as f:
        json.dump(student_to_probes, f, indent=4)
        
    for student, p_list in student_to_probes.items():
        print(f"{student}: {len(p_list)} probes")

if __name__ == "__main__":
    main()
