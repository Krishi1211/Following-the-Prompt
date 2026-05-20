import json
import os
import glob
import numpy as np

def analyze_ripe_results():
    mapping_files = glob.glob("Krishi_Final_Dataset/ripe_measurement_mapping_*.json")
    if not mapping_files:
        print("No measurement mapping file found.")
        return
        
    latest_mapping = sorted(mapping_files)[-1]
    with open(latest_mapping, "r") as f:
        mapping = json.load(f)

    print(f"--- Analysis Report for {latest_mapping} ---")
    
    for service, domains in mapping.items():
        print(f"\n======================================")
        print(f" SERVICE: {service}")
        print(f"======================================")
        for domain, m_id in domains.items():
            result_file = f"Krishi_Final_Dataset/ripe_results_{m_id}.json"
            if not os.path.exists(result_file):
                print(f"  [!] Missing data file for {domain} (ID: {m_id})")
                continue
                
            with open(result_file, "r") as f:
                data = json.load(f)
                
            total_probes = len(data)
            reached_dest = 0
            avg_rtts = []
            hop_counts = []
            
            for probe_run in data:
                hops = probe_run.get('result', [])
                if not hops:
                    continue
                    
                # A probe is considered to have reached the destination if 'destination_ip_responded' is true
                # or if the last hop contains the target IP. However, RIPE Atlas has a 'destination_ip_responded' field sometimes.
                # Let's just look at the last hop's RTTs.
                last_hop = hops[-1]
                valid_rtts = [attempt.get('rtt') for attempt in last_hop.get('result', []) if 'rtt' in attempt]
                
                if valid_rtts:
                    reached_dest += 1
                    avg_rtts.append(np.mean(valid_rtts))
                    hop_counts.append(last_hop.get('hop', 0))
                    
            success_rate = (reached_dest / total_probes * 100) if total_probes > 0 else 0
            mean_rtt = np.mean(avg_rtts) if avg_rtts else 0
            mean_hops = np.mean(hop_counts) if hop_counts else 0
            
            print(f"  Domain: {domain} (ID: {m_id})")
            print(f"    - Probes Participated: {total_probes}")
            print(f"    - Successful Connections: {reached_dest} ({success_rate:.1f}%)")
            print(f"    - Average RTT to Dest: {mean_rtt:.2f} ms")
            print(f"    - Average Hop Count: {mean_hops:.1f} hops")
            print("")

if __name__ == "__main__":
    analyze_ripe_results()
