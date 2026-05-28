import matplotlib.pyplot as plt
import networkx as nx

# ─── Configuration ────────────────────────────────────────────────────────────

OUTPUT_PATH = "data/montana_to_gemini_traceroute.png"

# Node definitions: id → (label, hex color)
NODES = {
    "Probe":       ("RIPE Probe\n(Montana)\n[Local]",                   "#0f9d58"),
    "Router1":     ("ISP Edge Router\n206.127.64.129\n[Local]",         "#0f9d58"),
    "Router2":     ("Regional Gateway\n206.127.109.180\n[Local]",       "#0f9d58"),
    "Zayo":        ("Tier 1 Backbone\n209.133.55.242\n[Transit]",       "#f4b400"),
    "GoogleEdge":  ("Google Edge\n142.250.175.226\n[Transit]",          "#f4b400"),
    "Gemini":      ("Gemini Endpoint\n142.251.156.2\n[Target]",         "#4285F4"),
}

# Edge definitions: (source, destination, latency label)
EDGES = [
    ("Probe",      "Router1",    "1.4ms"),
    ("Router1",    "Router2",    "0.3ms"),
    ("Router2",    "Zayo",       "15.5ms"),
    ("Zayo",       "GoogleEdge", "15.6ms"),
    ("GoogleEdge", "Gemini",     "15.5ms"),
]

# Fixed left-to-right positions
NODE_POSITIONS = {
    "Probe": (0, 0), "Router1": (1, 0), "Router2": (2, 0),
    "Zayo":  (3, 0), "GoogleEdge": (4, 0), "Gemini": (5, 0),
}

# ─── Graph Construction ───────────────────────────────────────────────────────

def buildGraph():
    G = nx.DiGraph()
    for nodeId, (label, _) in NODES.items():
        G.add_node(nodeId, label=label)
    for src, dst, latency in EDGES:
        G.add_edge(src, dst, weight=latency)
    return G

# ─── Drawing ──────────────────────────────────────────────────────────────────

def drawGraph(G):
    colorMap   = [NODES[n][1] for n in G]
    nodeLabels = nx.get_node_attributes(G, "label")
    edgeLabels = nx.get_edge_attributes(G, "weight")

    nx.draw_networkx_nodes(G, NODE_POSITIONS,
                           node_color=colorMap, node_size=3000,
                           edgecolors="white", linewidths=2)
    nx.draw_networkx_labels(G, NODE_POSITIONS, nodeLabels,
                            font_size=9, font_color="black", font_weight="bold")
    nx.draw_networkx_edges(G, NODE_POSITIONS,
                           edge_color="gray", arrows=True, arrowsize=20, width=2)
    nx.draw_networkx_edge_labels(G, NODE_POSITIONS, edgeLabels,
                                 font_size=10, font_color="red")

# ─── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    plt.figure(figsize=(14, 4))
    drawGraph(buildGraph())
    plt.title("Traceroute Hops: Montana → Gemini (gemini.google.com)",
              fontsize=14, fontweight="bold", pad=20)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight")
    print(f"Graph saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
