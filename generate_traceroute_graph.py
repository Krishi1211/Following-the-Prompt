import matplotlib.pyplot as plt
import networkx as nx

# Create a directed graph
G = nx.DiGraph()

# Add nodes with their labels
G.add_node("Probe", label="RIPE Probe\n(Montana)\n[Local]")
G.add_node("Router1", label="ISP Edge Router\n206.127.64.129\n[Local]")
G.add_node("Router2", label="Regional Gateway\n206.127.109.180\n[Local]")
G.add_node("Zayo", label="Tier 1 Fiber Backbone\n209.133.55.242\n[Transit]")
G.add_node("GoogleEdge", label="Google Edge\n142.250.175.226\n[Transit]")
G.add_node("Gemini", label="Gemini Endpoint\n142.251.156.2\n[Target]")

# Add edges with latency weights
G.add_edge("Probe", "Router1", weight="1.4ms")
G.add_edge("Router1", "Router2", weight="0.3ms")
G.add_edge("Router2", "Zayo", weight="15.5ms")
G.add_edge("Zayo", "GoogleEdge", weight="15.6ms")
G.add_edge("GoogleEdge", "Gemini", weight="15.5ms")

# Setup plot
plt.figure(figsize=(14, 4))

# Define fixed positions for a straight line layout
pos = {
    "Probe": (0, 0),
    "Router1": (1, 0),
    "Router2": (2, 0),
    "Zayo": (3, 0),
    "GoogleEdge": (4, 0),
    "Gemini": (5, 0)
}

# Define colors based on node type
color_map = []
for node in G:
    if node == "Probe" or "Router" in node:
        color_map.append('#0f9d58') # Green for local
    elif node == "Gemini":
        color_map.append('#4285F4') # Blue for target
    else:
        color_map.append('#f4b400') # Yellow for transit

# Draw nodes
nx.draw_networkx_nodes(G, pos, node_color=color_map, node_size=3000, edgecolors='white', linewidths=2)

# Draw labels
labels = nx.get_node_attributes(G, 'label')
nx.draw_networkx_labels(G, pos, labels, font_size=9, font_color='black', font_weight='bold')

# Draw edges
nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, width=2)

# Draw edge labels (latencies)
edge_labels = nx.get_edge_attributes(G, 'weight')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10, font_color='red')

plt.title("Traceroute Hops: Montana to Gemini (gemini.google.com)", fontsize=14, fontweight='bold', pad=20)
plt.axis('off')

# Save to PNG
plt.tight_layout()
plt.savefig('montana_to_gemini_traceroute.png', dpi=300, bbox_inches='tight')
print("Image saved as montana_to_gemini_traceroute.png")
