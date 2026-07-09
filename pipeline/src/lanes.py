import os
import osmnx as ox
import argparse

def infer_lanes(city_id: str):
    in_path = f"../data/{city_id}/cleaned.graphml"
    out_path = f"../data/{city_id}/lanes.graphml"
    
    G = ox.load_graphml(in_path)
    
    road_type_lanes = {
        'motorway': 3, 'trunk': 2, 'primary': 2,
        'secondary': 1, 'tertiary': 1, 'residential': 1
    }
    
    for u, v, key, data in G.edges(keys=True, data=True):
        lanes = data.get('lanes')
        if lanes:
            if isinstance(lanes, list):
                lanes = lanes[0]
            try:
                data['lanes_inferred'] = int(float(lanes))
                data['lane_confidence'] = 'high'
                continue
            except (ValueError, TypeError):
                pass
                
        hw = data.get('highway')
        if isinstance(hw, list):
            hw = hw[0]
        if hw in road_type_lanes:
            data['lanes_inferred'] = road_type_lanes[hw]
            data['lane_confidence'] = 'medium'
            continue
            
        width = data.get('width')
        if width:
            if isinstance(width, list):
                width = width[0]
            try:
                data['lanes_inferred'] = max(1, int(float(width) / 3.3))
                data['lane_confidence'] = 'low'
                continue
            except (ValueError, TypeError):
                pass
                
        data['lanes_inferred'] = 1
        data['lane_confidence'] = 'default'

    ox.save_graphml(G, out_path)
    print(f"Saved lanes graph to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    infer_lanes(args.city)
