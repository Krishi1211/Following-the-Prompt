import os
import plotly.graph_objects as go
import pandas as pd
from viz.plots.template import wrap_plotly_html

COLOR_MAP = {
    "Shared backbone": "#EF4444",      # Red
    "Partially shared": "#F59E0B",     # Amber
    "LLM-specific": "#10B981"          # Emerald Green
}

def plot_common_as(df, output_dir):
    """
    Plots horizontal bar chart of the top 30 most common ASNs seen in traceroutes.
    Supports sorting toggles.
    """
    if df.empty:
        print("  [!] DataFrame is empty, skipping common_as plot.")
        return

    # Keep top 30 ASNs by total appearances
    df_sorted_appearances = df.sort_values(by="total_appearances", ascending=False).head(30)
    # Sort by commonality (all-3 first, then total appearances)
    df_sorted_commonality = df.sort_values(by=["llm_count", "total_appearances"], ascending=[False, False]).head(30)

    fig = go.Figure()
    
    # Store indices of traces for visibility switching
    trace_idx_app = []
    trace_idx_com = []
    
    counter = 0

    # 1. Build traces for Sort 1: Sorted by appearances
    for classification, color in COLOR_MAP.items():
        sub_df = df_sorted_appearances[df_sorted_appearances["classification"] == classification]
        if sub_df.empty:
            continue
            
        y_labels = [f"{row['asn']} ({row['org_name']})" for _, row in sub_df.iterrows()]
        line_dict = dict(width=2, color="white") if classification == "Shared backbone" else dict(width=0)
        
        fig.add_trace(go.Bar(
            y=y_labels,
            x=sub_df["total_appearances"],
            orientation="h",
            name=classification,
            marker_color=color,
            marker_line=line_dict,
            hoverinfo="text",
            hovertext=[
                f"ASN: {row['asn']}<br>"
                f"Org: {row['org_name']}<br>"
                f"Appears in: {row['llms']}<br>"
                f"Total appearances: {row['total_appearances']}<br>"
                f"Classification: {classification}"
                for _, row in sub_df.iterrows()
            ],
            visible=True
        ))
        trace_idx_app.append(counter)
        counter += 1

    # 2. Build traces for Sort 2: Sorted by commonality
    for classification, color in COLOR_MAP.items():
        sub_df = df_sorted_commonality[df_sorted_commonality["classification"] == classification]
        if sub_df.empty:
            continue
            
        y_labels = [f"{row['asn']} ({row['org_name']})" for _, row in sub_df.iterrows()]
        line_dict = dict(width=2, color="white") if classification == "Shared backbone" else dict(width=0)
        
        fig.add_trace(go.Bar(
            y=y_labels,
            x=sub_df["total_appearances"],
            orientation="h",
            name=classification,
            marker_color=color,
            marker_line=line_dict,
            hoverinfo="text",
            hovertext=[
                f"ASN: {row['asn']}<br>"
                f"Org: {row['org_name']}<br>"
                f"Appears in: {row['llms']}<br>"
                f"Total appearances: {row['total_appearances']}<br>"
                f"Classification: {classification}"
                for _, row in sub_df.iterrows()
            ],
            visible=False
        ))
        trace_idx_com.append(counter)
        counter += 1

    # Visibility masks
    def get_visibility_mask(sort_type):
        mask = [False] * counter
        indices = trace_idx_app if sort_type == "app" else trace_idx_com
        for idx in indices:
            mask[idx] = True
        return mask

    fig.update_layout(
        title=dict(
            text="Common ASes Shared Across LLMs",
            font=dict(size=20, color="white"),
            x=0.5,
            y=0.95
        ),
        xaxis=dict(
            title=dict(text="Total Appearances in Traceroutes", font=dict(color="white")),
            tickfont=dict(color="white"),
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        yaxis=dict(
            title=dict(text="Autonomous System (ASN)", font=dict(color="white")),
            tickfont=dict(color="white"),
            gridcolor="rgba(255, 255, 255, 0.05)",
            categoryorder="total ascending"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(
            font=dict(color="white"),
            bgcolor="rgba(10, 10, 15, 0.6)",
            bordercolor="rgba(255, 255, 255, 0.2)",
            x=0.8,
            y=0.15
        ),
        margin=dict(l=220, r=40, t=100, b=60),
        barmode="overlay",
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.5,
                y=1.12,
                xanchor="center",
                yanchor="top",
                buttons=[
                    dict(
                        args=[{"visible": get_visibility_mask("app")}, {"yaxis.categoryorder": "total ascending"}],
                        label="Sort by Total Appearances",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": get_visibility_mask("com")}, {"yaxis.categoryorder": "trace"}],
                        label="Sort by Shared Commonality",
                        method="update"
                    )
                ],
                font=dict(color="white"),
                bgcolor="rgba(30, 30, 45, 0.8)",
                bordercolor="rgba(255, 255, 255, 0.2)"
            )
        ]
    )

    # Convert to HTML snippet
    plotly_div = fig.to_html(include_plotlyjs="cdn", full_html=False)

    # Stats cards
    shared_backbones = len(df[df["llm_count"] == 3])
    partially_shared = len(df[df["llm_count"] == 2])
    most_common_org = df_sorted_appearances.iloc[0]["org_name"] if not df_sorted_appearances.empty else "N/A"
    
    stats = {
        "Total ASNs Tracked": len(df),
        "Shared Backbone ASes": shared_backbones,
        "Partially Shared": partially_shared,
        "Most Active Backbone": most_common_org
    }

    description = (
        "Identifies Autonomous Systems (ASNs) that are crossed by network packets on their way to "
        "multiple LLM endpoints. Red bars indicate backbone networks shared by all 3 LLM services, "
        "representing critical transit infrastructure."
    )

    full_html = wrap_plotly_html(
        div_content=plotly_div,
        title="Shared Backbone Infrastructure",
        description=description,
        active_tab="common_as",
        stats=stats
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "common_as.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  Common ASes shared backbone plot saved to {out_path}")
