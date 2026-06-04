# RIPE Atlas — LLM Routing Analytics

A network measurement and visualization project that maps routing infrastructure and latency from RIPE Atlas probes worldwide to the API endpoints of three major LLM services: **Claude** (Anthropic), **Gemini** (Google), and **ChatGPT** (OpenAI).

Traceroutes were collected over multiple days from probes across all 50 US states and six international countries. The pipeline resolves every hop IP to its geolocation and autonomous system, computes four analytical metrics, and serves results through an interactive React dashboard.

---

## Data

### Coverage

| Contributor | Collection Dates | Regions |
|---|---|---|
| Urmil | 2026-05-29 — 2026-05-30 | All 50 US states + 6 countries |
| Aryan | 2026-05-27 | All 50 US states + 6 countries |
| Ashay | 2026-06-03 | All 50 US states |

**International countries:** France, India, Kenya, Pakistan, South Africa, UK

**Total across all contributors:** 1,773 aggregated traceroutes, 624 raw result files, ~2,600 unique public IPs resolved.

### Structure

```
data/
  <Contributor>/
    ripe_measurement_mapping_<timestamp>.json   # maps measurement ID → LLM service + domain
    ripe_intl_mapping_<timestamp>.json          # international equivalent
    US/
      <State>/
        ripe_results_<measurement_id>.json      # raw traceroute array from RIPE Atlas
    international/
      <Country>/
        ripe_results_<measurement_id>.json
```

### Measurement Mapping Format

Each mapping file links a measurement ID to an LLM service and target domain:

```json
{
  "Claude":  { "api.anthropic.com":               175506361 },
  "Gemini":  { "generativelanguage.googleapis.com": 175506359 },
  "ChatGPT": { "api.openai.com":                   175506356 }
}
```

### Result File Format

Each file is a JSON array — one element per probe's traceroute:

```json
{
  "src_addr": "63.130.83.29",
  "dst_addr": "172.217.17.202",
  "proto": "ICMP",
  "result": [
    {
      "hop": 1,
      "result": [
        { "from": "63.130.83.25", "ttl": 255, "rtt": 1.236 },
        { "from": "63.130.83.25", "ttl": 255, "rtt": 0.348 }
      ]
    }
  ]
}
```

Hops with no response return `*` packets — the pipeline treats these as gaps.

---

## Methodology

### Step 1 — Load & Aggregate

`pipeline/viz/loader.py` scans all `ripe_measurement_mapping_*.json` files to build a lookup from measurement ID to LLM service. It then reads every `ripe_results_*.json`, tags each traceroute with its contributor, region, country, and LLM, and groups runs by `(measurement_id, src_addr)`.

When the same probe ran the same measurement on multiple days, its runs are merged: hop IPs are unioned and RTTs are concatenated across runs. This gives one canonical record per `(probe, measurement)` pair that captures path variation over the 4-day window.

### Step 2 — Resolve IPs

`pipeline/viz/resolver.py` collects all unique IPs across every hop in every traceroute and resolves them in batches of 100 via the [ip-api.com](https://ip-api.com) batch endpoint (rate-limited to 44 req/min). Each IP is resolved to:

- Latitude / longitude
- Country, city
- ISP name
- ASN and organisation name

Private / RFC-1918 IPs are skipped. Results are persisted to `outputs/geo_cache.json` so subsequent runs skip already-resolved IPs.

For IPs where ip-api.com returns an unknown ASN, a fallback query is made via [Cymru DNS](https://www.team-cymru.com/ip-asn-mapping) (`<reversed-ip>.origin.asn.cymru.com`). Organisation names are further cross-referenced against the [CAIDA AS-to-Org dataset](https://www.caida.org/catalog/datasets/as-organizations/) (`latest.as-org2info.txt`) if present.

> **Accuracy note:** Country-level resolution is ~98% accurate. City-level and lat/lon are ~70% accurate. Backbone transit IPs typically resolve to the ISP's headquarters or nearest PoP city, not the physical router location.

### Step 3 — Enrich

Geo and ASN data from Step 2 is joined back onto every hop in every traceroute record. Each hop IP then carries: `lat`, `lon`, `asn`, `org_name`, `isp`, `city`, `country`.

### Step 4 — Compute Analytics

`pipeline/viz/analytics.py` computes four metrics from the enriched records:

#### (a) Hops per Starting ISP
The starting ISP is identified as the `org_name` of the **first non-private hop** in the traceroute. For each `(starting_isp, llm)` pair the pipeline computes mean and standard deviation of hop count across all matching traceroutes.

#### (b) End-to-End RTT per ISP per Region
The end-to-end latency proxy is the **minimum RTT of the last responding hop** — the hop closest to the destination with a valid RTT value. Taking the minimum across that hop's packets reduces queuing jitter. Results are grouped and averaged by `(source_region, starting_isp, llm)`.

#### (c) Common Autonomous Systems
Every ASN appearing in any hop of any traceroute is recorded. For each ASN the pipeline tracks which LLMs' traceroutes it appeared in (`{Claude, Gemini, ChatGPT}` or any subset) and the total number of hop records it was seen in. ASNs are classified as:

| Label | Condition |
|---|---|
| Shared backbone | Appears in all 3 LLMs |
| Partially shared | Appears in exactly 2 LLMs |
| LLM-specific | Appears in only 1 LLM |

#### (d) Hops to Exit Source ISP's AS
The source ASN is resolved from the probe's `src_addr`. The pipeline walks hops in order and counts consecutive hops whose ASN matches the source ASN. The first hop with a different ASN marks the ISP boundary. Traceroutes that never exit the source AS are flagged as anomalies and excluded from aggregated means (but counted and displayed separately).

### Step 5 — Export

`pipeline/viz/exporter.py` writes six JSON files to `dashboard/public/data/` for the React dashboard, and `pipeline/viz/plots/` renders standalone Plotly HTML files to `outputs/html/` as a backup.

---

## Project Structure

```
.
├── run_project.sh                    # Interactive menu: collect / run pipeline / start dashboard
├── requirements.txt                  # Python dependencies
├── docker-compose.yml                # Run a local RIPE Atlas probe (optional)
│
├── data/                             # Raw RIPE Atlas measurement data (committed)
│   ├── Urmil/
│   ├── aryan/
│   └── ashay/
│
├── pipeline/
│   ├── run.py                        # Main entry point — runs the full pipeline
│   ├── collect/
│   │   ├── RipeAtlasCollection.py    # Trigger US-state RIPE Atlas measurements
│   │   ├── InternationalCollection.py
│   │   └── LocalCollection.py        # Run traceroutes from local machine
│   ├── legacy/                       # Pre-pipeline analysis scripts (kept for reference)
│   │   ├── AnalyzeRipeData.py
│   │   ├── EnrichRipeData.py
│   │   ├── EnrichWithGeo.py
│   │   └── PlotData.py
│   └── viz/                          # Active analytics pipeline
│       ├── loader.py                 # Load + aggregate traceroute records
│       ├── resolver.py               # IP → geo + ASN resolution with disk cache
│       ├── analytics.py              # Compute the four metrics
│       ├── exporter.py               # Export analytics as JSON for the dashboard
│       └── plots/                    # Standalone Plotly HTML renderers (backup)
│
├── dashboard/                        # React analytics dashboard
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── WorldMap.tsx          # Interactive globe / flat map
│   │   │   ├── HopsPerISP.tsx        # Bar + box chart
│   │   │   ├── RTTHeatmap.tsx        # RTT bar chart by region / ISP
│   │   │   ├── CommonAS.tsx          # Shared backbone horizontal bar chart
│   │   │   └── HopsToExitAS.tsx      # ISP boundary bar chart
│   │   ├── hooks/useAnalyticsData.ts # Fetches JSON from public/data/
│   │   └── types/analytics.ts        # TypeScript interfaces
│   └── public/data/                  # JSON files written by pipeline/run.py
│
└── outputs/                          # Generated — not committed
    ├── geo_cache.json                # IP resolution cache (speeds up re-runs)
    └── html/                         # Standalone HTML chart backups
```

---

## Prerequisites

- **Python 3.8+** with `pip`
- **Node.js 18+** with `npm`
- **`dig`** command (standard on macOS / Linux) — used for Cymru DNS ASN fallback
- **RIPE Atlas API key** — only needed to collect new measurements
- **`latest.as-org2info.txt`** — optional CAIDA dataset for org-name enrichment. Download from [CAIDA](https://www.caida.org/catalog/datasets/as-organizations/) and place in the project root.

---

## Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd Following-the-Prompt

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Dashboard dependencies
cd dashboard && npm install && cd ..
```

For RIPE Atlas data collection, set your API key:
```bash
echo "RIPE_ATLAS_API_KEY=your-key-here" > .env
```

---

## Running the Pipeline

The pipeline loads all data from `data/`, resolves IPs (using the cache if available), computes all four metrics, and exports JSON to `dashboard/public/data/`:

```bash
python3 pipeline/run.py
```

Or use the interactive menu which wraps collection, pipeline, and dashboard in one place:

```bash
./run_project.sh
```

---

## Starting the Dashboard

```bash
cd dashboard
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

The dashboard reads from `dashboard/public/data/` — run `pipeline/run.py` first if these files don't exist or if new data has been added.

To build a production bundle:

```bash
cd dashboard
npm run build   # output goes to dashboard/dist/
```
