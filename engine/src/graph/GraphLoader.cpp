#include "GraphLoader.h"
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace nexussim {

Graph GraphLoader::load_from_json(const std::string& filepath) {
    Graph g;
    std::ifstream file(filepath);
    if (!file.is_open()) {
        std::cerr << "Failed to open " << filepath << "\n";
        return g;
    }

    json j;
    file >> j;

    if (j.contains("nodes")) {
        for (const auto& node_json : j["nodes"]) {
            Node n;
            n.id = node_json["id"].get<int64_t>();
            n.lat = node_json["lat"].get<double>();
            n.lon = node_json["lon"].get<double>();
            n.zone_id = node_json["zone_id"].get<int32_t>();
            g.add_node(n);
        }
    }

    if (j.contains("edges")) {
        for (const auto& edge_json : j["edges"]) {
            Edge e;
            e.u = edge_json["u"].get<int64_t>();
            e.v = edge_json["v"].get<int64_t>();
            e.length_m = edge_json["length_m"].get<double>();
            e.lanes = edge_json["lanes"].get<int32_t>();
            g.add_edge(e);
        }
    }

    return g;
}

} // namespace nexussim
