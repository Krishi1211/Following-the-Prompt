import os
import json
import glob
from collections import defaultdict

def load_mappings(data_dir):
    """
    Scans data_dir for mapping files and returns a dict mapping msm_id -> (llm_service, domain)
    """
    msm_to_llm = {}
    mapping_files = glob.glob(os.path.join(data_dir, "**/*mapping*.json"), recursive=True)
    for path in mapping_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            # Check if this is the international mapping format
            if isinstance(content, dict) and "measurements" in content:
                for country, services in content["measurements"].items():
                    for service, info in services.items():
                        m_id = info.get("measurement_id")
                        domain = info.get("domain")
                        if m_id:
                            msm_to_llm[int(m_id)] = (service, domain)
            elif isinstance(content, dict):
                # US mapping format
                for service, domains in content.items():
                    if isinstance(domains, dict):
                        for domain, m_id in domains.items():
                            if m_id:
                                msm_to_llm[int(m_id)] = (service, domain)
        except Exception as e:
            print(f"Error parsing mapping file {path}: {e}")
    return msm_to_llm

def parse_path(path):
    """
    Derives contributor, region (state/country), and country from file path.
    """
    parts = os.path.normpath(path).split(os.sep)
    if "US" in parts:
        idx = parts.index("US")
        contributor = parts[idx-1]
        region = parts[idx+1]
        country = "US"
    elif "international" in parts:
        idx = parts.index("international")
        contributor = parts[idx-1]
        region = parts[idx+1]
        country = region
    else:
        contributor = "unknown"
        region = "unknown"
        country = "unknown"
    return contributor, region, country

def load_data(data_dir):
    """
    Loads all RIPE results, matches them with mappings, aggregates across days,
    and returns a list of aggregated traceroute records.
    """
    print("Loading mappings...")
    msm_to_llm = load_mappings(data_dir)
    print(f"Loaded {len(msm_to_llm)} measurement mappings.")

    # Find all ripe_results_*.json files, ignoring any enriched files
    all_files = glob.glob(os.path.join(data_dir, "**/ripe_results_*.json"), recursive=True)
    # Filter out enriched files just in case
    result_files = [f for f in all_files if "enriched" not in os.path.basename(f)]
    
    print(f"Found {len(result_files)} raw result files.")

    # Group raw traceroutes by (msm_id, probe_src_ip)
    # key: (msm_id, src_addr) -> list of runs
    grouped_traceroutes = defaultdict(list)
    # To keep metadata for each group (use the first one found)
    group_meta = {}

    for path in result_files:
        basename = os.path.basename(path)
        try:
            m_id_str = basename.split("_")[-1].replace(".json", "")
            m_id = int(m_id_str)
        except Exception:
            # Skip files with invalid name format
            continue

        if m_id not in msm_to_llm:
            continue

        llm, domain = msm_to_llm[m_id]
        contributor, region, country = parse_path(path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                continue

            for probe_res in data:
                src_addr = probe_res.get("src_addr")
                if not src_addr:
                    continue

                # Parse hops
                parsed_hops = []
                for hop_data in probe_res.get("result", []):
                    hop_num = hop_data.get("hop")
                    if hop_num is None:
                        continue
                    
                    ips = []
                    rtts = []
                    for pkt in hop_data.get("result", []):
                        ip = pkt.get("from")
                        rtt = pkt.get("rtt")
                        if ip:
                            ips.append(ip)
                        if rtt is not None:
                            rtts.append(float(rtt))
                    
                    parsed_hops.append({
                        "hop": int(hop_num),
                        "ips": list(set(ips)),
                        "rtts": rtts
                    })

                key = (m_id, src_addr)
                grouped_traceroutes[key].append(parsed_hops)
                if key not in group_meta:
                    group_meta[key] = {
                        "msm_id": m_id,
                        "llm": llm,
                        "domain": domain,
                        "contributor": contributor,
                        "region": region,
                        "country": country,
                        "src_addr": src_addr,
                        "dst_addr": probe_res.get("dst_addr")
                    }
        except Exception as e:
            print(f"Error reading file {path}: {e}")

    # Now aggregate across days/runs
    aggregated_records = []
    for key, runs in grouped_traceroutes.items():
        msm_id, src_addr = key
        meta = group_meta[key]
        meta["msm_id"] = msm_id
        
        # Aggregate hops: group by hop number
        hops_by_num = defaultdict(lambda: {"ips": set(), "rtts": []})
        for run in runs:
            for hop in run:
                hop_num = hop["hop"]
                hops_by_num[hop_num]["ips"].update(hop["ips"])
                hops_by_num[hop_num]["rtts"].extend(hop["rtts"])

        # Convert back to sorted list of dicts
        agg_hops = []
        for hop_num in sorted(hops_by_num.keys()):
            agg_hops.append({
                "hop": hop_num,
                "ips": list(hops_by_num[hop_num]["ips"]),
                "rtts": hops_by_num[hop_num]["rtts"]
            })

        meta["hops"] = agg_hops
        meta["num_runs"] = len(runs)
        aggregated_records.append(meta)

    print(f"Aggregated data into {len(aggregated_records)} unique traceroute records.")
    return aggregated_records
