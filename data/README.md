# AI Routing Project: Dataset

This directory contains traceroute datasets collected from the North / Mid-Atlantic region via RIPE Atlas, along with generated visualizations.

## Collection Parameters

- **Region:** North / Mid-Atlantic (12 US States)
- **Probe Count:** 36 Active RIPE Atlas Probes
- **Method:** Active ICMP Traceroutes

## File Index

Raw RIPE Atlas results are named by measurement ID. Use this index to find data for each AI target:

### OpenAI
- `ripe_results_172090307.json` — ChatGPT Web (`chat.openai.com`)
- `ripe_results_172090357.json` — ChatGPT API (`api.openai.com`)

### Google
- `ripe_results_172090376.json` — Gemini Web (`gemini.google.com`)
- `ripe_results_172090383.json` — Gemini API (`generativelanguage.googleapis.com`)

### Anthropic
- `ripe_results_172090395.json` — Claude Web (`claude.ai`)
- `ripe_results_172090402.json` — Claude API (`api.anthropic.com`)

## Enriched Files

The `enriched_ripe_results_*.json` files add `asn` and `org_name` fields to each hop packet, derived from the CAIDA AS-to-Org dataset and Cymru DNS lookups.

## Visualizations

- `montana_to_gemini_traceroute.png` — Directed network graph of the 5-hop path from a Montana probe to Google's Gemini edge.
