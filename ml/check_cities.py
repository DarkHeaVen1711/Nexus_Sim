import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from env.graph_loader import load_graph_json

for c in ['chicago', 'piedmont']:
    g = load_graph_json(os.path.join(os.path.dirname(__file__), '..', 'data', c, 'graph.json'))
    n = g['num_intersections']
    z = len(g['zones'])
    print(f'{c}: {n} intersections, {z} zones, obs_dim=11')
