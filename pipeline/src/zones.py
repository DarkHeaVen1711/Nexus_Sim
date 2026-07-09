import os
import osmnx as ox
import argparse

def tag_zones(city_id: str, grid_size: int = 10):
    in_path = f"../data/{city_id}/lanes.graphml"
    out_path = f"../data/{city_id}/zones.graphml"
    
    G = ox.load_graphml(in_path)
    
    lats = [float(data['y']) for n, data in G.nodes(data=True)]
    lons = [float(data['x']) for n, data in G.nodes(data=True)]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    for n, data in G.nodes(data=True):
        lat_idx = int((float(data['y']) - min_lat) / (max_lat - min_lat + 1e-9) * grid_size)
        lon_idx = int((float(data['x']) - min_lon) / (max_lon - min_lon + 1e-9) * grid_size)
        data['zone_id'] = lat_idx * grid_size + lon_idx
        
    ox.save_graphml(G, out_path)
    print(f"Saved zones graph to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    tag_zones(args.city)
