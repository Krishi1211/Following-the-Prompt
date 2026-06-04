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
    Structured world map data organised by LLM → country → region so the
    React component can load only the selected country/state instead of
    rendering all paths at once.

    Structure:
      US  → { "Alabama": { lats, lons, texts }, "Alaska": { ... }, ... }
      Intl → { "France": { lats, lons, texts }, "India": { ... }, ... }
    """
    LLMs = ["Claude", "Gemini", "ChatGPT"]
    # result[llm][country_or_state_key] = { lats, lons, texts }
    result = {llm: {} for llm in LLMs}

    def _bucket(llm, key):
        if key not in result[llm]:
            result[llm][key] = {"lats": [], "lons": [], "texts": []}
        return result[llm][key]

    for r in records:
        llm = r["llm"]
        if llm not in result:
            continue

        country = r.get("country", "unknown")
        region  = r.get("region",  country)

        # US: bucket per state; international: bucket per country
        bucket_key = region if country == "US" else country

        path_lats, path_lons, path_texts = [], [], []

        src_geo = geo_cache.get(r.get("src_addr", ""), {})
        if src_geo and not src_geo.get("private") and src_geo.get("lat") is not None:
            path_lats.append(src_geo["lat"])
            path_lons.append(src_geo["lon"])
            path_texts.append(
                f"Source: {r.get('src_addr')}<br>"
                f"Region: {region}, {country}"
            )

        for hop in r.get("hops", []):
            valid_ip = next(
                (ip for ip in hop.get("ips", []) if not is_private(ip)), None
            )
            if not valid_ip:
                continue
            geo = geo_cache.get(valid_ip, {})
            if not geo or geo.get("lat") is None:
                continue
            rtts = [x for x in hop.get("rtts", []) if x]
            min_rtt = round(min(rtts), 2) if rtts else None
            path_lats.append(geo["lat"])
            path_lons.append(geo["lon"])
            path_texts.append(
                f"IP: {valid_ip}<br>"
                f"Org: {geo.get('org_name', '?')}<br>"
                f"ASN: {geo.get('asn', '?')}<br>"
                f"City: {geo.get('city', '?')}, {geo.get('country', '?')}<br>"
                f"Hop #{hop['hop']}"
                + (f" · {min_rtt} ms" if min_rtt else "")
            )

        if len(path_lats) > 1:
            b = _bucket(llm, bucket_key)
            b["lats"].extend(path_lats + [None])
            b["lons"].extend(path_lons + [None])
            b["texts"].extend(path_texts + [None])

    # Wrap US buckets under a "US" parent so the React component can detect them
    for llm in LLMs:
        us_states = {}
        intl_keys = []
        for key in list(result[llm].keys()):
            # State names are multi-word; country keys are shorter but we can't rely
            # on that. Instead check against known international countries.
            # Anything that isn't a known intl country is a US state.
            known_intl = {"France", "India", "Kenya", "Pakistan", "South Africa", "UK"}
            if key in known_intl:
                intl_keys.append(key)
            else:
                us_states[key] = result[llm].pop(key)
        if us_states:
            result[llm]["US"] = us_states

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


def export_country_exit(df, output_dir):
    if df.empty:
        _write(output_dir, "country_exit.json", [])
        return

    from collections import Counter

    normal    = df[df["never_exited"] == False]
    anomalies = df[df["never_exited"] == True]

    agg_cols = ["source_country", "llm"]
    anomaly_counts = (
        anomalies.groupby(agg_cols).size().reset_index(name="never_exited_count")
    )

    grouped = normal.groupby(agg_cols)["exit_hop"].agg(
        mean="mean", std="std", count="count"
    ).reset_index()
    grouped["mean"] = grouped["mean"].round(2)
    grouped["std"]  = grouped["std"].fillna(0).round(2)

    # Top transit countries per (source_country, llm)
    transit_map: dict = {}
    for _, row in df.iterrows():
        key = (row["source_country"], row["llm"])
        if key not in transit_map:
            transit_map[key] = Counter()
        for c in row["transit_countries"].split("|"):
            if c:
                transit_map[key][c] += 1

    merged = grouped.merge(anomaly_counts, on=agg_cols, how="left")
    merged["never_exited_count"] = merged["never_exited_count"].fillna(0).astype(int)

    rows = []
    for _, row in merged.iterrows():
        key = (row["source_country"], row["llm"])
        top_transit = [c for c, _ in transit_map.get(key, Counter()).most_common(5)]
        rows.append({
            "source_country":      row["source_country"],
            "llm":                 row["llm"],
            "mean_exit_hop":       row["mean"],
            "std_exit_hop":        row["std"],
            "count":               int(row["count"]),
            "never_exited_count":  int(row["never_exited_count"]),
            "top_transit_countries": top_transit,
        })

    _write(output_dir, "country_exit.json", rows)


def export_all(records, geo_cache, metrics, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print("  Exporting summary...")
    export_summary(records, geo_cache, output_dir)
    print("  Exporting world map paths (by country/state)...")
    export_world_map(records, geo_cache, output_dir)
    print("  Exporting hops per ISP...")
    export_hops_per_isp(metrics["hops_per_isp"], output_dir)
    print("  Exporting RTT per ISP/region...")
    export_rtt_per_isp(metrics["rtt_per_isp"], output_dir)
    print("  Exporting common ASes...")
    export_common_as(metrics["common_as"], output_dir)
    print("  Exporting hops to exit AS...")
    export_hops_to_exit_as(metrics["hops_to_exit_as"], output_dir)
    print("  Exporting country boundary exit analysis...")
    export_country_exit(metrics["country_exit"], output_dir)
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
