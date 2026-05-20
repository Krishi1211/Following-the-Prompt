# AI Routing Project: Krishi's Regional Dataset

This directory contains the final, isolated network traceroute dataset collected by **Krishi** for the North / Mid-Atlantic region. 

## Data Collection Parameters
* **Region:** North / Mid-Atlantic (12 US States)
* **Probe Count:** 36 Active RIPE Atlas Probes
* **Methodology:** Active ICMP Traceroutes (Forward-Path Round Trip Time)

## File Mapping
Because RIPE Atlas saves output files based on internal Measurement IDs, use this index to find the raw JSON routing data for each specific AI target:

### OpenAI
* `ripe_results_172090307.json` ➔ **ChatGPT Web** (`chat.openai.com`)
* `ripe_results_172090357.json` ➔ **ChatGPT API** (`api.openai.com`)

### Google 
* `ripe_results_172090376.json` ➔ **Gemini Web** (`gemini.google.com`)
* `ripe_results_172090383.json` ➔ **Gemini API** (`generativelanguage.googleapis.com`)

### Anthropic
* `ripe_results_172090395.json` ➔ **Claude Web** (`claude.ai`)
* `ripe_results_172090402.json` ➔ **Claude API** (`api.anthropic.com`)

## Visualizations
* `montana_to_gemini_traceroute.png` ➔ A directed network graph detailing a 5-hop path from an isolated/remote probe (Montana) to a Google Edge datacenter.
