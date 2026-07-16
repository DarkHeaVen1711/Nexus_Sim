import os
import yaml
import osmnx as ox
import argparse

def download_city(city_id: str):
    with open("cities.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    if city_id not in config:
        raise ValueError(f"City {city_id} not found in cities.yaml")
        
    query = config[city_id]["query"]
    print(f"Downloading data for {query}...")
    
    # Keep highway tags on nodes so we can identify traffic signals
    if 'highway' not in ox.settings.useful_tags_node:
        ox.settings.useful_tags_node.append('highway')
        
    # Use simplify=False so clean.py handles it
    G = ox.graph_from_place(query, network_type="drive", simplify=False)
    
    out_dir = f"../data/{city_id}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "raw.graphml")
    
    ox.save_graphml(G, out_path)
    print(f"Saved raw graph to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    download_city(args.city)
