import asyncio
import json
import math
import random
import websockets

async def mock_engine(websocket):
    print("Dashboard connected!")
    
    # Load graph data
    with open('data/piedmont/graph.json', 'r') as f:
        graph = json.load(f)
        
    nodes = {n['id']: n for n in graph['nodes']}
    edges = graph['edges']
    
    # Spawn a few fake agents on random edges
    agents = []
    for i in range(50):
        edge = random.choice(edges)
        u, v = nodes[edge['u']], nodes[edge['v']]
        agents.append({
            'id': i,
            'u': u,
            'v': v,
            'progress': random.random(),
            'speed': edge.get('speed_kph', 30) / 3.6, # m/s
            'type': random.randint(0, 4)
        })

    while True:
        # Move agents
        payload_agents = []
        for agent in agents:
            # simple mock movement
            agent['progress'] += 0.01
            if agent['progress'] >= 1.0:
                agent['progress'] = 0.0
                new_edge = random.choice(edges)
                agent['u'] = nodes[new_edge['u']]
                agent['v'] = nodes[new_edge['v']]
                
            u, v = agent['u'], agent['v']
            t = agent['progress']
            lat = u['lat'] + (v['lat'] - u['lat']) * t
            lon = u['lon'] + (v['lon'] - u['lon']) * t
            
            # heading
            dy = v['lat'] - u['lat']
            dx = v['lon'] - u['lon']
            heading = math.atan2(dy, dx)
            
            payload_agents.append({
                'id': agent['id'],
                'lat': lat,
                'lon': lon,
                'heading': heading,
                'type': agent['type']
            })
            
        # Broadcast
        try:
            await websocket.send(json.dumps(payload_agents))
            await asyncio.sleep(0.1) # 10 FPS
        except websockets.exceptions.ConnectionClosed:
            print("Dashboard disconnected.")
            break

async def main():
    print("Starting Mock Engine on ws://localhost:9002")
    async with websockets.serve(mock_engine, "localhost", 9002):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
