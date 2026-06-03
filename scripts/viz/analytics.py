import pandas as pd
from viz.resolver import is_private

def get_starting_isp(hops, geo_cache):
    """
    Finds the ISP/Organization of the first non-private hop.
    """
    for hop in hops:
        for ip in hop.get("ips", []):
            if not is_private(ip):
                geo = geo_cache.get(ip, {})
                if geo:
                    # Prefer org_name, then isp, then fallback to ASN
                    isp = geo.get("org_name") or geo.get("isp")
                    if isp and isp != "Unknown" and isp != "Private":
                        return isp
                    asn = geo.get("asn")
                    if asn and asn != "Unknown" and asn != "Private":
                        return asn
    return "Unknown ISP"

def compute_hops_per_isp(records, geo_cache):
    """
    Metric (a): Hops per starting ISP per LLM
    """
    data = []
    for r in records:
        starting_isp = get_starting_isp(r["hops"], geo_cache)
        if starting_isp == "Unknown ISP":
            continue
            
        # Count total hops with at least one responsive IP
        hop_count = sum(1 for h in r["hops"] if h.get("ips"))
        
        data.append({
            "starting_isp": starting_isp,
            "llm": r["llm"],
            "hop_count": hop_count,
            "country": r["country"]
        })
    return pd.DataFrame(data)

def compute_rtt_per_isp(records, geo_cache):
    """
    Metric (b): Total RTT per ISP per Region
    """
    data = []
    for r in records:
        starting_isp = get_starting_isp(r["hops"], geo_cache)
        if starting_isp == "Unknown ISP":
            continue
            
        # Find last responding hop with valid RTTs
        last_rtt = None
        for hop in reversed(r["hops"]):
            rtts = hop.get("rtts", [])
            valid_rtts = [t for t in rtts if t is not None and t > 0]
            if valid_rtts:
                last_rtt = min(valid_rtts) # take minimum to avoid jitter
                break
                
        if last_rtt is not None:
            data.append({
                "source_region": r["region"],
                "starting_isp": starting_isp,
                "llm": r["llm"],
                "total_rtt_ms": last_rtt,
                "country": r["country"]
            })
    return pd.DataFrame(data)

def compute_common_as(records, geo_cache):
    """
    Metric (c): Common ASes across LLMs
    """
    # Track which LLMs each ASN appears in, and total appearances
    # asn -> { "llms": set(), "appearances": 0, "org_name": "" }
    as_stats = {}
    
    for r in records:
        llm = r["llm"]
        for hop in r["hops"]:
            for ip in hop.get("ips", []):
                if is_private(ip):
                    continue
                geo = geo_cache.get(ip)
                if not geo:
                    continue
                asn = geo.get("asn")
                org_name = geo.get("org_name") or geo.get("isp") or "Unknown"
                
                if asn and asn != "Unknown" and asn != "Private":
                    if asn not in as_stats:
                        as_stats[asn] = {
                            "llms": set(),
                            "appearances": 0,
                            "org_name": org_name
                        }
                    as_stats[asn]["llms"].add(llm)
                    as_stats[asn]["appearances"] += 1
                    
                    # Update org name if it was unknown
                    if as_stats[asn]["org_name"] == "Unknown" and org_name != "Unknown":
                        as_stats[asn]["org_name"] = org_name

    data = []
    for asn, stats in as_stats.items():
        llm_set = stats["llms"]
        num_llms = len(llm_set)
        
        if num_llms == 3:
            classification = "Shared backbone"
        elif num_llms == 2:
            classification = "Partially shared"
        else:
            classification = "LLM-specific"
            
        data.append({
            "asn": asn,
            "org_name": stats["org_name"],
            "llms": ", ".join(sorted(list(llm_set))),
            "llm_count": num_llms,
            "total_appearances": stats["appearances"],
            "classification": classification
        })
        
    return pd.DataFrame(data)

def compute_hops_to_exit_as(records, geo_cache):
    """
    Metric (d): Hops to exit source ISP's AS
    """
    data = []
    for r in records:
        src_addr = r["src_addr"]
        # Resolve source ASN
        src_geo = geo_cache.get(src_addr, {})
        src_asn = src_geo.get("asn")
        
        # Fallback to ASN of first public hop if source IP itself has no ASN
        if not src_asn or src_asn == "Unknown" or src_asn == "Private":
            for hop in r["hops"]:
                for ip in hop.get("ips", []):
                    if not is_private(ip):
                        first_geo = geo_cache.get(ip, {})
                        if first_geo.get("asn") and first_geo.get("asn") != "Private":
                            src_asn = first_geo.get("asn")
                            break
                if src_asn:
                    break
                    
        if not src_asn or src_asn == "Unknown" or src_asn == "Private":
            continue
            
        starting_isp = get_starting_isp(r["hops"], geo_cache)
        if starting_isp == "Unknown ISP":
            continue
            
        # Count consecutive hops from hop 1 belonging to src_asn
        hops_to_exit = 0
        never_exited = True
        total_hops = sum(1 for h in r["hops"] if h.get("ips"))
        
        for hop in r["hops"]:
            hop_ips = hop.get("ips", [])
            if not hop_ips:
                continue
            
            # Check if any IP in this hop is outside of src_asn
            outside_as = False
            for ip in hop_ips:
                if is_private(ip):
                    continue
                ip_geo = geo_cache.get(ip, {})
                ip_asn = ip_geo.get("asn")
                if ip_asn and ip_asn != src_asn and ip_asn != "Private" and ip_asn != "Unknown":
                    outside_as = True
                    break
            
            if outside_as:
                never_exited = False
                break
            else:
                hops_to_exit += 1
                
        data.append({
            "source_country": r["country"],
            "source_isp": starting_isp,
            "llm": r["llm"],
            "hops_to_exit": hops_to_exit,
            "never_exited": never_exited,
            "total_hops": total_hops
        })
        
    return pd.DataFrame(data)

def compute_all_metrics(records, geo_cache):
    """
    Computes all four metrics and returns a dictionary of DataFrames.
    """
    print("Computing Metric (a): Hops per starting ISP...")
    df_a = compute_hops_per_isp(records, geo_cache)
    
    print("Computing Metric (b): Total RTT per ISP per Region...")
    df_b = compute_rtt_per_isp(records, geo_cache)
    
    print("Computing Metric (c): Common ASes across LLMs...")
    df_c = compute_common_as(records, geo_cache)
    
    print("Computing Metric (d): Hops to exit source ISP...")
    df_d = compute_hops_to_exit_as(records, geo_cache)
    
    return {
        "hops_per_isp": df_a,
        "rtt_per_isp": df_b,
        "common_as": df_c,
        "hops_to_exit_as": df_d
    }
