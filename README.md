# AI Routing Infrastructure Analysis Project

This project performs network traceroute measurements to map the routing infrastructure and latency toward major AI endpoints (ChatGPT, Gemini, Claude) using both local probes and the global RIPE Atlas probe network.

## Prerequisites

- Python 3.8+
- `dig` command available (standard on macOS/Linux)
- CAIDA AS-to-Org mapping dataset (`latest.as-org2info.txt`) in the project root — required only for enrichment

## Quick Start

```bash
./run_project.sh
```

This script creates a virtual environment, installs all dependencies, and presents an interactive menu.

## Manual Setup

1. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your RIPE Atlas API key**
   ```bash
   echo "RIPE_ATLAS_API_KEY=your-api-key-here" > .env
   ```

## Pipeline

All scripts must be run from the **project root** directory.

### 1. Data Collection

**RIPE Atlas global collection** — triggers traceroutes across US states via RIPE Atlas probes and saves raw JSON results to `data/`:
```bash
python3 scripts/RipeAtlasCollection.py
```

**Local collection** — runs traceroutes from your machine to the AI targets and saves results to `data/`:
```bash
python3 scripts/LocalCollection.py
```

### 2. Data Enrichment

Maps IP addresses to ASNs and organizations using the CAIDA dataset and Cymru DNS. Reads `data/ripe_results_*.json` and writes `data/enriched_ripe_results_*.json`:
```bash
python3 scripts/EnrichRipeData.py
```

> Requires `latest.as-org2info.txt` in the project root. Download from [CAIDA](https://www.caida.org/catalog/datasets/as-organizations/).

### 3. Analysis & Visualization

**Analyze performance metrics** — calculates RTT, success rates, and hop counts:
```bash
python3 scripts/AnalyzeRipeData.py
```

**Generate traceroute graph** — produces `data/montana_to_gemini_traceroute.png`:
```bash
python3 scripts/GenerateTracerouteGraph.py
```

## Project Structure

```
.
├── data/                              # Collected datasets and generated outputs
│   ├── ripe_results_*.json            # Raw RIPE Atlas traceroute results
│   ├── enriched_ripe_results_*.json   # ASN/org-enriched results
│   ├── ripe_measurement_mapping_*.json
│   └── montana_to_gemini_traceroute.png
├── scripts/
│   ├── RipeAtlasCollection.py         # Trigger RIPE Atlas measurements
│   ├── LocalCollection.py             # Run local traceroutes
│   ├── EnrichRipeData.py              # Enrich with CAIDA + Cymru ASN data
│   ├── AnalyzeRipeData.py             # Compute RTT, success rate, hop stats
│   └── GenerateTracerouteGraph.py     # Generate network hop visualizations
├── requirements.txt
├── run_project.sh                     # Interactive setup and runner
└── docker-compose.yml                 # Optional: run a local RIPE Atlas probe
```
