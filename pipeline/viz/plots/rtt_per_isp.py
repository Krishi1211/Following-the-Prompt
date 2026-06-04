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

    llms = ["ChatGPT", "Gemini", "Claude"]
    heatmaps_html = []
    
    # Load plotly script once
    plotly_script_included = False

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

        fig_single = go.Figure(go.Heatmap(
            x=top_isps_heat,
            y=top_regions_heat,
            z=z_values,
            colorscale="Viridis",
            colorbar=dict(title=dict(text="RTT (ms)", font=dict(color="white")), tickfont=dict(color="white")),
            hoverongaps=False
        ))

        fig_single.update_layout(
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
            margin=dict(l=100, r=40, t=20, b=100)
        )

        include_js = "cdn" if not plotly_script_included else False
        plotly_script_included = True

        div_str = fig_single.to_html(include_plotlyjs=include_js, full_html=False)
        is_visible_style = "" if llm == "ChatGPT" else "display: none;"
        heatmaps_html.append(f"""
        <div id="heatmap-{llm}" class="heatmap-div" style="{is_visible_style}">
            {div_str}
        </div>
        """)

    # Render Plotly snippets
    div_bar = fig_bar.to_html(include_plotlyjs="cdn", full_html=False)

    heatmap_controls = """
    <div class="heatmap-controls-container" style="display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem;">
        <h3 id="heatmap-title" style="font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 1.3rem; color: #ffffff;">Regional End-to-End Latency to ChatGPT</h3>
        
        <div class="dropdown-wrapper">
            <label for="heatmap-llm-select" class="dropdown-label">Select Target Service:</label>
            <select id="heatmap-llm-select" class="custom-select" onchange="switchHeatmap(this.value)">
                <option value="ChatGPT">ChatGPT (api.openai.com)</option>
                <option value="Gemini">Gemini (generativelanguage.googleapis.com)</option>
                <option value="Claude">Claude (api.anthropic.com)</option>
            </select>
        </div>
    </div>
    
    <style>
        .dropdown-wrapper {
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 0.6rem 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            width: fit-content;
        }
        .dropdown-label {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
        }
        .custom-select {
            background: #111118;
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            padding: 0.4rem 2rem 0.4rem 0.8rem;
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            cursor: pointer;
            outline: none;
            transition: all 0.2s ease;
            appearance: none;
            background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
            background-repeat: no-repeat;
            background-position: right 0.6rem center;
            background-size: 0.9rem;
        }
        .custom-select:hover {
            border-color: var(--accent-color);
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
        }
    </style>
    
    <script>
        function switchHeatmap(llm) {
            document.querySelectorAll('.heatmap-div').forEach(el => el.style.display = 'none');
            const selectedDiv = document.getElementById('heatmap-' + llm);
            if (selectedDiv) {
                selectedDiv.style.display = 'block';
            }
            const titleEl = document.getElementById('heatmap-title');
            if (titleEl) {
                titleEl.innerText = 'Regional End-to-End Latency to ' + llm;
            }
            window.dispatchEvent(new Event('resize'));
        }
    </script>
    """

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
            {heatmap_controls}
            {"".join(heatmaps_html)}
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
