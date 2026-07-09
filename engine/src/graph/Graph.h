#pragma once
#include <vector>
#include <unordered_map>
#include <cstdint>

namespace nexussim {

struct Node {
    int64_t id;
    double lat;
    double lon;
    int32_t zone_id;
};

struct Edge {
    int64_t u;
    int64_t v;
    double length_m;
    int32_t lanes;
};

class Graph {
public:
    void add_node(const Node& node) {
        nodes_[node.id] = node;
    }

    void add_edge(const Edge& edge) {
        edges_.push_back(edge);
        adj_list_[edge.u].push_back(edge);
    }

    const Node* get_node(int64_t id) const {
        auto it = nodes_.find(id);
        return it != nodes_.end() ? &it->second : nullptr;
    }

    const std::vector<Edge>& get_edges_from(int64_t u) const {
        static const std::vector<Edge> empty;
        auto it = adj_list_.find(u);
        return it != adj_list_.end() ? it->second : empty;
    }

    size_t node_count() const { return nodes_.size(); }
    size_t edge_count() const { return edges_.size(); }
    
    // For summary stats
    int32_t total_lanes() const {
        int32_t total = 0;
        for (const auto& e : edges_) total += e.lanes;
        return total;
    }
    
    size_t zone_count() const {
        std::unordered_map<int32_t, bool> zones;
        for (const auto& pair : nodes_) zones[pair.second.zone_id] = true;
        return zones.size();
    }

private:
    std::unordered_map<int64_t, Node> nodes_;
    std::vector<Edge> edges_;
    std::unordered_map<int64_t, std::vector<Edge>> adj_list_;
};

} // namespace nexussim
