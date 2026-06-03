# RIPE Atlas Traceroute Visualization — Implementation Plan

## Overview

This document describes the planned architecture, data flow, and output specifications for a world-map visualization and analytics suite built on top of RIPE Atlas traceroute data collected toward three LLM API endpoints: **Claude**, **Gemini**, and **ChatGPT**.

The data covers multiple days of traceroutes from RIPE Atlas probes distributed across 50 US states and several international countries. The goal is to:

1. Visualize the full network paths on an interactive world map, colored by LLM service
2. Compute and plot four analytical metrics about hop counts, latency, shared infrastructure, and AS exit behavior

---

## Data Context

### Folder Structure

```
data/
  <contributor>/                      e.g. ashay/
    ripe_measurement_mapping_<ts>.json
    US/
      <State>/
        ripe_results_<measurement_id>.json
    international/
      <Country>/
        ripe_results_<measurement_id>.json
```

### Measurement Mapping Format

Each mapping file links an LLM service name to a domain and a RIPE Atlas measurement ID:

```json
{
  "ChatGPT": {},
  "Gemini": {
    "generativelanguage.googleapis.com": 176455641
  },
  "Claude": {
    "api.anthropic.com": 176455646
  }
}
```

The mapping file is the key to knowing **which measurement ID belongs to which LLM**. A result file named `ripe_results_176455641.json` therefore belongs to Gemini.

### RIPE Result File Format

Each result file is a JSON array. Each element is one probe's traceroute:

```json
{
  "dst_name": "172.217.17.202",
  "dst_addr": "172.217.17.202",
  "src_addr": "63.130.83.29",
  "proto": "ICMP",
  "result": [
    {
      "hop": 1,
      "result": [
        { "from": "63.130.83.25", "ttl": 255, "rtt": 1.236 },
        { "from": "63.130.83.25", "ttl": 255, "rtt": 0.348 },
        { "from": "63.130.83.25", "ttl": 255, "rtt": 0.451 }
      ]
    },
    {
      "hop": 2,
      "result": [
        { "from": "72.14.195.68", "ttl": 250, "rtt": 1.52 }
      ]
    }
  ]
}
```

Key fields:
- `src_addr` — probe's own IP (the "starting point")
- `result[].hop` — hop number (1-indexed)
- `result[].result[].from` — IP of the router at that hop
- `result[].result[].rtt` — round-trip time in milliseconds for that packet

Some hops return `*` (timeout/no response) — these must be handled as gaps.

### 4-Day Aggregation

The same measurement may have been run on multiple days, producing multiple result files with the same measurement ID. The same router IP may appear across runs. Deduplication logic must:
- Track all unique IPs seen
- Track how many times each IP appeared across runs
- For analytics, aggregate per-traceroute metrics (mean/median across runs for the same probe and measurement)

---

## Planned Project Structure

```
scripts/
  VisualizeWorldMap.py          ← main entry point; runs all modules in order
  viz/
    __init__.py
    loader.py                   ← load, tag, and aggregate all traceroute data
    resolver.py                 ← IP → geo (lat/lon/ISP) + ASN, with disk cache
    analytics.py                ← compute all four metrics from enriched data
    plots/
      __init__.py
      world_map.py              ← interactive world map with colored paths
      hops_per_isp.py           ← metric (a): hops per starting ISP per LLM
      rtt_per_isp.py            ← metric (b): total RTT per ISP per region
      common_as.py              ← metric (c): ASes shared across LLMs
      hops_to_exit_as.py        ← metric (d): hops to exit source ISP's AS
outputs/
  geo_cache.json                ← persisted IP resolution results (auto-generated)
  world_map.html
  hops_per_isp.html
  rtt_per_isp_region.html
  common_as.html
  hops_to_exit_as.html
```

---

## Data Flow

```
Step 1 ─ LOAD (loader.py)
  Read all ripe_measurement_mapping_*.json files
  Build: measurement_id → (llm_service, domain)

  Read all ripe_results_*.json files
  Derive from path: contributor, country/state
  Tag each traceroute with: llm_service, source_region, source_country
  Extract per-traceroute record:
    { probe_src_ip, dst_addr, llm, region, country, hops: [{hop_n, ips, rtts}] }

  Aggregate across multiple runs (same measurement_id):
    group by (measurement_id, probe_src_ip)
    average numeric fields, union unique IPs

        │
        ▼

Step 2 ─ RESOLVE (resolver.py)
  Collect all unique IPs across every hop in every traceroute
  Batch query ip-api.com (100 IPs per request, max 45 req/min)
    → lat, lon, country, city, isp, org, as (ASN string)
  Also query CAIDA / Cymru DNS for authoritative ASN + org name
  Write full results to outputs/geo_cache.json
  On re-runs, load from cache — skip network calls for known IPs

        │
        ▼

Step 3 ─ ENRICH
  Join resolution results back onto each hop in each traceroute
  Each hop IP now carries: lat, lon, asn, org, isp, city, country

        │
        ▼

Step 4 ─ ANALYTICS (analytics.py)
  Compute four structured result tables (as pandas DataFrames or dicts)
  Pass each to the relevant plot module

        │
        ▼

Step 5 ─ PLOTS
  Each plot module receives its data, renders a Plotly figure, writes HTML
```

---

## Module Responsibilities

### `loader.py`

**Inputs:** All JSON files under `data/`  
**Outputs:** A list of enriched traceroute records (Python dicts)

Key logic:
- Parse all mapping files to build `{measurement_id: {llm, domain}}`
- Walk all `ripe_results_*.json` paths; extract measurement ID from filename
- Derive region from directory name (e.g. `data/ashay/US/Kansas/` → region=`Kansas`, country=`US`)
- For each result file, emit one record per probe per run
- Deduplication: group records sharing the same `(measurement_id, src_addr)` across days; average RTTs, union hop IPs

### `resolver.py`

**Inputs:** A set of unique IP strings  
**Outputs:** `{ip: {lat, lon, asn, org, isp, city, country}}` dict; also persisted to `outputs/geo_cache.json`

Key logic:
- Load existing cache first; only query IPs not yet cached
- Filter out private/RFC1918 IPs (10.x, 172.16–31.x, 192.168.x) — mark them as `private=True`, skip geo lookup
- Use ip-api.com batch endpoint (POST `/batch`): up to 100 IPs per call, throttle to 44 req/min
- Fall back to CAIDA file or Cymru DNS for ASN if ip-api.com's ASN field is absent or Unknown
- Write updated cache after resolution

### `analytics.py`

**Inputs:** Fully enriched traceroute records  
**Outputs:** Four DataFrames passed to plot modules (see metric details below)

### `VisualizeWorldMap.py`

Top-level runner:
```
loader.load()  →  resolver.resolve()  →  analytics.compute()  →  run all plot modules
```

Prints a summary table to stdout (total traceroutes, unique IPs resolved, cache hit rate).

---

## Visualization 1 — World Map (`world_map.py`)

### What it shows
An interactive Plotly globe/map with one **polyline per traceroute** drawn between consecutive hop coordinates. Each line is colored by LLM service.

### Color scheme
| LLM | Color |
|---|---|
| Claude | `#D97706` (amber/orange) |
| Gemini | `#2563EB` (blue) |
| ChatGPT | `#16A34A` (green) |

### Rendering rules
- Each hop with a resolved lat/lon becomes a node (circle marker)
- Consecutive hops are connected by a line segment (great-circle path via `scattergeo` with `mode='lines+markers'`)
- Private IPs are skipped; the line has a gap at that hop
- Hops with no response (`*`) are also skipped
- Node size = fixed (small); opacity = 0.7 for lines, 1.0 for node markers
- LLM legend entries are toggleable — clicking hides/shows all traces for that LLM

### Hover tooltip on a node
```
IP:       63.130.83.25
Org:      AT&T Services Inc.
ASN:      AS7018
City:     Dallas, TX, US
Hop #:    1
Seen in:  3 runs
```

### Aggregation for the map
- If aggregating across 4 days: show one representative path per `(measurement_id, src_addr)` pair — use the run with the most complete hop coverage (fewest `*` hops)
- Optionally add a toggle: "Show all runs" vs "Show representative path"

### Output
`outputs/world_map.html` — fully self-contained interactive HTML

---

## Metric (a) — Hops per Starting ISP (`hops_per_isp.py`)

### Question answered
*How many hops does it take to reach each LLM's server, broken down by the ISP that the RIPE probe is connected to?*

### Definition of "Starting ISP"
The `org` or `isp` field of the probe's **first non-private hop** (hop 1 is often within the probe's own LAN; use the first hop with a public routable IP and a resolved org).

### Computation (`analytics.py`)
For each traceroute record:
- Identify starting ISP from first public hop
- Count total number of hops with a valid `from` IP (exclude `*`)
- Emit `(starting_isp, llm, hop_count)`
- Aggregate: `mean` and `std` of `hop_count` grouped by `(starting_isp, llm)`

### Plot
- **Type:** Grouped bar chart
- **X-axis:** ISP name (sorted by average total hops descending)
- **Y-axis:** Average hop count
- **Error bars:** ±1 standard deviation
- **Groups:** Three bars per ISP, one per LLM (Claude, Gemini, ChatGPT), colored accordingly
- **Secondary view:** Toggle to box plot showing full distribution (min, quartiles, max) per ISP per LLM
- **Filter control:** Dropdown to filter by source country (US / International / All)

### Output
`outputs/hops_per_isp.html`

---

## Metric (b) — Total RTT per ISP per Region (`rtt_per_isp.py`)

### Question answered
*How long does a full traceroute from a given ISP in a given region take to reach each LLM server?*

### Definition of "Total RTT"
The RTT of the **last responding hop** in the traceroute (i.e., the hop closest to the destination with a valid RTT). This represents the one-way propagation delay to (approximately) the LLM server.

> Note: RIPE traceroute RTTs are measured round-trip from the probe, so the last hop RTT is a reasonable proxy for end-to-end latency.

If the final hop has `*` (no response), walk backward to find the last hop with a valid RTT.

### Computation (`analytics.py`)
For each traceroute record:
- Find the last hop with a valid `rtt`
- Take the **minimum RTT** among that hop's packets (to reduce queuing jitter)
- Emit `(source_region, starting_isp, llm, total_rtt_ms)`
- Aggregate: `mean` grouped by `(source_region, starting_isp, llm)`

### Plot
- **Type:** Heatmap (primary) + grouped bar chart (secondary, togglable)
- **Heatmap rows:** Source region (US state or country name)
- **Heatmap columns:** Starting ISP
- **Cell value:** Average total RTT in ms
- **Color scale:** `Viridis` (low = purple/fast, high = yellow/slow)
- **Facets:** One heatmap per LLM, shown side-by-side or as tabs
- **Bar chart alternative:** Select a specific ISP from a dropdown; show bar chart of RTT by region for each LLM

### Output
`outputs/rtt_per_isp_region.html`

---

## Metric (c) — Common ASes Across LLMs (`common_as.py`)

### Question answered
*Which autonomous systems (routers/networks) appear in traceroutes to multiple LLMs? These represent shared backbone infrastructure.*

### Computation (`analytics.py`)
For each unique ASN seen in any hop in any traceroute:
- Record the set of LLMs whose traceroutes it appeared in: `{Claude, Gemini, ChatGPT}` (any subset)
- Record total appearances (sum of how many traceroute hop records contain this ASN)
- Record the org name associated with the ASN
- Emit `(asn, org_name, llm_set, total_appearances)`

### Classification
| Appears in | Label |
|---|---|
| All 3 LLMs | Shared backbone |
| 2 LLMs | Partially shared |
| 1 LLM only | LLM-specific |

### Plot
- **Type:** Horizontal bar chart
- **Y-axis:** `AS<number> — <org name>` (top 30 by total appearances)
- **X-axis:** Total appearance count across all traceroutes
- **Bar color:** Categorical — one color per LLM-set membership pattern (e.g. "All 3", "Claude+Gemini", "Claude only", etc.)
- **Highlight:** ASes in all 3 LLMs have a bold outline and a star marker
- **Sort options:** Toggle between "sort by total appearances" and "sort by commonality (all-3 first)"
- **Hover tooltip:**
  ```
  ASN:         AS15169
  Org:         Google LLC
  Appears in:  Claude, Gemini, ChatGPT
  Total hits:  847 hop records
  ```

### Output
`outputs/common_as.html`

---

## Metric (d) — Hops to Exit Source ISP's AS (`hops_to_exit_as.py`)

### Question answered
*How many hops does it take for a traceroute to leave the source ISP's own network, broken down by country and ISP?*

### Definition of "Source ISP's AS"
The ASN of the probe's **source IP** (`src_addr` field). This is the AS the probe is directly connected to — the "first mile" ISP.

### Computation (`analytics.py`)
For each traceroute record:
- Resolve the ASN of `src_addr` (from the geo cache)
- Walk hops in order (hop 1, 2, 3, …)
- For each hop, check the ASN of its `from` IP
- Count the number of consecutive hops (from hop 1) whose ASN equals the source ASN
- The first hop where the ASN differs = "exited the ISP's AS"; `hops_to_exit = that hop number - 1`
- If all hops are within the same AS: `hops_to_exit = total_hops` (never exited — flag as anomalous)
- Emit `(source_country, source_isp, llm, hops_to_exit)`
- Aggregate: `mean` and `std` grouped by `(source_country, source_isp)`

### Plot
- **Type:** Grouped bar chart, faceted by country
- **X-axis:** ISP name (within each country panel)
- **Y-axis:** Average hops to exit source AS
- **Error bars:** ±1 standard deviation
- **Groups:** One color per LLM (to see if exit behavior differs by destination)
- **Facet control:** Dropdown to select specific country, or show all countries as a scrollable set of subplots
- **Anomaly flag:** Traceroutes where `hops_to_exit = total_hops` are excluded from the mean but counted and shown as an annotation (e.g. "3 traceroutes never exited the source AS")

### Output
`outputs/hops_to_exit_as.html`

---

## Dependencies

All already in `requirements.txt` or easily added:

| Package | Purpose |
|---|---|
| `plotly` | All interactive visualizations |
| `pandas` | Tabular aggregation for all metrics |
| `requests` | ip-api.com batch queries |
| `python-dotenv` | Environment config (API keys, paths) |
| `ripe.atlas.cousteau` | Already used for data collection |

No new major dependencies needed. `pandas` may need to be added to `requirements.txt`.

---

## Design Decisions (Open Questions)

These should be confirmed before implementation begins:

| # | Decision | Options |
|---|---|---|
| 1 | **Total RTT definition** | Last-hop RTT (end-to-end) vs. sum of all per-hop RTTs (path cost) |
| 2 | **Starting ISP identification** | First public hop's org (recommended) vs. RIPE probe's registered metadata |
| 3 | **Map aggregation** | One representative path per `(measurement_id, probe)` vs. all runs overlaid with opacity |
| 4 | **Output format** | Separate HTML files per chart vs. single multi-tab dashboard HTML |
| 5 | **Private IP handling** | Skip and leave gap in path vs. draw a dashed segment to show LAN hops exist |
| 6 | **"*" hop handling** | Skip entirely vs. draw a node with label "No response" at an interpolated position |

---

## Open Constraints & Known Limitations

- **ip-api.com accuracy:** Country-level is ~98% accurate. City-level and lat/lon are ~70% accurate. For transit/backbone IPs, the resolved location is typically the ISP's headquarters or PoP city, **not** the physical router location. Treat map node positions as approximate.
- **Anycast IPs:** Common for large providers (Google, Cloudflare). A single IP may resolve to different physical locations depending on the querying probe's region. ip-api.com will return one location; the true path may differ.
- **4-day overlap:** The same probe hitting the same destination on different days may take slightly different paths. This is expected behavior (ECMP, BGP changes). Averaging is appropriate for metrics; showing all paths on the map is informative.
- **Measurement ID → LLM mapping:** If a measurement mapping file contains an empty dict for a service (e.g. `"ChatGPT": {}`), that service has no data in that contributor's dataset — skip it silently.

---

## Output Summary

| File | Content |
|---|---|
| `outputs/world_map.html` | Interactive world map with color-coded paths per LLM |
| `outputs/hops_per_isp.html` | Bar/box chart: hops per starting ISP grouped by LLM |
| `outputs/rtt_per_isp_region.html` | Heatmap: RTT by ISP × region, faceted by LLM |
| `outputs/common_as.html` | Horizontal bar chart: ASes shared across LLMs |
| `outputs/hops_to_exit_as.html` | Bar chart: hops to exit source AS by country and ISP |
| `outputs/geo_cache.json` | Persisted IP resolution cache (auto-generated, not committed) |
