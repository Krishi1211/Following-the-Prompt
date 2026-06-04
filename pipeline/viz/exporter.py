"""
Exports all analytics results as structured JSON files for the React dashboard.
Output goes to dashboard/public/data/ so Vite serves them as static assets.
"""

import os
import json
from collections import defaultdict
from viz.resolver import is_private


def _safe_float(v, default=None):
    try:
        f = float(v)
        return round(f, 3) if f == f else default  # NaN check
    except (TypeError, ValueError):
        return default


def export_summary(records, geo_cache, output_dir):
    llm_counts = defaultdict(int)
    country_counts = defaultdict(int)
    contributors = set()
    for r in records:
        llm_counts[r["llm"]] += 1
        country_counts[r["country"]] += 1
        contributors.add(r.get("contributor", "unknown"))

    cached_public = sum(
        1 for ip, v in geo_cache.items()
        if not v.get("private") and v.get("lat") is not None
    )
    total_ips = len(geo_cache)

    data = {
        "total_traceroutes": len(records),
        "unique_ips_resolved": total_ips,
        "geo_resolved_ips": cached_public,
        "contributors": sorted(contributors),
        "llm_breakdown": dict(llm_counts),
        "country_breakdown": dict(sorted(country_counts.items(), key=lambda x: -x[1])),
        "days_span": 4,
    }

    _write(output_dir, "summary.json", data)


def export_world_map(records, geo_cache, output_dir):
    """
    Compact world map data for Plotly scattergeo:
    { "Claude": { lats, lons, texts }, "Gemini": {...}, "ChatGPT": {...} }
    Also exports per-path data for hover/filter.
    """
    LLMs = ["Claude", "Gemini", "ChatGPT"]
    result = {llm: {"lats": [], "lons": [], "texts": []} for llm in LLMs}

    for r in records:
        llm = r["llm"]
        if llm not in result:
            continue

        path_lats, path_lons, path_texts = [], [], []

        src_geo = geo_cache.get(r.get("src_addr", ""), {})
        if src_geo and not src_geo.get("private") and src_geo.get("lat") is not None:
            path_lats.append(src_geo["lat"])
            path_lons.append(src_geo["lon"])
            path_texts.append(
                f"Source: {r.get('src_addr')}<br>"
                f"Region: {r.get('region')}, {r.get('country')}"
            )

        for hop in r.get("hops", []):
            valid_ip = None
            for ip in hop.get("ips", []):
                if not is_private(ip):
                    valid_ip = ip
                    break
            if not valid_ip:
                continue
            geo = geo_cache.get(valid_ip, {})
            if not geo or geo.get("lat") is None:
                continue
            path_lats.append(geo["lat"])
            path_lons.append(geo["lon"])
            rtts = [x for x in hop.get("rtts", []) if x]
            min_rtt = round(min(rtts), 2) if rtts else None
            path_texts.append(
                f"IP: {valid_ip}<br>"
                f"Org: {geo.get('org_name', '?')}<br>"
                f"ASN: {geo.get('asn', '?')}<br>"
                f"City: {geo.get('city', '?')}, {geo.get('country', '?')}<br>"
                f"Hop #: {hop['hop']}"
                + (f"<br>Min RTT: {min_rtt} ms" if min_rtt else "")
            )

        if len(path_lats) > 1:
            result[llm]["lats"].extend(path_lats + [None])
            result[llm]["lons"].extend(path_lons + [None])
            result[llm]["texts"].extend(path_texts + [None])

    _write(output_dir, "world_map.json", result)


def export_hops_per_isp(df, output_dir):
    if df.empty:
        _write(output_dir, "hops_per_isp.json", [])
        return

    grouped = df.groupby(["starting_isp", "llm", "country"])["hop_count"].agg(
        mean="mean", std="std", count="count"
    ).reset_index()
    grouped["mean"] = grouped["mean"].round(2)
    grouped["std"] = grouped["std"].fillna(0).round(2)

    # For box plot: raw distribution per (isp, llm)
    raw = df.groupby(["starting_isp", "llm"])["hop_count"].apply(list).reset_index()
    raw_map = {}
    for _, row in raw.iterrows():
        key = f"{row['starting_isp']}|{row['llm']}"
        raw_map[key] = row["hop_count"]

    rows = []
    for _, row in grouped.iterrows():
        key = f"{row['starting_isp']}|{row['llm']}"
        rows.append({
            "starting_isp": row["starting_isp"],
            "llm": row["llm"],
            "country": row["country"],
            "mean_hops": row["mean"],
            "std_hops": row["std"],
            "count": int(row["count"]),
            "distribution": raw_map.get(key, [])
        })

    _write(output_dir, "hops_per_isp.json", rows)


def export_rtt_per_isp(df, output_dir):
    if df.empty:
        _write(output_dir, "rtt_per_isp.json", [])
        return

    grouped = df.groupby(["source_region", "starting_isp", "llm", "country"])["total_rtt_ms"].agg(
        mean="mean", std="std", count="count", min="min", max="max"
    ).reset_index()
    for col in ["mean", "std", "min", "max"]:
        grouped[col] = grouped[col].fillna(0).round(2)

    rows = grouped.rename(columns={
        "mean": "mean_rtt_ms", "std": "std_rtt_ms",
        "min": "min_rtt_ms", "max": "max_rtt_ms"
    }).to_dict(orient="records")

    for r in rows:
        r["count"] = int(r["count"])

    _write(output_dir, "rtt_per_isp.json", rows)


def export_common_as(df, output_dir):
    if df.empty:
        _write(output_dir, "common_as.json", [])
        return

    df = df.sort_values("total_appearances", ascending=False)
    rows = df.head(60).to_dict(orient="records")
    for r in rows:
        r["total_appearances"] = int(r["total_appearances"])
        r["llm_count"] = int(r["llm_count"])
    _write(output_dir, "common_as.json", rows)


def export_hops_to_exit_as(df, output_dir):
    if df.empty:
        _write(output_dir, "hops_to_exit_as.json", [])
        return

    # Separate anomalies before aggregation
    anomalies = df[df["never_exited"] == True]
    normal = df[df["never_exited"] == False]

    agg_cols = ["source_country", "source_isp", "llm"]
    anomaly_count = anomalies.groupby(agg_cols).size().reset_index(name="anomaly_count")

    grouped = normal.groupby(agg_cols)["hops_to_exit"].agg(
        mean="mean", std="std", count="count"
    ).reset_index()
    grouped["mean"] = grouped["mean"].round(2)
    grouped["std"] = grouped["std"].fillna(0).round(2)

    merged = grouped.merge(anomaly_count, on=agg_cols, how="left")
    merged["anomaly_count"] = merged["anomaly_count"].fillna(0).astype(int)

    rows = merged.rename(columns={
        "mean": "mean_hops_to_exit", "std": "std_hops_to_exit"
    }).to_dict(orient="records")

    for r in rows:
        r["count"] = int(r["count"])
        r["anomaly_count"] = int(r["anomaly_count"])

    _write(output_dir, "hops_to_exit_as.json", rows)


def export_all(records, geo_cache, metrics, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f"  Exporting summary...")
    export_summary(records, geo_cache, output_dir)
    print(f"  Exporting world map paths...")
    export_world_map(records, geo_cache, output_dir)
    print(f"  Exporting hops per ISP...")
    export_hops_per_isp(metrics["hops_per_isp"], output_dir)
    print(f"  Exporting RTT per ISP/region...")
    export_rtt_per_isp(metrics["rtt_per_isp"], output_dir)
    print(f"  Exporting common ASes...")
    export_common_as(metrics["common_as"], output_dir)
    print(f"  Exporting hops to exit AS...")
    export_hops_to_exit_as(metrics["hops_to_exit_as"], output_dir)
    print(f"  JSON data written to {output_dir}")


def _write(directory, filename, data):
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), allow_nan=False, default=_json_default)


def _json_default(obj):
    import math
    if isinstance(obj, float) and math.isnan(obj):
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
