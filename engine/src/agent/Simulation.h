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
                active.push_back(i);
            }
            snap_state_[i] = agents_.state[i];
        }

        rebuild_quadtree(active);

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

        auto t1 = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        tick_times_.push_back(ms);
        tick_count_++;
    }

    void log_journey_times(const std::string& filepath) {
        std::ofstream file(filepath);
        file << "agent_id,type,origin,destination,status\n";
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (agents_.state[i] == AgentState::Arrived)
                file << agents_.id[i] << ","
                     << static_cast<int>(agents_.type[i]) << ","
                     << agents_.origin[i] << ","
                     << agents_.destination[i] << ",Arrived\n";
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

    std::vector<double> snap_x_, snap_y_, snap_v_;
    std::vector<double> snap_edge_dir_x_, snap_edge_dir_y_;
    std::vector<AgentState> snap_state_;

    struct PairHash {
        size_t operator()(const std::pair<int64_t,int64_t>& p) const {
            return std::hash<int64_t>()(p.first)
                 ^ (std::hash<int64_t>()(p.second) * 0x9e3779b9);
        }
    };
    std::unordered_map<std::pair<int64_t,int64_t>,double,PairHash> edge_len_;

    std::vector<double> tick_times_;
    uint64_t tick_count_ = 0;

    void precompute_edge_lengths() {
        for (const auto& e : graph_.get_edges())
            edge_len_[{e.u, e.v}] = e.length_m;
    }

    double lookup_edge_len(int64_t u, int64_t v) const {
        auto it = edge_len_.find({u, v});
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
            ? std::clamp(agents_.position[i] / elen, 0.0, 1.0)
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
        IDMParams p = get_default_idm_params(agents_.type[i],
                                              chaos_coefficient_);
        double acc = compute_idm_acceleration(p, agents_.velocity[i],
                                              p.v0, 10000.0);
        agents_.velocity[i] += acc * dt;
        agents_.velocity[i] = std::max(0.0, agents_.velocity[i]);
        agents_.position[i] += agents_.velocity[i] * dt;
        advance_edge(i);
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
            else
                agents_.lane[i] = 0;
        }
    }
};

} // namespace nexussim
