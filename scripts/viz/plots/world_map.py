import os
import plotly.graph_objects as go
from viz.resolver import is_private
from viz.plots.template import wrap_plotly_html

COLORS = {
    "Claude": "#D97706",   # Amber
    "Gemini": "#2563EB",   # Blue
    "ChatGPT": "#16A34A"   # Green
}

def plot_world_map(records, geo_cache, output_dir):
    """
    Renders an interactive orthographic/flat world map showing traceroute paths
    wrapped in a premium dashboard layout.
    """
    fig = go.Figure()

    # llm -> { "lats": [], "lons": [], "text": [] }
    llm_paths = {llm: {"lats": [], "lons": [], "text": []} for llm in COLORS}
    resolved_ips_in_map = set()

    for r in records:
        llm = r["llm"]
        if llm not in llm_paths:
            continue
            
        path_lats = []
        path_lons = []
        path_text = []
        
        # Always add the probe starting IP location if public
        src_geo = geo_cache.get(r["src_addr"], {})
        if src_geo and not src_geo.get("private") and src_geo.get("lat") is not None:
            path_lats.append(src_geo["lat"])
            path_lons.append(src_geo["lon"])
            path_text.append(
                f"Source Probe IP: {r['src_addr']}<br>"
                f"Org: {src_geo.get('org_name')}<br>"
                f"Region: {r['region']}, {r['country']}"
            )
            resolved_ips_in_map.add(r["src_addr"])
            
        # Add responding hops
        for hop in r["hops"]:
            hop_num = hop["hop"]
            # Find first responsive public IP
            valid_ip = None
            for ip in hop.get("ips", []):
                if not is_private(ip):
                    valid_ip = ip
                    break
                    
            if valid_ip:
                geo = geo_cache.get(valid_ip, {})
                if geo and geo.get("lat") is not None:
                    path_lats.append(geo["lat"])
                    path_lons.append(geo["lon"])
                    path_text.append(
                        f"IP: {valid_ip}<br>"
                        f"Org: {geo.get('org_name')}<br>"
                        f"ASN: {geo.get('asn')}<br>"
                        f"City: {geo.get('city')}, {geo.get('country')}<br>"
                        f"Hop #: {hop_num}<br>"
                        f"Seen in: {r.get('num_runs', 1)} runs"
                    )
                    resolved_ips_in_map.add(valid_ip)

        if len(path_lats) > 1:
            # Add this path to the LLM's combined path lists, separated by None
            llm_paths[llm]["lats"].extend(path_lats + [None])
            llm_paths[llm]["lons"].extend(path_lons + [None])
            llm_paths[llm]["text"].extend(path_text + [None])

    # Add traces to the figure
    for llm, color in COLORS.items():
        paths = llm_paths[llm]
        if not paths["lats"]:
            continue
            
        fig.add_trace(go.Scattergeo(
            lon=paths["lons"],
            lat=paths["lats"],
            mode="lines+markers",
            name=llm,
            line=dict(width=1.5, color=color),
            marker=dict(size=4, color=color, opacity=0.8),
            hoverinfo="text",
            hovertext=paths["text"],
            opacity=0.7
        ))

    # Add projection controls to the layout
    fig.update_layout(
        title=dict(
            text="Interactive LLM Routing Traceroute Map",
            font=dict(size=20, color="white"),
            x=0.5,
            y=0.95
        ),
        showlegend=True,
        legend=dict(
            font=dict(color="white"),
            bgcolor="rgba(10, 10, 15, 0.6)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            x=0.05,
            y=0.15
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=65, b=0),
        geo=dict(
            projection_type="orthographic", # default globe
            showland=True,
            landcolor="rgb(25, 25, 30)",
            oceancolor="rgb(10, 10, 15)",
            showocean=True,
            showlakes=True,
            lakecolor="rgb(10, 10, 15)",
            showcountries=True,
            countrycolor="rgb(60, 60, 65)",
            bgcolor="rgba(0,0,0,0)",
            resolution=50
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.5,
                y=0.05,
                xanchor="center",
                yanchor="bottom",
                buttons=[
                    dict(
                        args=["geo.projection.type", "orthographic"],
                        label="Globe (3D)",
                        method="relayout"
                    ),
                    dict(
                        args=["geo.projection.type", "natural earth"],
                        label="Flat (2D)",
                        method="relayout"
                    )
                ],
                font=dict(color="white"),
                bgcolor="rgba(30, 30, 40, 0.8)",
                bordercolor="rgba(255, 255, 255, 0.3)"
            )
        ]
    )

    # Convert to HTML snippet
    plotly_div = fig.to_html(include_plotlyjs="cdn", full_html=False)

    # Stats cards
    stats = {
        "Total Paths Traced": len(records),
        "Resolved IPs on Map": len(resolved_ips_in_map),
        "LLMs Tracked": len(set(r["llm"] for r in records)),
        "Active Day Runs": 4
    }

    description = (
        "Visualizes network routing paths from RIPE Atlas probes to the API endpoints of Claude, Gemini, and ChatGPT. "
        "Lines show the geographical trajectory from node to node, omitting private or unresponsive hops. "
        "Select the 2D/3D toggle below the map to switch projection formats."
    )

    full_html = wrap_plotly_html(
        div_content=plotly_div,
        title="Global Route Map",
        description=description,
        active_tab="world_map",
        stats=stats
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "world_map.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  World map saved to {out_path}")
