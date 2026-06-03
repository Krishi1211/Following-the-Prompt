import os
import sys

# Add scripts directory to path to import viz package
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_ROOT)

from viz.loader import load_data
from viz.resolver import resolve_ips, load_cache, is_private
from viz.analytics import compute_all_metrics
from viz.plots.world_map import plot_world_map
from viz.plots.hops_per_isp import plot_hops_per_isp
from viz.plots.rtt_per_isp import plot_rtt_per_isp
from viz.plots.common_as import plot_common_as
from viz.plots.hops_to_exit_as import plot_hops_to_exit_as

def main():
    print("==================================================")
    print(" RIPE Atlas Traceroute Visualization & Analytics")
    print("==================================================")

    project_root = os.path.dirname(_ROOT)
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "outputs")

    # Step 1: Load data
    print("\n--- Step 1: Loading Data ---")
    records = load_data(data_dir)
    if not records:
        print("[!] No records found. Exiting.")
        return

    # Step 2: Extract unique IPs for resolution
    print("\n--- Step 2: Extracting Unique IPs ---")
    unique_ips = set()
    for r in records:
        unique_ips.add(r["src_addr"])
        unique_ips.add(r["dst_addr"])
        for hop in r["hops"]:
            for ip in hop.get("ips", []):
                unique_ips.add(ip)
    
    print(f"Found {len(unique_ips)} unique IPs in the dataset.")

    # Load cache first to calculate hit rate before resolving
    initial_cache = load_cache()
    cached_count = sum(1 for ip in unique_ips if ip in initial_cache)
    print(f"Cache status: {cached_count}/{len(unique_ips)} IPs already resolved in outputs/geo_cache.json.")

    # Step 3: Resolve IPs
    print("\n--- Step 3: Geolocation & ASN Resolution ---")
    geo_cache = resolve_ips(unique_ips)

    # Step 4: Compute Metrics
    print("\n--- Step 4: Computing Analytics Metrics ---")
    metrics = compute_all_metrics(records, geo_cache)

    # Step 5: Render Plots
    print("\n--- Step 5: Rendering Interactive Charts ---")
    
    print("Generating World Map...")
    plot_world_map(records, geo_cache, output_dir)
    
    print("Generating Metric (a) Hops per Starting ISP plot...")
    plot_hops_per_isp(metrics["hops_per_isp"], output_dir)
    
    print("Generating Metric (b) Total RTT per ISP per Region heatmap...")
    plot_rtt_per_isp(metrics["rtt_per_isp"], output_dir)
    
    print("Generating Metric (c) Shared Backbone ASes plot...")
    plot_common_as(metrics["common_as"], output_dir)
    
    print("Generating Metric (d) Hops to exit source AS plot...")
    plot_hops_to_exit_as(metrics["hops_to_exit_as"], output_dir)

    print("\n==================================================")
    print(" Execution Summary")
    print("==================================================")
    print(f"Total Traceroutes Analyzed:   {len(records)}")
    print(f"Unique IPs Resolved:           {len(unique_ips)}")
    print(f"Cache Hit Rate:                {cached_count / len(unique_ips) * 100:.1f}%")
    print(f"Interactive HTML outputs saved in: {output_dir}/")
    print("==================================================")

if __name__ == "__main__":
    main()
