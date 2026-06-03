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

def plot_hops_per_isp(df, output_dir):
    """
    Plots average hop count per starting ISP per LLM.
    Supports toggling between bar chart and box plot, and filtering by country.
    """
    if df.empty:
        print("  [!] DataFrame is empty, skipping hops_per_isp plot.")
        return

    # Select the top 25 starting ISPs by volume
    top_isps = df["starting_isp"].value_counts().head(25).index.tolist()
    df_filtered = df[df["starting_isp"].isin(top_isps)].copy()

    countries_filter = {
        "All": df_filtered,
        "US": df_filtered[df_filtered["country"] == "US"],
        "Intl": df_filtered[df_filtered["country"] != "US"]
    }

    fig = go.Figure()
    
    trace_groups = {}
    trace_counter = 0

    for name, data in countries_filter.items():
        trace_groups[name] = {"bar": [], "box": []}
        
        # Calculate stats for the bar chart
        if not data.empty:
            grouped = data.groupby(["starting_isp", "llm"])["hop_count"].agg(["mean", "std"]).reset_index()
            isp_order = data.groupby("starting_isp")["hop_count"].mean().sort_values(ascending=False).index.tolist()
        else:
            grouped = pd.DataFrame(columns=["starting_isp", "llm", "mean", "std"])
            isp_order = []

        # 1. Add Bar traces
        for llm, color in COLORS.items():
            llm_group = grouped[grouped["llm"] == llm]
            
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

            fig.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                error_y=dict(type="data", array=y_errors, visible=True),
                name=llm,
                marker_color=color,
                visible=(name == "All") # Only "All" bar charts visible initially
            ))
            trace_groups[name]["bar"].append(trace_counter)
            trace_counter += 1

        # 2. Add Box traces
        for llm, color in COLORS.items():
            llm_raw = data[data["llm"] == llm]
            
            fig.add_trace(go.Box(
                x=llm_raw["starting_isp"],
                y=llm_raw["hop_count"],
                name=llm,
                marker_color=color,
                boxmean="sd",
                visible=False # Box plots hidden initially
            ))
            trace_groups[name]["box"].append(trace_counter)
            trace_counter += 1

    # Create buttons for toggling Chart Type (Bar vs Box) and Dropdowns for Country Filter
    def get_visibility_mask(active_country, active_type):
        mask = [False] * trace_counter
        for t_idx in trace_groups[active_country][active_type]:
            mask[t_idx] = True
        return mask

    # Layout updates
    fig.update_layout(
        title=dict(
            text="Network Hop Count per Starting ISP",
            font=dict(size=20, color="white"),
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
            title=dict(text="Hop Count", font=dict(color="white")),
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
        margin=dict(l=60, r=40, t=100, b=100),
        barmode="group",
        updatemenus=[
            # Dropdown for Country Filter
            dict(
                buttons=[
                    dict(
                        args=[{"visible": get_visibility_mask("All", "bar")}, 
                              {"title.text": "Network Hop Count per Starting ISP (All Regions)"}],
                        label="All Regions",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": get_visibility_mask("US", "bar")}, 
                              {"title.text": "Network Hop Count per Starting ISP (US Probes Only)"}],
                        label="US Probes Only",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": get_visibility_mask("Intl", "bar")}, 
                              {"title.text": "Network Hop Count per Starting ISP (International Probes Only)"}],
                        label="International Probes Only",
                        method="update"
                    )
                ],
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.15,
                y=1.12,
                xanchor="left",
                yanchor="top",
                font=dict(color="black")
            ),
            # Toggle for Chart Type (Bar vs Box)
            dict(
                buttons=[
                    dict(
                        args=[{"visible": get_visibility_mask("All", "bar")}],
                        label="Grouped Bar (Mean ± SD)",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": get_visibility_mask("All", "box")}],
                        label="Box Plot (Full Distribution)",
                        method="update"
                    )
                ],
                type="buttons",
                direction="right",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.85,
                y=1.12,
                xanchor="right",
                yanchor="top",
                font=dict(color="white"),
                bgcolor="rgba(30, 30, 45, 0.8)",
                bordercolor="rgba(255, 255, 255, 0.2)"
            )
        ]
    )

    # Convert to HTML snippet
    plotly_div = fig.to_html(include_plotlyjs="cdn", full_html=False)

    # Stats cards
    stats = {
        "Avg Route Hops": f"{df_filtered['hop_count'].mean():.1f}",
        "Max Hops Tracked": df_filtered["hop_count"].max(),
        "Top ISPs Displayed": len(top_isps),
        "Total Paths Sampled": len(df)
    }

    description = (
        "Measures the network length (number of hop points) from starting client ISPs to each LLM endpoint. "
        "Fewer hops generally indicate better routing directness. You can toggle between grouped average "
        "bars and full distribution box plots using the controls on the right, or filter regions using the dropdown on the left."
    )

    full_html = wrap_plotly_html(
        div_content=plotly_div,
        title="Network Hop Counts",
        description=description,
        active_tab="hops_per_isp",
        stats=stats
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "hops_per_isp.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  Hops per ISP plot saved to {out_path}")
