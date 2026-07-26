#pragma once
#include <vector>
#include <thread>
#include <future>
#include <fstream>
#include <random>
#include <iostream>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <unordered_map>
#include "Agent.h"
#include "IDM.h"
#include "Pathfinder.h"
#include "../graph/Graph.h"
#include "../spatial/Quadtree.h"
#include "../network/WebSocketServer.h"
#include "agent_delta_generated.h"
#include "flatbuffers/flatbuffers.h"

namespace nexussim {

class Simulation {
public:
    Simulation(const Graph& graph, double chaos_coeff = 0.1)
        : graph_(graph), chaos_coefficient_(chaos_coeff) {
        for (const auto& pair : graph_.get_nodes())
            valid_nodes_.push_back(pair.first);
        precompute_edge_lengths();
    }

    void spawn_agents(size_t target_count) {
        if (valid_nodes_.empty()) return;
        std::mt19937 rng(42);
        std::uniform_int_distribution<size_t> dist(0, valid_nodes_.size() - 1);
        std::uniform_int_distribution<int> type_dist(0, 4);

        for (size_t i = agents_.size(); i < target_count; ++i) {
            int64_t start = valid_nodes_[dist(rng)];
            int64_t end   = valid_nodes_[dist(rng)];
            while (start == end && valid_nodes_.size() > 1)
                end = valid_nodes_[dist(rng)];

            AgentType t = static_cast<AgentType>(type_dist(rng));
            size_t idx = agents_.add_agent(i, start, end, t);
            agents_.path[idx] = Pathfinder::compute_path(graph_, start, end);
            if (agents_.path[idx].size() < 2)
                agents_.state[idx] = AgentState::Arrived;
            agents_.target_speed[idx] =
                get_default_idm_params(t, chaos_coefficient_).v0;
            agents_.lane[idx] =
                static_cast<int32_t>(rng() % std::max(1, get_num_lanes(start, end)));
        }
    }

    void tick(double dt) {
        auto t0 = std::chrono::high_resolution_clock::now();
        const size_t N = agents_.size();

        // Snapshot phase (sequential) — safe reads for parallel updates
        snap_x_.resize(N);
        snap_y_.resize(N);
        snap_v_.resize(N);
        snap_state_.resize(N);
        snap_edge_dir_x_.resize(N);
        snap_edge_dir_y_.resize(N);

        std::vector<size_t> active;
        active.reserve(N);
        for (size_t i = 0; i < N; ++i) {
            auto s = agents_.state[i];
            if (s == AgentState::Spawned || s == AgentState::Navigating) {
                compute_world(i);
                snap_v_[i] = agents_.velocity[i];
                active.push_back(i);
            }
            snap_state_[i] = agents_.state[i];
        }

        // Rebuild quadtree
        rebuild_quadtree(active);

        // Parallel agent updates (with fallback to sequential if C++11 thread support is missing)
#if defined(_GLIBCXX_HAS_GTHREADS) || defined(_MSC_VER)
        size_t nthreads = std::thread::hardware_concurrency();
        if (nthreads == 0) nthreads = 4;
        size_t chunk = (active.size() + nthreads - 1) / nthreads;
        std::vector<std::future<void>> futures;
        for (size_t t = 0; t < nthreads; ++t) {
            size_t s = t * chunk;
            size_t e = std::min(s + chunk, active.size());
            if (s >= e) continue;
            futures.push_back(std::async(std::launch::async,
                [this, &active, s, e, dt]() {
                    for (size_t k = s; k < e; ++k)
                        update_agent(active[k], dt);
                }));
        }
        for (auto& f : futures) f.get();
#else
        for (size_t k = 0; k < active.size(); ++k) {
            update_agent(active[k], dt);
        }
#endif


        // FPS tracking
        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        tick_times_.push_back(ms);
        tick_count_++;
        if (tick_count_ % 500 == 0) log_fps();
    }

    void broadcast_state(network::WebSocketServer* ws_server) {
        if (!ws_server) return;

        std::string json = "{\"tick\":";
        json += std::to_string(tick_count_);
        json += ",\"agents\":[";

        bool first = true;
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (snap_state_[i] != AgentState::Navigating && snap_state_[i] != AgentState::Spawned)
                continue;
            if (!first) json += ",";
            first = false;
            json += "{\"id\":";
            json += std::to_string(agents_.id[i]);
            json += ",\"lat\":";
            json += std::to_string(snap_y_[i]);
            json += ",\"lon\":";
            json += std::to_string(snap_x_[i]);
            json += ",\"heading\":";
            json += std::to_string(std::atan2(snap_edge_dir_y_[i], snap_edge_dir_x_[i]));
            json += ",\"type\":";
            json += std::to_string(static_cast<int>(agents_.type[i]));
            json += ",\"speed\":";
            json += std::to_string(agents_.velocity[i]);
            json += "}";
        }

        json += "],\"metrics\":{\"avg_speed\":";
        double total_v = 0;
        size_t nav_count = 0;
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (snap_state_[i] == AgentState::Navigating || snap_state_[i] == AgentState::Spawned) {
                total_v += agents_.velocity[i];
                nav_count++;
            }
        }
        json += std::to_string(nav_count > 0 ? total_v / nav_count : 0.0);
        json += ",\"active_agents\":";
        json += std::to_string(nav_count);
        json += ",\"completed_agents\":";
        size_t arrived = 0;
        for (auto s : agents_.state)
            if (s == AgentState::Arrived) arrived++;
        json += std::to_string(arrived);
        json += "},\"zone_metrics\":[]}";

        ws_server->broadcast_text(json);
    }

    void log_journey_times(const std::string& filepath) {
        std::ofstream file(filepath);
        file << "agent_id,type,origin,destination,status\n";
        for (size_t i = 0; i < agents_.size(); ++i) {
            const char* status = "Unknown";
            switch (agents_.state[i]) {
                case AgentState::Spawned:   status = "Spawned"; break;
                case AgentState::Navigating: status = "Navigating"; break;
                case AgentState::Arrived:   status = "Arrived"; break;
            }
            file << agents_.id[i] << ","
                 << static_cast<int>(agents_.type[i]) << ","
                 << agents_.origin[i] << ","
                 << agents_.destination[i] << ","
                 << status << "\n";
        }
    }

    size_t active_agents() const {
        size_t c = 0;
        for (auto s : agents_.state)
            if (s != AgentState::Arrived) c++;
        return c;
    }

    double avg_tick_ms() const {
        if (tick_times_.empty()) return 0.0;
        return std::accumulate(tick_times_.begin(),
                               tick_times_.end(), 0.0)
               / tick_times_.size();
    }

    double p95_tick_ms() const {
        if (tick_times_.empty()) return 0.0;
        auto v = tick_times_;
        std::sort(v.begin(), v.end());
        size_t idx = static_cast<size_t>(v.size() * 0.95);
        return v[std::min(idx, v.size() - 1)];
    }

private:
    const Graph& graph_;
    AgentSystem agents_;
    double chaos_coefficient_;
    std::vector<int64_t> valid_nodes_;
    Quadtree<double> qt_{0, 0, 1, 1};

    // Snapshots for thread-safe parallel reads
    std::vector<double> snap_x_, snap_y_, snap_v_;
    std::vector<double> snap_edge_dir_x_, snap_edge_dir_y_;
    std::vector<AgentState> snap_state_;

    // Edge length lookup cache
    struct PairHash {
        size_t operator()(const std::pair<int64_t,int64_t>& p) const {
            return std::hash<int64_t>()(p.first)
                 ^ (std::hash<int64_t>()(p.second) * 0x9e3779b9);
        }
    };
    std::unordered_map<std::pair<int64_t,int64_t>,double,PairHash> edge_len_;

    // FPS tracking
    std::vector<double> tick_times_;
    uint64_t tick_count_ = 0;

    void precompute_edge_lengths() {
        for (const auto& e : graph_.get_edges())
            edge_len_[std::make_pair(e.u, e.v)] = e.length_m;
    }

    double lookup_edge_len(int64_t u, int64_t v) const {
        auto it = edge_len_.find(std::make_pair(u, v));
        return it != edge_len_.end() ? it->second : 100.0;
    }

    int32_t get_num_lanes(int64_t u, int64_t v) const {
        for (const auto& e : graph_.get_edges_from(u))
            if (e.v == v) return e.lanes;
        return 1;
    }

    void compute_world(size_t i) {
        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        const auto& p = agents_.path[i];
        if (p.empty()) { snap_x_[i] = 0; snap_y_[i] = 0; return; }
        if (ei + 1 >= p.size()) {
            const Node* n = graph_.get_node(p.back());
            snap_x_[i] = n ? n->x : 0;
            snap_y_[i] = n ? n->y : 0;
            snap_edge_dir_x_[i] = 0;
            snap_edge_dir_y_[i] = 0;
            return;
        }
        int64_t u = p[ei], v = p[ei + 1];
        const Node* nu = graph_.get_node(u);
        const Node* nv = graph_.get_node(v);
        if (!nu || !nv) { snap_x_[i] = 0; snap_y_[i] = 0; return; }

        double elen = lookup_edge_len(u, v);
        double t = (elen > 0)
            ? std::max(0.0, std::min(1.0, agents_.position[i] / elen))
            : 0.0;
        snap_x_[i] = nu->x + (nv->x - nu->x) * t;
        snap_y_[i] = nu->y + (nv->y - nu->y) * t;

        double dx = nv->x - nu->x;
        double dy = nv->y - nu->y;
        double len = std::hypot(dx, dy);
        snap_edge_dir_x_[i] = (len > 0) ? dx / len : 0;
        snap_edge_dir_y_[i] = (len > 0) ? dy / len : 0;
    }

    void rebuild_quadtree(const std::vector<size_t>& active) {
        if (active.empty()) return;
        std::vector<double> xs(active.size()), ys(active.size());
        for (size_t k = 0; k < active.size(); ++k) {
            xs[k] = snap_x_[active[k]];
            ys[k] = snap_y_[active[k]];
        }
        qt_.rebuild(xs, ys, active);
    }

    void update_agent(size_t i, double dt) {
        if (agents_.state[i] == AgentState::Spawned) {
            agents_.state[i] = AgentState::Navigating;
        }

        IDMParams p = get_default_idm_params(agents_.type[i],
                                              chaos_coefficient_);
        double v_lead = p.v0;
        double s = 10000.0;

        // Proximity-based deceleration via quadtree
        find_leader(i, v_lead, s);

        double acc = compute_idm_acceleration(p, agents_.velocity[i],
                                              v_lead, s);
        agents_.velocity[i] += acc * dt;
        agents_.velocity[i] = std::max(0.0, agents_.velocity[i]);

        double dist = agents_.velocity[i] * dt;
        agents_.position[i] += dist;

        // Lane change check
        maybe_lane_change(i, dt);

        // Edge advancement
        advance_edge(i);
    }

    void find_leader(size_t i, double& v_lead, double& s) {
        double ax = snap_x_[i], ay = snap_y_[i];
        double dx = snap_edge_dir_x_[i];
        double dy = snap_edge_dir_y_[i];

        double follow_dist = agents_.target_speed[i] * 3.0 + 20.0;
        std::vector<QuadPoint<double>> nearby;
        qt_.query_radius(ax, ay, follow_dist, nearby);

        double best_s = 1e18;
        double best_v = 0;
        for (const auto& pt : nearby) {
            size_t j = pt.idx;
            if (j == i) continue;
            if (snap_state_[j] != AgentState::Navigating
                && snap_state_[j] != AgentState::Spawned)
                continue;

            double rel_x = pt.x - ax;
            double rel_y = pt.y - ay;
            double proj = rel_x * dx + rel_y * dy;

            if (proj <= 0.5) continue; // Not ahead

            double perp = std::abs(rel_x * (-dy) + rel_y * dx);
            if (perp > 5.0) continue; // Different lateral position

            if (proj < best_s) {
                best_s = proj;
                best_v = snap_v_[j];
            }
        }
        if (best_s < 1e17) {
            s = best_s;
            v_lead = best_v;
        }
    }

    void maybe_lane_change(size_t i, double dt) {
        if (snap_state_[i] != AgentState::Navigating) return;
        IDMParams p = get_default_idm_params(agents_.type[i],
                                              chaos_coefficient_);
        double prob = (1.0 - p.lane_discipline)
                    * chaos_coefficient_ * dt * 0.5;
        if (prob <= 0) return;

        std::mt19937 rng(agents_.id[i] + tick_count_);
        std::uniform_real_distribution<double> coin(0.0, 1.0);
        if (coin(rng) >= prob) return;

        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        const auto& path = agents_.path[i];
        if (ei + 1 >= path.size()) return;
        int32_t max_lane = get_num_lanes(path[ei], path[ei + 1]) - 1;
        if (max_lane <= 0) return;

        int32_t dir = (coin(rng) < 0.5) ? -1 : 1;
        int32_t target = agents_.lane[i] + dir;
        if (target < 0 || target > max_lane) return;

        double ax = snap_x_[i], ay = snap_y_[i];
        double px = -snap_edge_dir_y_[i];
        double py =  snap_edge_dir_x_[i];
        double shift = 3.5 * dir;
        double tx = ax + px * shift;
        double ty = ay + py * shift;

        std::vector<QuadPoint<double>> lateral;
        qt_.query_radius(tx, ty, 5.0, lateral);

        bool blocked = false;
        for (const auto& pt : lateral) {
            size_t j = pt.idx;
            if (j == i) continue;
            double dx2 = pt.x - tx;
            double dy2 = pt.y - ty;
            if (dx2 * dx2 + dy2 * dy2 < 25.0) {
                blocked = true;
                break;
            }
        }
        if (!blocked) agents_.lane[i] = target;
    }

    void advance_edge(size_t i) {
        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        auto& path = agents_.path[i];
        if (ei + 1 >= path.size()) {
            agents_.state[i] = AgentState::Arrived;
            return;
        }
        int64_t u = path[ei], v = path[ei + 1];
        double elen = lookup_edge_len(u, v);

        if (agents_.position[i] >= elen) {
            agents_.position[i] -= elen;
            agents_.current_edge_idx[i]++;
            if (agents_.current_edge_idx[i] + 1
                >= static_cast<int64_t>(path.size()))
                agents_.state[i] = AgentState::Arrived;
            else {
                agents_.lane[i] = 0;
            }
        }
    }

    void log_fps() {
        double avg = avg_tick_ms();
        double p95 = p95_tick_ms();
        double fps = (avg > 0) ? 1000.0 / avg : 0;
        std::cout << "[FPS] tick=" << tick_count_
                  << " avg=" << avg << "ms"
                  << " p95=" << p95 << "ms"
                  << " fps=" << fps << "\n";
    }
};

} // namespace nexussim
