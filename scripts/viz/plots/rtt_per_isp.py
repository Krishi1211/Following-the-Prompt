import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from viz.plots.template import wrap_plotly_html

COLORS = {
    "Claude": "#D97706",
    "Gemini": "#2563EB",
    "ChatGPT": "#16A34A"
}

def plot_rtt_per_isp(df, output_dir):
    """
    Plots average total RTT as a global side-by-side comparison bar chart
    and regional latency heatmaps inside a tabbed dashboard view.
    """
    if df.empty:
        print("  [!] DataFrame is empty, skipping rtt_per_isp plot.")
        return

    # --- PART 1: GLOBAL ISP SIDE-BY-SIDE COMPARISON (BAR CHART) ---
    # Select top 20 starting ISPs globally
    top_isps = df["starting_isp"].value_counts().head(20).index.tolist()
    df_bar_filtered = df[df["starting_isp"].isin(top_isps)]

    grouped_bar = df_bar_filtered.groupby(["starting_isp", "llm"])["total_rtt_ms"].agg(["mean", "std"]).reset_index()
    # Sort ISPs by overall average RTT descending
    isp_order = df_bar_filtered.groupby("starting_isp")["total_rtt_ms"].mean().sort_values(ascending=False).index.tolist()

    fig_bar = go.Figure()

    for llm, color in COLORS.items():
        llm_group = grouped_bar[grouped_bar["llm"] == llm]
        
        x_vals = isp_order
        y_vals = []
        y_errors = []
        for isp in x_vals:
            row = llm_group[llm_group["starting_isp"] == isp]
            if not row.empty:
                y_vals.append(row.iloc[0]["mean"])
                y_errors.append(row.iloc[0]["std"] if not pd.isna(row.iloc[0]["std"]) else 0)
            else:
                y_vals.append(0)
                y_errors.append(0)

        fig_bar.add_trace(go.Bar(
            x=x_vals,
            y=y_vals,
            error_y=dict(type="data", array=y_errors, visible=True),
            name=llm,
            marker_color=color
        ))

    fig_bar.update_layout(
        title=dict(
            text="Global Average End-to-End Latency (RTT) per Starting ISP",
            font=dict(size=18, color="white"),
            x=0.5,
            y=0.95
        ),
        xaxis=dict(
            title=dict(text="Starting ISP/Organization", font=dict(color="white")),
            tickfont=dict(color="white"),
            tickangle=35,
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        yaxis=dict(
            title=dict(text="Latency / RTT (ms)", font=dict(color="white")),
            tickfont=dict(color="white"),
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            font=dict(color="white"),
            bgcolor="rgba(10, 10, 15, 0.6)",
            bordercolor="rgba(255, 255, 255, 0.2)"
        ),
        margin=dict(l=60, r=40, t=85, b=100),
        barmode="group"
    )

    # --- PART 2: REGIONAL LATENCY HEATMAPS ---
    # Focus on top 12 ISPs and top 25 regions to keep heatmap dense
    top_isps_heat = df["starting_isp"].value_counts().head(12).index.tolist()
    top_regions_heat = df["source_region"].value_counts().head(25).index.tolist()
    df_heat_filtered = df[df["starting_isp"].isin(top_isps_heat) & df["source_region"].isin(top_regions_heat)]

    fig_heat = go.Figure()
    llms = ["ChatGPT", "Gemini", "Claude"]
    trace_indices = {}
    counter = 0

    for llm in llms:
        df_llm = df_heat_filtered[df_heat_filtered["llm"] == llm]
        
        if not df_llm.empty:
            pivot = df_llm.pivot_table(
                index="source_region",
                columns="starting_isp",
                values="total_rtt_ms",
                aggfunc="mean"
            )
            pivot = pivot.reindex(index=top_regions_heat, columns=top_isps_heat)
        else:
            pivot = pd.DataFrame(index=top_regions_heat, columns=top_isps_heat)

        z_values = pivot.replace({np.nan: None}).values.tolist()

        fig_heat.add_trace(go.Heatmap(
            x=top_isps_heat,
            y=top_regions_heat,
            z=z_values,
            colorscale="Viridis",
            colorbar=dict(title=dict(text="RTT (ms)", font=dict(color="white")), tickfont=dict(color="white")),
            hoverongaps=False,
            visible=(llm == "ChatGPT")
        ))
        trace_indices[llm] = counter
        counter += 1

    # Dropdown menu to switch between LLM heatmaps in Heatmap tab
    buttons = []
    for llm in llms:
        visibility = [False] * len(llms)
        visibility[trace_indices[llm]] = True
        buttons.append(dict(
            args=[{"visible": visibility}, {"title.text": f"Regional End-to-End Latency to {llm}"}],
            label=f"{llm} Heatmap",
            method="update"
        ))

    fig_heat.update_layout(
        title=dict(
            text="Regional End-to-End Latency to ChatGPT",
            font=dict(size=18, color="white"),
            x=0.5,
            y=0.95
        ),
        xaxis=dict(
            title=dict(text="Starting ISP/Organization", font=dict(color="white")),
            tickfont=dict(color="white"),
            tickangle=35,
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        yaxis=dict(
            title=dict(text="Source Region (State/Country)", font=dict(color="white")),
            tickfont=dict(color="white"),
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=100, r=40, t=100, b=100),
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.5,
                y=1.12,
                xanchor="center",
                yanchor="top",
                font=dict(color="black")
            )
        ]
    )

    # Render Plotly snippets
    div_bar = fig_bar.to_html(include_plotlyjs="cdn", full_html=False)
    div_heat = fig_heat.to_html(include_plotlyjs="cdn", full_html=False)

    # Embed inside CSS/JS tabs structure
    tabbed_div_content = f"""
    <div class="tabs-container">
        <div class="tab-buttons">
            <button class="tab-btn active" data-view="bar" onclick="switchView('bar')">📊 Global ISP Comparison</button>
            <button class="tab-btn" data-view="heatmap" onclick="switchView('heatmap')">🗺️ Geographic Latency Heatmaps</button>
        </div>
        <div id="view-bar" class="tab-content active-content">
            {div_bar}
        </div>
        <div id="view-heatmap" class="tab-content">
            {div_heat}
        </div>
    </div>
    """

    # Stats cards
    avg_latency = f"{df['total_rtt_ms'].mean():.1f} ms" if not df.empty else "N/A"
    fastest_row = df.groupby("llm")["total_rtt_ms"].mean().idxmin() if not df.empty else "N/A"
    stats = {
        "Global Avg RTT": avg_latency,
        "Fastest Service": fastest_row,
        "ISPs Analyzed": len(df["starting_isp"].unique()),
        "Regions Represented": len(df["source_region"].unique())
    }

    description = (
        "Compares the propagation delay (latency) to reach the servers of each LLM service. "
        "The first view shows global average RTT comparisons for the starting ISPs side-by-side. "
        "The second view breaks down this latency geographically (by state or country) in heatmaps faceted per LLM."
    )

    full_html = wrap_plotly_html(
        div_content=tabbed_div_content,
        title="End-to-End Latency Suite",
        description=description,
        active_tab="rtt_per_isp",
        stats=stats
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "rtt_per_isp_region.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  RTT per ISP per region heatmap/bar chart saved to {out_path}")
