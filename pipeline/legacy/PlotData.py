"""
PlotData.py — Visualization suite for RIPE Atlas AI routing data.

Generates five plots saved to data/plots/:
  1. choropleth_<service>.html  — avg RTT per state, one interactive map per service
  2. bar_rtt_by_state.png       — RTT comparison across all states, grouped by service
  3. cdf_rtt.png                — cumulative RTT distribution per service
  4. scatter_rtt_vs_hops.png    — RTT vs hop count, per service
  5. sankey_region_to_service.html — avg RTT flow: US region → AI service

Run from the project root:
    python scripts/PlotData.py
"""

import os
import json
import glob
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    print("[!] plotly not installed — skipping choropleth and Sankey.")
    print("    Install with: pip install plotly\n")

# ─── Configuration ────────────────────────────────────────────────────────────

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_ROOT, "data")
US_DIR   = os.path.join(DATA_DIR, "US")
PLOTS_DIR = os.path.join(DATA_DIR, "plots")

API_DOMAINS = {
    "api.openai.com":                    "ChatGPT",
    "generativelanguage.googleapis.com": "Gemini",
    "api.anthropic.com":                 "Claude",
}

SERVICES = ["ChatGPT", "Gemini", "Claude"]

SERVICE_COLORS = {
    "ChatGPT": "#10a37f",   # OpenAI green
    "Gemini":  "#4285F4",   # Google blue
    "Claude":  "#D97706",   # Anthropic amber
}

STATE_ABBREV = {
    "Alabama": "AL",        "Alaska": "AK",         "Arizona": "AZ",
    "Arkansas": "AR",       "California": "CA",      "Colorado": "CO",
    "Connecticut": "CT",    "Delaware": "DE",        "Florida": "FL",
    "Georgia": "GA",        "Hawaii": "HI",          "Idaho": "ID",
    "Illinois": "IL",       "Indiana": "IN",         "Iowa": "IA",
    "Kansas": "KS",         "Kentucky": "KY",        "Louisiana": "LA",
    "Maine": "ME",          "Maryland": "MD",        "Massachusetts": "MA",
    "Michigan": "MI",       "Minnesota": "MN",       "Mississippi": "MS",
    "Missouri": "MO",       "Montana": "MT",         "Nebraska": "NE",
    "Nevada": "NV",         "New Hampshire": "NH",   "New Jersey": "NJ",
    "New Mexico": "NM",     "New York": "NY",        "North Carolina": "NC",
    "North Dakota": "ND",   "Ohio": "OH",            "Oklahoma": "OK",
    "Oregon": "OR",         "Pennsylvania": "PA",    "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD",    "Tennessee": "TN",
    "Texas": "TX",          "Utah": "UT",            "Vermont": "VT",
    "Virginia": "VA",       "Washington": "WA",      "West Virginia": "WV",
    "Wisconsin": "WI",      "Wyoming": "WY",
}

# West → East ordering for the bar chart
GEO_ORDER = [
    "Alaska", "Hawaii", "Washington", "Oregon", "California", "Nevada", "Idaho",
    "Montana", "Wyoming", "Utah", "Colorado", "Arizona", "New Mexico",
    "North Dakota", "South Dakota", "Nebraska", "Kansas", "Oklahoma", "Texas",
    "Minnesota", "Iowa", "Missouri", "Wisconsin", "Illinois", "Michigan", "Indiana",
    "Arkansas", "Louisiana", "Mississippi", "Alabama", "Tennessee", "Kentucky",
    "Ohio", "Georgia", "Florida", "South Carolina", "North Carolina",
    "West Virginia", "Virginia", "Pennsylvania", "Maryland", "Delaware",
    "New York", "New Jersey", "Connecticut", "Rhode Island", "Massachusetts",
    "Vermont", "New Hampshire", "Maine",
]

# Member regions used in the Sankey diagram
REGIONS = {
    "West / Central":       ["Alaska", "Nevada", "Utah", "California", "Washington",
                             "Oregon", "Arizona", "Colorado", "Oklahoma", "Kansas",
                             "Nebraska", "Iowa", "Missouri"],
    "South / Midwest":      ["Hawaii", "New Mexico", "Wyoming", "Texas", "Illinois",
                             "Arkansas", "Louisiana", "Mississippi", "Alabama",
                             "Tennessee", "Kentucky", "Indiana", "Michigan"],
    "North / Mid-Atlantic": ["Montana", "North Dakota", "South Dakota", "New York",
                             "Virginia", "Minnesota", "Wisconsin", "Ohio",
                             "Pennsylvania", "West Virginia", "Maryland", "Delaware"],
    "East / New England":   ["Idaho", "Maine", "Vermont", "Florida", "New Jersey",
                             "Georgia", "South Carolina", "North Carolina",
                             "Connecticut", "Rhode Island", "Massachusetts",
                             "New Hampshire"],
}
STATE_TO_REGION = {s: r for r, states in REGIONS.items() for s in states}

# Fallback IP-prefix → service (for measurements without a mapping file entry)
IP_PREFIX_TO_SERVICE = {
    "104.18":  "ChatGPT",
    "162.159": "ChatGPT",
    "142.250": "Gemini",
    "142.251": "Gemini",
    "160.79":  "Claude",
}

# ─── Data Loading ─────────────────────────────────────────────────────────────

def loadMeasurementIndex():
    """Return {str(measurement_id): service_name} for API endpoints only."""
    index = {}
    for mf in glob.glob(os.path.join(DATA_DIR, "ripe_measurement_mapping_*.json")):
        with open(mf) as f:
            mapping = json.load(f)
        for _svc, domains in mapping.items():
            for domain, mid in domains.items():
                if domain in API_DOMAINS:
                    index[str(mid)] = API_DOMAINS[domain]
    return index

def inferServiceFromIp(ip):
    """Map a destination IP to a service name via known IP prefixes."""
    prefix = ".".join(ip.split(".")[:2])
    return IP_PREFIX_TO_SERVICE.get(prefix)

def probeMetrics(probe):
    """
    Extract (avg_rtt_ms, hop_count) from a single probe result.
    Walks hops in reverse to find the deepest one with valid RTTs.
    Returns None if no valid hop is found.
    """
    for hop in reversed(probe.get("result", [])):
        rtts = [p["rtt"] for p in hop.get("result", []) if "rtt" in p]
        if rtts:
            return float(np.mean(rtts)), int(hop["hop"])
    return None

def loadAllData():
    """
    Walk data/US/<state>/ripe_results_<id>.json and build:
        {state: {service: [(avg_rtt_ms, hop_count), ...]}}
    Service identity is resolved via mapping files first, then IP inference.
    """
    index   = loadMeasurementIndex()
    data    = defaultdict(lambda: defaultdict(list))
    skipped = 0

    for stateDir in sorted(glob.glob(os.path.join(US_DIR, "*"))):
        if not os.path.isdir(stateDir):
            continue
        state = os.path.basename(stateDir)

        for resultFile in glob.glob(os.path.join(stateDir, "ripe_results_*.json")):
            mid = (os.path.basename(resultFile)
                   .replace("ripe_results_", "")
                   .replace(".json", ""))

            with open(resultFile) as f:
                probes = json.load(f)

            service = index.get(mid)
            if not service and probes:
                service = inferServiceFromIp(probes[0].get("dst_addr", ""))
            if not service:
                skipped += 1
                continue

            for probe in probes:
                m = probeMetrics(probe)
                if m:
                    data[state][service].append(m)

    if skipped:
        print(f"  [!] Skipped {skipped} unresolvable file(s).")
    return data

def summarize(data):
    """
    Derive per-state means and flat per-service measurement lists.
    Returns:
        stateMeans:  {state: {service: avg_rtt}}
        allMeasure:  {service: [(avg_rtt, hop_count), ...]}
    """
    stateMeans  = defaultdict(dict)
    allMeasure  = defaultdict(list)

    for state, services in data.items():
        for service, measurements in services.items():
            rtts = [m[0] for m in measurements]
            stateMeans[state][service] = float(np.mean(rtts))
            allMeasure[service].extend(measurements)

    return stateMeans, allMeasure

# ─── Plot 1: Choropleth Maps ───────────────────────────────────────────────────

def plotChoropleth(stateMeans):
    if not HAS_PLOTLY:
        return

    print("  [1/5] Choropleth maps...")

    domain_label = {
        "ChatGPT": "api.openai.com",
        "Gemini":  "generativelanguage.googleapis.com",
        "Claude":  "api.anthropic.com",
    }

    # Build per-service data first so we can compute both global and local scales
    service_data = {}
    for service in SERVICES:
        locs, vals, texts = [], [], []
        for state, means in stateMeans.items():
            if service in means and state in STATE_ABBREV:
                locs.append(STATE_ABBREV[state])
                vals.append(round(means[service], 1))
                texts.append(f"{state}<br>{means[service]:.1f} ms")
        service_data[service] = (locs, vals, texts)

    # Shared scale across all services (for fair cross-service comparison)
    all_vals = [v for _, vals, _ in service_data.values() for v in vals]
    global_min, global_max = min(all_vals), max(all_vals)

    def makeChoropleth(service, zmin, zmax, subtitle, filename):
        locs, vals, texts = service_data[service]
        fig = go.Figure(go.Choropleth(
            locations=locs,
            z=vals,
            text=texts,
            locationmode="USA-states",
            zmin=zmin,
            zmax=zmax,
            colorscale="RdYlGn_r",
            colorbar=dict(
                title=dict(text="Avg RTT (ms)", font=dict(size=12)),
                thickness=16,
                tickformat=".0f",
            ),
            hovertemplate="%{text}<extra></extra>",
        ))
        fig.update_layout(
            title=dict(
                text=(
                    f"<b>{service}</b> — Avg RTT by State"
                    f"<br><sup>{domain_label[service]}"
                    f" &nbsp;|&nbsp; {subtitle}</sup>"
                ),
                font=dict(size=16),
                x=0.5,
            ),
            geo=dict(scope="usa", showlakes=False, bgcolor="#f8f8f8"),
            margin=dict(l=0, r=0, t=80, b=0),
            width=950, height=570,
        )
        path = os.path.join(PLOTS_DIR, filename)
        fig.write_html(path)
        return path

    for service in SERVICES:
        _, vals, _ = service_data[service]
        svc_min  = min(vals)
        svc_max  = max(vals)
        svc_mean = round(float(np.mean(vals)), 1)

        # Version 1 — shared scale (compare across services)
        p1 = makeChoropleth(
            service,
            zmin=global_min,
            zmax=global_max,
            subtitle=f"shared scale {global_min:.0f}–{global_max:.0f} ms",
            filename=f"choropleth_{service.lower()}.html",
        )
        print(f"       → {p1}  (shared scale)")

        # Version 2 — per-service scale (see geographic variation within service)
        p2 = makeChoropleth(
            service,
            zmin=svc_min,
            zmax=svc_max,
            subtitle=(
                f"relative scale {svc_min:.1f} ms (best) → {svc_max:.1f} ms (worst)"
                f" &nbsp;|&nbsp; national avg: {svc_mean} ms"
            ),
            filename=f"choropleth_{service.lower()}_relative.html",
        )
        print(f"       → {p2}  (relative scale  {svc_min:.1f}–{svc_max:.1f} ms)")

# ─── Plot 2: Grouped Bar Chart ─────────────────────────────────────────────────

def plotBarChart(stateMeans):
    print("  [2/5] Grouped bar chart...")

    states = [s for s in GEO_ORDER if s in stateMeans]
    n      = len(states)
    x      = np.arange(n)
    width  = 0.27

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(24, 6))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#1c1c1c")

    for i, service in enumerate(SERVICES):
        vals = [stateMeans[s].get(service, np.nan) for s in states]
        ax.bar(
            x + (i - 1) * width, vals, width,
            label=service,
            color=SERVICE_COLORS[service],
            alpha=0.88,
            edgecolor="none",
            zorder=3,
        )

    # Region separator lines and labels
    region_breaks = []
    region_label_positions = []
    current_region, region_start = None, 0
    for idx, state in enumerate(states):
        r = STATE_TO_REGION.get(state, "")
        if r != current_region:
            if current_region is not None:
                region_breaks.append(idx - 0.5)
                region_label_positions.append((region_start + idx - 1) / 2)
            current_region = r
            region_start   = idx
    region_label_positions.append((region_start + n - 1) / 2)

    for xb in region_breaks:
        ax.axvline(xb, color="#444444", linewidth=1, linestyle="--", alpha=0.8, zorder=2)

    region_names = list(REGIONS.keys())
    for pos, label in zip(region_label_positions, region_names):
        ax.text(pos, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 200,
                label, ha="center", va="bottom",
                fontsize=7.5, color="#888888", style="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(
        [STATE_ABBREV.get(s, s) for s in states],
        rotation=45, ha="right", fontsize=8.5, color="#cccccc",
    )
    ax.set_ylabel("Avg RTT (ms)", color="#cccccc", fontsize=11)
    ax.set_title(
        "Average RTT to AI API Endpoints — All US States (West → East)",
        color="white", fontsize=13, pad=14,
    )
    ax.tick_params(colors="#cccccc")
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.grid(axis="y", color="#333333", linewidth=0.5, alpha=0.7, zorder=1)
    ax.legend(
        facecolor="#1c1c1c", edgecolor="#444444",
        labelcolor="white", fontsize=10, loc="upper right",
    )
    ax.set_xlim(-0.5, n - 0.5)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "bar_rtt_by_state.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"       → {path}")

# ─── Plot 3: CDF ──────────────────────────────────────────────────────────────

def plotCDF(allMeasure):
    print("  [3/5] CDF plot...")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#1c1c1c")

    median_y_offsets = {"ChatGPT": 0.62, "Gemini": 0.48, "Claude": 0.34}

    for service in SERVICES:
        rtts = sorted(m[0] for m in allMeasure[service])
        if not rtts:
            continue
        cdf    = np.arange(1, len(rtts) + 1) / len(rtts)
        median = float(np.median(rtts))
        p95    = float(np.percentile(rtts, 95))

        ax.plot(rtts, cdf,
                label=f"{service}  (median {median:.0f} ms, p95 {p95:.0f} ms)",
                color=SERVICE_COLORS[service],
                linewidth=2.5, zorder=3)

        # Median line + annotation
        ax.axvline(median, color=SERVICE_COLORS[service],
                   linewidth=1.2, linestyle="--", alpha=0.55, zorder=2)
        ax.annotate(
            f"{median:.0f} ms",
            xy=(median, median_y_offsets[service]),
            xytext=(median + max(rtts) * 0.02, median_y_offsets[service]),
            color=SERVICE_COLORS[service], fontsize=8.5,
            arrowprops=dict(arrowstyle="-", color=SERVICE_COLORS[service], alpha=0.5),
        )

    ax.set_xlabel("RTT (ms)", color="#cccccc", fontsize=11)
    ax.set_ylabel("Cumulative Fraction of Probes", color="#cccccc", fontsize=11)
    ax.set_title("CDF of RTT — All US Probes per AI Service", color="white", fontsize=13)
    ax.tick_params(colors="#cccccc")
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.grid(color="#333333", linewidth=0.5, alpha=0.7, zorder=1)
    ax.legend(facecolor="#1c1c1c", edgecolor="#444444", labelcolor="white", fontsize=9.5)
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1.03)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "cdf_rtt.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"       → {path}")

# ─── Plot 4: Scatter RTT vs Hop Count ─────────────────────────────────────────

def plotScatter(allMeasure):
    print("  [4/5] RTT vs hop-count scatter...")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#1c1c1c")

    rng = np.random.default_rng(42)   # deterministic jitter

    for service in SERVICES:
        rtts = np.array([m[0] for m in allMeasure[service]])
        hops = np.array([m[1] for m in allMeasure[service]], dtype=float)
        # Small horizontal jitter so overlapping points are visible
        hops_jittered = hops + rng.normal(0, 0.15, len(hops))

        ax.scatter(
            hops_jittered, rtts,
            alpha=0.55, s=45,
            color=SERVICE_COLORS[service],
            label=service,
            edgecolors="none",
            zorder=3,
        )

        # Trend line
        if len(hops) > 2:
            m_coef, b = np.polyfit(hops, rtts, 1)
            x_fit = np.linspace(hops.min(), hops.max(), 100)
            ax.plot(x_fit, m_coef * x_fit + b,
                    color=SERVICE_COLORS[service],
                    linewidth=1.5, linestyle="--", alpha=0.6, zorder=2)

    ax.set_xlabel("Hop Count", color="#cccccc", fontsize=11)
    ax.set_ylabel("Avg RTT (ms)", color="#cccccc", fontsize=11)
    ax.set_title("RTT vs Hop Count per Probe  (dashed = trend line)",
                 color="white", fontsize=13)
    ax.tick_params(colors="#cccccc")
    for spine in ax.spines.values():
        spine.set_color("#333333")
    ax.grid(color="#333333", linewidth=0.5, alpha=0.7, zorder=1)
    ax.legend(facecolor="#1c1c1c", edgecolor="#444444", labelcolor="white", fontsize=10)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, "scatter_rtt_vs_hops.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"       → {path}")

# ─── Plot 5: Sankey Diagram ────────────────────────────────────────────────────

def plotSankey(stateMeans):
    if not HAS_PLOTLY:
        return
    print("  [5/5] Sankey diagram...")

    region_names  = list(REGIONS.keys())
    service_names = SERVICES
    all_labels    = region_names + service_names

    region_idx  = {r: i                    for i, r in enumerate(region_names)}
    service_idx = {s: len(region_names) + i for i, s in enumerate(service_names)}

    link_colors = {
        "ChatGPT": "rgba(16,163,127,0.38)",
        "Gemini":  "rgba(66,133,244,0.38)",
        "Claude":  "rgba(217,119,6,0.38)",
    }
    node_colors = (
        ["#4a6fa5"] * len(region_names) +
        [SERVICE_COLORS[s] for s in service_names]
    )

    sources, targets, values, colors, hover = [], [], [], [], []

    for region, states in REGIONS.items():
        for service in SERVICES:
            rtts = [
                stateMeans[s][service]
                for s in states
                if s in stateMeans and service in stateMeans[s]
            ]
            if not rtts:
                continue
            avg = round(float(np.mean(rtts)), 1)
            sources.append(region_idx[region])
            targets.append(service_idx[service])
            values.append(avg)
            colors.append(link_colors[service])
            hover.append(
                f"<b>{region}</b> → <b>{service}</b><br>"
                f"Avg RTT: {avg} ms  ({len(rtts)} states)"
            )

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25,
            thickness=22,
            line=dict(color="#222222", width=0.5),
            label=all_labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=colors,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
        ),
    ))
    fig.update_layout(
        title=dict(
            text="Average RTT Flow: US Region → AI Service API",
            font=dict(size=16, color="white"),
            x=0.5,
        ),
        font=dict(size=13, color="white"),
        paper_bgcolor="#111111",
        width=960, height=540,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    path = os.path.join(PLOTS_DIR, "sankey_region_to_service.html")
    fig.write_html(path)
    print(f"       → {path}")

# ─── Summary Table ────────────────────────────────────────────────────────────

def printSummaryTable(stateMeans):
    print(f"\n{'State':<22} {'ChatGPT':>10} {'Gemini':>10} {'Claude':>10}  {'Fastest'}")
    print("─" * 65)
    for state in [s for s in GEO_ORDER if s in stateMeans]:
        means   = stateMeans[state]
        fastest = min(means, key=means.get)
        row = f"{state:<22}"
        for svc in SERVICES:
            val = means.get(svc)
            row += f"  {val:>7.1f}ms" if val is not None else f"  {'—':>7}"
        row += f"  {fastest}"
        print(row)

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)

    print("Loading data from data/US/ ...")
    data = loadAllData()
    print(f"  Loaded {len(data)} states.\n")

    stateMeans, allMeasure = summarize(data)

    printSummaryTable(stateMeans)

    # Global stats
    print("\nGlobal averages across all probes:")
    for service in SERVICES:
        all_rtts = [m[0] for m in allMeasure[service]]
        print(f"  {service:<10}  mean={np.mean(all_rtts):.1f}ms  "
              f"median={np.median(all_rtts):.1f}ms  "
              f"p95={np.percentile(all_rtts, 95):.1f}ms  "
              f"n={len(all_rtts)}")

    print(f"\nGenerating plots → {PLOTS_DIR}/")
    plotChoropleth(stateMeans)
    plotBarChart(stateMeans)
    plotCDF(allMeasure)
    plotScatter(allMeasure)
    plotSankey(stateMeans)

    print("\nAll done. Files written:")
    for f in sorted(glob.glob(os.path.join(PLOTS_DIR, "*"))):
        size_kb = os.path.getsize(f) // 1024
        print(f"  {os.path.basename(f):<45}  {size_kb:>5} KB")


if __name__ == "__main__":
    main()
