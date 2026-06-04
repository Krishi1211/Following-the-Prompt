import os
import plotly.graph_objects as go
import pandas as pd
from viz.plots.template import wrap_plotly_html

COLORS = {
    "Claude": "#D97706",
    "Gemini": "#2563EB",
    "ChatGPT": "#16A34A"
}

def plot_hops_to_exit_as(df, output_dir):
    """
    Plots grouped bar chart of the average number of hops to exit the source ASN for US probes.
    """
    if df.empty:
        print("  [!] DataFrame is empty, skipping hops_to_exit_as plot.")
        return

    # Filter to US probes only
    df_us = df[df["source_country"] == "US"].copy()
    if df_us.empty:
        print("  [!] No US probes found in data for hops_to_exit_as plot.")
        return

    # Filter out anomalous traceroutes (e.g. never exited) for average,
    # but we can display the anomaly count in annotations
    df_clean = df_us[~df_us["never_exited"]]
    anomalies = df_us[df_us["never_exited"]]

    # Select top 15 source ISPs in US to avoid crowding
    top_isps = df_clean["source_isp"].value_counts().head(15).index.tolist()
    df_filtered = df_clean[df_clean["source_isp"].isin(top_isps)]

    grouped = df_filtered.groupby(["source_isp", "llm"])["hops_to_exit"].agg(["mean", "std"]).reset_index()
    isp_order = df_filtered.groupby("source_isp")["hops_to_exit"].mean().sort_values(ascending=False).index.tolist()

    fig = go.Figure()

    for llm, color in COLORS.items():
        llm_group = grouped[grouped["llm"] == llm]
        
        x_vals = isp_order
        y_vals = []
        y_errors = []
        for isp in x_vals:
            row = llm_group[llm_group["source_isp"] == isp]
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
            name=f"{llm}",
            marker_color=color
        ))

    num_anoms = len(anomalies)
    anomaly_subtitle = f" ({num_anoms} never exited source AS)" if num_anoms > 0 else ""
    title_text = f"US Network Hops to Exit Source ISP AS{anomaly_subtitle}"

    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=20, color="white"),
            x=0.5,
            y=0.95
        ),
        xaxis=dict(
            title=dict(text="Source ISP Name", font=dict(color="white")),
            tickfont=dict(color="white"),
            tickangle=35,
            gridcolor="rgba(255, 255, 255, 0.05)"
        ),
        yaxis=dict(
            title=dict(text="Average Hops to Exit Source ASN", font=dict(color="white")),
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
        margin=dict(l=60, r=40, t=100, b=120),
        barmode="group"
    )

    # Convert to HTML snippet
    plotly_div = fig.to_html(include_plotlyjs="cdn", full_html=False)

    # Metrics for stats cards
    avg_hops = f"{df_clean['hops_to_exit'].mean():.2f}" if not df_clean.empty else "N/A"
    stats = {
        "US Probes Analyzed": len(df_us),
        "Avg Hops to Exit": avg_hops,
        "AS Anomalies": num_anoms,
        "Unique US ISPs": len(df_us["source_isp"].unique())
    }

    description = (
        "Measures the average number of network hops required to leave the source ISP's "
        "autonomous system (ASN) toward each LLM service. Higher values indicate deeper routing paths "
        "inside the originator's internal backbone before handoff. Anomalies show traces that never "
        "exited the source ASN."
    )

    full_html = wrap_plotly_html(
        div_content=plotly_div,
        title="First-Mile AS Exit Count",
        description=description,
        active_tab="hops_to_exit_as",
        stats=stats
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "hops_to_exit_as.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  Hops to exit source AS plot saved to {out_path}")
