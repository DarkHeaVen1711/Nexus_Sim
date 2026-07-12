#include <iostream>
#include <string>
#include "graph/GraphLoader.h"

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
    auto g = nexussim::GraphLoader::load_from_json(filepath);
    
    std::cout << "Node count: " << g.node_count() << "\n";
    std::cout << "Edge count: " << g.edge_count() << "\n";
    std::cout << "Total lanes: " << g.total_lanes() << "\n";
    std::cout << "Zone count: " << g.zone_count() << "\n";
    
    return 0;
}
