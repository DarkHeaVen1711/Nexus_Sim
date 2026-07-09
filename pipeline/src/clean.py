import os
import osmnx as ox
import argparse

def clean_graph(city_id: str):
    in_path = f"../data/{city_id}/raw.graphml"
    out_path = f"../data/{city_id}/cleaned.graphml"
    
    print(f"Loading raw graph from {in_path}...")
    G = ox.load_graphml(in_path)
    
    nodes_before = len(G.nodes)
    print(f"Nodes before cleaning: {nodes_before}")
    
    import networkx as nx
    G = ox.simplify_graph(G)
    largest_cc = max(nx.strongly_connected_components(G), key=len)
    G = G.subgraph(largest_cc).copy()
    
    nodes_after = len(G.nodes)
    print(f"Nodes after cleaning: {nodes_after}")
    
    ox.save_graphml(G, out_path)
    print(f"Saved cleaned graph to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    clean_graph(args.city)
