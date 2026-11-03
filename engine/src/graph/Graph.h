#pragma once
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <cstdint>
#include <cstddef>
#include <string>

namespace nexussim {

struct Node {
    int64_t id;
    double lat;
    double lon;
    double x; // Precomputed pseudo-meters for fast heuristic
    double y; // Precomputed pseudo-meters for fast heuristic
    int32_t zone_id;
    bool is_signal = false;
};

struct Edge {
    int64_t u;
    int64_t v;
    double length_m;
    int32_t lanes;
};

struct Point {
    double x;
    double y;
};

struct PolygonHazard {
    int64_t id;
    std::vector<Point> vertices;
    double penalty = 1e9; // default infinite penalty (road closure)
    std::string description;

    bool contains_point(double px, double py) const {
        if (vertices.size() < 3) return false;
        bool inside = false;
        size_t n = vertices.size();
        for (size_t i = 0, j = n - 1; i < n; j = i++) {
            double xi = vertices[i].x, yi = vertices[i].y;
            double xj = vertices[j].x, yj = vertices[j].y;
            bool intersect = ((yi > py) != (yj > py)) &&
                             (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    }
};

struct ChargingStation {
    int64_t node_id;
    int32_t total_stalls = 4;
    int32_t occupied_stalls = 0;
    double charge_rate_kw = 50.0;
    std::string name;

    bool has_available_stall() const {
        return occupied_stalls < total_stalls;
    }
};

class Graph {
public:
    static constexpr double INFINITY_PENALTY = 1e9;

    static int64_t edge_key(int64_t u, int64_t v) {
        return (u * 0x9e3779b9) ^ v;
    }

    void add_node(const Node& node) {
        nodes_[node.id] = node;
    }

    void add_edge(const Edge& edge) {
        edges_.push_back(edge);
        adj_list_[edge.u].push_back(edge);
    }

    void add_charging_station(const ChargingStation& cs) {
        charging_stations_[cs.node_id] = cs;
    }

    const ChargingStation* get_charging_station(int64_t node_id) const {
        auto it = charging_stations_.find(node_id);
        return it != charging_stations_.end() ? &it->second : nullptr;
    }

    const std::unordered_map<int64_t, ChargingStation>& get_charging_stations() const {
        return charging_stations_;
    }

    const Node* get_node(int64_t id) const {
        auto it = nodes_.find(id);
        return it != nodes_.end() ? &it->second : nullptr;
    }

    const std::vector<Edge>& get_edges() const {
        return edges_;
    }

    const std::vector<Edge>& get_edges_from(int64_t u) const {
        static const std::vector<Edge> empty;
        auto it = adj_list_.find(u);
        return it != adj_list_.end() ? it->second : empty;
    }

    const std::unordered_map<int64_t, Node>& get_nodes() const {
        return nodes_;
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
        std::unordered_set<int32_t> zones;
        for (const auto& pair : nodes_) zones.insert(pair.second.zone_id);
        return zones.size();
    }

    void set_edge_penalty(int64_t u, int64_t v, double penalty) {
        int64_t key = edge_key(u, v);
        if (penalty <= 1.0) {
            edge_penalties_.erase(key);
        } else {
            edge_penalties_[key] = penalty;
        }
    }

    size_t apply_polygon_incident(const PolygonHazard& hazard) {
        size_t penalized_count = 0;
        for (const auto& edge : edges_) {
            const Node* nu = get_node(edge.u);
            const Node* nv = get_node(edge.v);
            if (!nu || !nv) continue;

            double mid_x = (nu->x + nv->x) * 0.5;
            double mid_y = (nu->y + nv->y) * 0.5;

            if (hazard.contains_point(nu->x, nu->y) ||
                hazard.contains_point(nv->x, nv->y) ||
                hazard.contains_point(mid_x, mid_y)) {
                set_edge_penalty(edge.u, edge.v, hazard.penalty);
                penalized_count++;
            }
        }
        return penalized_count;
    }

    double get_edge_penalty(int64_t u, int64_t v) const {
        if (edge_penalties_.empty()) return 1.0;
        auto it = edge_penalties_.find(edge_key(u, v));
        return it != edge_penalties_.end() ? it->second : 1.0;
    }

    void clear_all_penalties() {
        edge_penalties_.clear();
    }

    const std::unordered_map<int64_t, double>& get_all_penalties() const {
        return edge_penalties_;
    }

private:
    std::unordered_map<int64_t, Node> nodes_;
    std::vector<Edge> edges_;
    std::unordered_map<int64_t, std::vector<Edge>> adj_list_;
    std::unordered_map<int64_t, double> edge_penalties_;
    std::unordered_map<int64_t, ChargingStation> charging_stations_;
};

} // namespace nexussim
