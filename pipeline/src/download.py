import os
import yaml
import osmnx as ox
import argparse

def download_city(city_id: str):
    # Resolve cities.yaml relative to this file, not the working directory, so
    # the pipeline behaves identically however it is invoked. (A bare relative
    # "cities.yaml" only resolved when the CWD happened to be pipeline/.)
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "..", "cities.yaml")
    with open(config_path, "r") as f:
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
