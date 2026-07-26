#include <iostream>
#include <string>
#include <cstdlib>
#include "graph/GraphLoader.h"
#include "agent/Simulation.h"
#include "network/WebSocketServer.h"

int main(int argc, char** argv) {
    std::string city = "chicago";
    size_t agent_count = 500;
    int duration_min = 5;

    for (int i = 1; i < argc; i += 2) {
        std::string arg(argv[i]);
        if (arg == "--city" && i + 1 < argc)
            city = argv[i + 1];
        else if (arg == "--agents" && i + 1 < argc)
            agent_count = std::stoul(argv[i + 1]);
        else if (arg == "--duration" && i + 1 < argc)
            duration_min = std::atoi(argv[i + 1]);
    }

    std::cout << "NexusSim Engine v3.0\n";
    std::string filepath = "data/" + city + "/graph.json";
    std::ifstream test(filepath);
    if (!test.good()) {
        filepath = "../data/" + city + "/graph.json";
    }

    std::cout << "Loading graph for " << city << "...\n";
    auto g = nexussim::load_from_json(filepath);

    std::cout << "Nodes: " << g.node_count()
              << " Edges: " << g.edge_count()
              << " Lanes: " << g.total_lanes()
              << " Zones: " << g.zone_count() << "\n";

    double chaos = 0.1;
    nexussim::Simulation sim(g, chaos);
    std::cout << "Spawning " << agent_count << " agents...\n";
    sim.spawn_agents(agent_count);

    double dt = 0.1;
    int ticks = static_cast<int>((duration_min * 60.0) / dt);
    std::cout << "Running " << duration_min << "-min sim ("
              << ticks << " ticks, dt=" << dt << "s)...\n";

    nexussim::network::WebSocketServer ws_server(9001);
    ws_server.start();
    std::cout << "WebSocket Server starting on port 9001...\n";

    for (int i = 0; i < ticks; ++i) {
        sim.tick(dt);
        sim.broadcast_state(&ws_server);
        
        if (i % 500 == 0)
            std::cout << "Tick " << i << "/" << ticks
                      << " active=" << sim.active_agents() << "\n";

        // Pace at ~60fps so dashboard can visualize in real-time
#ifdef _WIN32
        Sleep(16);
#else
        std::this_thread::sleep_for(std::chrono::milliseconds(16));
#endif
    }

    sim.log_journey_times("journey_times.csv");
    std::cout << "Avg tick: " << sim.avg_tick_ms() << "ms"
              << " p95: " << sim.p95_tick_ms() << "ms\n";
    std::cout << "Saved journey_times.csv\n";
    return 0;
}
