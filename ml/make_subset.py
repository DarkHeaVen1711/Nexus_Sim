import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from env.graph_loader import load_graph_json

g = load_graph_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'chicago', 'graph.json'))
zone_intersections = {}
for i in g['intersections']:
    z = g['zone_map'][i]
    zone_intersections.setdefault(z, []).append(i)

subset_zones = sorted(zone_intersections.keys())[:5]
subset_ids = set()
for z in subset_zones:
    subset_ids.update(zone_intersections[z])

with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'chicago', 'graph.json')) as f:
    raw = json.load(f)

filtered_nodes = [n for n in raw['nodes'] if n['id'] in subset_ids]
filtered_edges = [e for e in raw['edges'] if e['u'] in subset_ids and e['v'] in subset_ids]

out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'chicago_subset')
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, 'graph.json'), 'w') as f:
    json.dump({'nodes': filtered_nodes, 'edges': filtered_edges}, f)

g2 = load_graph_json(os.path.join(out_dir, 'graph.json'))
print('Chicago subset:', g2['num_intersections'], 'intersections,', len(g2['zones']), 'zones')
