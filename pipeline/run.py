import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_ROOT)

from viz.loader import load_data
from viz.resolver import resolve_ips, load_cache, is_private
from viz.analytics import compute_all_metrics
from viz.exporter import export_all
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
    output_dir = os.path.join(project_root, "outputs", "html")
    # React dashboard reads JSON from its public/data folder
    dashboard_data_dir = os.path.join(project_root, "dashboard", "public", "data")

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
        if r.get("src_addr"):
            unique_ips.add(r["src_addr"])
        if r.get("dst_addr"):
            unique_ips.add(r["dst_addr"])
        for hop in r["hops"]:
            for ip in hop.get("ips", []):
                unique_ips.add(ip)

    print(f"Found {len(unique_ips)} unique IPs in the dataset.")

    initial_cache = load_cache()
    cached_count = sum(1 for ip in unique_ips if ip in initial_cache)
    print(f"Cache status: {cached_count}/{len(unique_ips)} IPs already resolved.")

    # Step 3: Resolve IPs (reads/writes outputs/geo_cache.json)
    print("\n--- Step 3: Geolocation & ASN Resolution ---")
    geo_cache = resolve_ips(unique_ips)

    # Step 4: Compute Metrics
    print("\n--- Step 4: Computing Analytics Metrics ---")
    metrics = compute_all_metrics(records, geo_cache)

    # Step 5: Export JSON for React dashboard
    print("\n--- Step 5: Exporting JSON Data for Dashboard ---")
    export_all(records, geo_cache, metrics, dashboard_data_dir)

    # Step 6: Render standalone HTML plots (legacy / backup)
    print("\n--- Step 6: Rendering Standalone HTML Charts ---")
    os.makedirs(output_dir, exist_ok=True)

    print("Generating World Map...")
    plot_world_map(records, geo_cache, output_dir)

    print("Generating Metric (a) Hops per Starting ISP...")
    plot_hops_per_isp(metrics["hops_per_isp"], output_dir)

    print("Generating Metric (b) Total RTT per ISP per Region...")
    plot_rtt_per_isp(metrics["rtt_per_isp"], output_dir)

    print("Generating Metric (c) Shared Backbone ASes...")
    plot_common_as(metrics["common_as"], output_dir)

    print("Generating Metric (d) Hops to exit source AS...")
    plot_hops_to_exit_as(metrics["hops_to_exit_as"], output_dir)

    print("\n==================================================")
    print(" Execution Summary")
    print("==================================================")
    print(f"Total Traceroutes Analyzed:   {len(records)}")
    print(f"Unique IPs:                    {len(unique_ips)}")
    cache_hit = cached_count / len(unique_ips) * 100 if unique_ips else 0
    print(f"Cache Hit Rate (start):        {cache_hit:.1f}%")
    print(f"Dashboard JSON data:           {dashboard_data_dir}/")
    print(f"Standalone HTML outputs:       {output_dir}/")
    print("==================================================")

if __name__ == "__main__":
    main()
