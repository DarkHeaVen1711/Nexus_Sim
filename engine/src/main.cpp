#include <iostream>
#include <string>
#include "graph/GraphLoader.h"
#include "agent/Simulation.h"

int main(int argc, char** argv) {
    std::string city = "chicago";
    if (argc >= 3) {
        std::string arg1(argv[1]);
        if (arg1 == "--city") {
            city = argv[2];
        }
    }
    
    std::cout << "NexusSim Engine Version 1.0\n";
    std::string filepath = "../data/" + city + "/graph.json";
    
    std::cout << "Loading graph for " << city << " from " << filepath << "...\n";
    auto g = nexussim::load_from_json(filepath);
    
    std::cout << "Node count: " << g.node_count() << "\n";
    std::cout << "Edge count: " << g.edge_count() << "\n";
    std::cout << "Total lanes: " << g.total_lanes() << "\n";
    std::cout << "Zone count: " << g.zone_count() << "\n";
    
    double chaos = 0.1;
    nexussim::Simulation sim(g, chaos);
    std::cout << "Spawning 500 agents...\n";
    sim.spawn_agents(500);

    std::cout << "Running 5-minute simulation loop (dt=0.1s)...\n";
    double dt = 0.1;
    int ticks = (5 * 60) / dt;
    for (int i = 0; i < ticks; ++i) {
        sim.tick(dt);
        if (i % 500 == 0) {
            std::cout << "Tick " << i << " / " << ticks << " - Active agents: " << sim.active_agents() << "\n";
        }
    }

    sim.log_journey_times("journey_times.csv");
    std::cout << "Saved journey times to journey_times.csv\n";
    
    return 0;
}
