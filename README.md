# AI Routing Infrastructure Analysis Project

This project performs network traceroute measurements to map the routing infrastructure and latency toward major AI endpoints (ChatGPT, Gemini, Claude) using both local probes and the global RIPE Atlas probe network.

## Prerequisites

1. **Python Environment**: Ensure you have Python 3.8+ installed.
2. **CAIDA Dataset**: Make sure you have the CAIDA AS-to-Org mapping dataset (`latest.as-org2info.txt`) in the root of the project directory.

## Setup Instructions

1. **Create and Activate a Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   The project requires a RIPE Atlas API key for global collection. This is securely stored in a `.env` file. If you haven't already, create a `.env` file in the root directory:
   ```env
   RIPE_ATLAS_API_KEY=your-api-key-here
   ```

## Execution Steps

Run all scripts from the **root directory** of the project so that file paths resolve correctly.

### 1. Data Collection

*   **RIPE Atlas Global Collection**
    This script triggers traceroute measurements across designated US states via RIPE Atlas probes and saves the results as JSON files.
    ```bash
    python scripts/ripe_atlas_collection.py
    ```

*   **Local Top Sites Collection**
    Runs local machine traceroutes to the list of top sites defined in `top_sites.json`.
    ```bash
    python scripts/collect_top_sites.py
    ```

*   **Custom Local Collection**
    Runs basic local traceroutes from your machine to the AI targets.
    ```bash
    python scripts/local_collection.py
    ```

### 2. Data Enrichment

Once the RIPE Atlas data is collected, you must enrich it by mapping IP addresses to their respective Autonomous System Numbers (ASNs) and Organizations using the CAIDA dataset and Cymru DNS API.

*   **Enrich RIPE Data**
    ```bash
    python scripts/enrich_ripe_data.py
    ```
    *(This script reads the raw `ripe_results_*.json` files and outputs `enriched_ripe_results_*.json`)*

### 3. Analysis & Visualization

*   **Analyze Performance Metrics**
    Calculates RTT (Round Trip Time), success rates, and hop counts across the collected data.
    ```bash
    python scripts/analyze_ripe_data.py
    ```

*   **Generate Traceroute Graphs**
    Generates visual network graphs (e.g., `montana_to_gemini_traceroute.png`) based on the collected traceroute hops.
    ```bash
    python scripts/generate_traceroute_graph.py
    ```

## Project Structure
*   `scripts/`: Contains all Python execution scripts.
*   `Krishi_Final_Dataset/`: Contains the final and enriched JSON traceroute datasets along with generated graphs.
*   `student_probes.json` / `top_sites.json`: Configuration targets for probe distribution and domain targets.
*   `.env`: Local environment file (Ignored by Git) to securely store API keys.
