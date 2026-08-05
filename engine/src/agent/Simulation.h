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
#include "SignalController.h"
#include "../graph/Graph.h"
#include "../spatial/Quadtree.h"
#include "../network/WebSocketServer.h"
#include "../nlohmann/json.hpp"
#include "agent_delta_generated.h"
#include "flatbuffers/flatbuffers.h"
#include <memory>

namespace nexussim {

class Simulation {
public:
    Simulation(const Graph& graph, double chaos_coeff = 0.1)
        : graph_(graph), chaos_coefficient_(chaos_coeff) {
        for (const auto& pair : graph_.get_nodes())
            valid_nodes_.push_back(pair.first);
        precompute_edge_lengths();
        init_signals();
    }

    void set_speed_factor(double f) { speed_factor_ = f; }
    void set_route_spread(double s) { route_spread_ = s; }
    void set_chaos(double c) { chaos_coefficient_ = c; }
    void set_city_name(const std::string& n) { city_name_ = n; }

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
                get_default_idm_params(t, chaos_coefficient_).v0
                * speed_factor_;
            agents_.lane[idx] =
                static_cast<int32_t>(rng() % std::max(1, get_num_lanes(start, end)));
            agents_.start_time[idx] = 0.0;
        }
    }

    // Open-ended (dashboard) runs: give agents that finished their trip a fresh
    // origin/destination after a short rest so traffic never dies out. The road
    // network stays visually live for as long as the dashboard is connected.
    void respawn_arrived(double min_rest_seconds = 20.0) {
        if (valid_nodes_.empty()) return;
        std::uniform_int_distribution<size_t> dist(0, valid_nodes_.size() - 1);
        std::uniform_int_distribution<int> type_dist(0, 4);
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (agents_.state[i] != AgentState::Arrived) continue;
            if (agents_.start_time[i] >= 0.0 && agents_.journey_time[i] >= 0.0) {
                double arrived_at = agents_.start_time[i] + agents_.journey_time[i];
                if (sim_time_ - arrived_at < min_rest_seconds) continue;
            }
            int64_t start = valid_nodes_[dist(respawn_rng_)];
            int64_t end = valid_nodes_[dist(respawn_rng_)];
            while (start == end && valid_nodes_.size() > 1)
                end = valid_nodes_[dist(respawn_rng_)];

            AgentType t = static_cast<AgentType>(type_dist(respawn_rng_));
            agents_.origin[i] = start;
            agents_.destination[i] = end;
            agents_.type[i] = t;
            agents_.state[i] = AgentState::Spawned;
            agents_.position[i] = 0.0;
            agents_.velocity[i] = 0.0;
            agents_.current_edge_idx[i] = 0;
            agents_.wait_time[i] = 0.0;
            agents_.start_time[i] = sim_time_;
            agents_.journey_time[i] = -1.0;
            agents_.lane[i] = static_cast<int32_t>(
                respawn_rng_() % std::max(1, get_num_lanes(start, end)));
            agents_.path[i] = Pathfinder::compute_path(graph_, start, end);
            if (agents_.path[i].size() < 2)
                agents_.state[i] = AgentState::Arrived;
            agents_.target_speed[i] =
                get_default_idm_params(t, chaos_coefficient_).v0
                * speed_factor_;
        }
    }

    // Phase 6: spawn agents from a real OD demand matrix. Agents are emitted
    // over sim time at the OD pair's hourly rate for the current time-of-day
    // (start_hour + elapsed sim time), scaled by demand_scale for tractability.
    void spawn_agents_from_od(const std::string& od_path,
                              double demand_scale = 1.0,
                              double start_hour = 8.0) {
        demand_scale_ = demand_scale;
        start_hour_ = start_hour;

        std::ifstream f(od_path);
        if (!f.good()) {
            std::cerr << "OD file not found: " << od_path << "\n";
            return;
        }
        nlohmann::json j;
        f >> j;

        for (const auto& [id, node] : graph_.get_nodes())
            zone_nodes_[node.zone_id].push_back(node.id);

        int zones_without_nodes = 0;
        for (const auto& z : j["zones"].items()) {
            int32_t zid = std::stoi(z.key());
            if (zone_nodes_.find(zid) == zone_nodes_.end()
                || zone_nodes_[zid].empty())
                zones_without_nodes++;
        }

        int skipped = 0;
        for (const auto& e : j["od"]) {
            int32_t o = e["origin"];
            int32_t d = e["destination"];
            auto oit = zone_nodes_.find(o);
            auto dit = zone_nodes_.find(d);
            if (oit == zone_nodes_.end() || dit == zone_nodes_.end()
                || oit->second.empty() || dit->second.empty()) {
                skipped++;
                continue;
            }
            ODPair p;
            p.origin = o;
            p.destination = d;
            p.hourly.resize(24);
            for (int h = 0; h < 24; ++h)
                p.hourly[h] = e["hourly"].at(h);
            od_pairs_.push_back(std::move(p));
        }

        std::cout << "Loaded " << od_pairs_.size() << " OD pairs"
                  << " (demand_scale=" << demand_scale_
                  << ", start_hour=" << start_hour_ << ")\n";
        if (skipped)
            std::cout << "Skipped " << skipped
                      << " OD pairs with no graph nodes in a zone\n";
        if (zones_without_nodes)
            std::cout << "Zones without graph nodes: "
                      << zones_without_nodes << "\n";
    }

    void tick(double dt) {
        auto t0 = std::chrono::high_resolution_clock::now();
        sim_time_ += dt;
        update_od_spawns(dt);
        const size_t N = agents_.size();

        // Tick signal controllers
        for (auto& [id, sc] : signals_) sc->tick(dt);

        // Snapshot phase (sequential) — safe reads for parallel updates
        snap_x_.resize(N);
        snap_y_.resize(N);
        snap_v_.resize(N);
        snap_lat_.resize(N);
        snap_lon_.resize(N);
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

        // Update zone metrics every 10 ticks
        if (tick_count_ % 10 == 0) compute_zone_metrics();
    }

    void broadcast_state(network::WebSocketServer* ws_server) {
        if (!ws_server) return;

        // Phase 4.3 LOD culling: when the dashboard has sent viewport bounds,
        // only include agents inside them in the marker payload. Global metrics
        // are still computed over every agent so the numbers stay correct.
        bool has_bounds = ws_server->get_bounds(min_lat_, min_lon_,
                                                max_lat_, max_lon_);

        std::string json = "{\"tick\":";
        json += std::to_string(tick_count_);
        json += ",\"city\":\"";
        json += city_name_;
        json += "\",\"agents\":[";

        bool first = true;
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (snap_state_[i] != AgentState::Navigating && snap_state_[i] != AgentState::Spawned)
                continue;
            if (has_bounds
                && (snap_lat_[i] < min_lat_ || snap_lat_[i] > max_lat_
                    || snap_lon_[i] < min_lon_ || snap_lon_[i] > max_lon_))
                continue;
            if (!first) json += ",";
            first = false;
            json += "{\"id\":";
            json += std::to_string(agents_.id[i]);
            json += ",\"lat\":";
            json += std::to_string(snap_lat_[i]);
            json += ",\"lon\":";
            json += std::to_string(snap_lon_[i]);
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
        json += ",\"avg_wait_time\":";
        json += std::to_string(avg_wait_time_);
        json += ",\"gini_coefficient\":";
        json += std::to_string(gini_coefficient_);
        json += "},\"zone_metrics\":[";
        for (size_t z = 0; z < zone_wait_times_.size(); ++z) {
            if (z > 0) json += ",";
            json += "{\"zone_id\":";
            json += std::to_string(zone_wait_times_[z].first);
            json += ",\"wait_time\":";
            json += std::to_string(zone_wait_times_[z].second);
            json += "}";
        }
        json += "]}";

        ws_server->broadcast_text(json);
    }

    void log_journey_times(const std::string& filepath) {
        std::ofstream file(filepath);
        file << "agent_id,type,origin,destination,origin_zone,destination_zone,start_time,journey_time_seconds,status\n";
        for (size_t i = 0; i < agents_.size(); ++i) {
            const char* status = "Unknown";
            switch (agents_.state[i]) {
                case AgentState::Spawned:   status = "Spawned"; break;
                case AgentState::Navigating: status = "Navigating"; break;
                case AgentState::Arrived:   status = "Arrived"; break;
            }
            const Node* on = graph_.get_node(agents_.origin[i]);
            const Node* dn = graph_.get_node(agents_.destination[i]);
            file << agents_.id[i] << ","
                 << static_cast<int>(agents_.type[i]) << ","
                 << agents_.origin[i] << ","
                 << agents_.destination[i] << ","
                 << (on ? on->zone_id : 0) << ","
                 << (dn ? dn->zone_id : 0) << ","
                 << agents_.start_time[i] << ","
                 << agents_.journey_time[i] << ","
                 << status << "\n";
        }
    }

    size_t active_agents() const {
        size_t c = 0;
        for (auto s : agents_.state)
            if (s != AgentState::Arrived) c++;
        return c;
    }

    size_t completed_agents() const {
        size_t c = 0;
        for (auto s : agents_.state)
            if (s == AgentState::Arrived) c++;
        return c;
    }

    static double compute_gini(const std::vector<double>& v) {
        if (v.size() <= 1) return 0.0;
        double sum = std::accumulate(v.begin(), v.end(), 0.0);
        if (sum <= 0.0) return 0.0;
        double diff_sum = 0.0;
        for (size_t i = 0; i < v.size(); ++i)
            for (size_t j = 0; j < v.size(); ++j)
                diff_sum += std::abs(v[i] - v[j]);
        return diff_sum / (2.0 * v.size() * sum);
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
    double speed_factor_ = 1.0;
    double route_spread_ = 0.0;
    std::string city_name_;
    std::vector<int64_t> valid_nodes_;
    Quadtree<double> qt_{0, 0, 1, 1};

    // Phase 4.3 LOD culling: viewport bounds received from the dashboard.
    double min_lat_ = 0.0;
    double min_lon_ = 0.0;
    double max_lat_ = 0.0;
    double max_lon_ = 0.0;

    // Phase 6: OD demand-driven spawning
    struct ODPair {
        int32_t origin;
        int32_t destination;
        std::vector<double> hourly;
        double accum = 0.0;
    };
    std::vector<ODPair> od_pairs_;
    std::unordered_map<int32_t, std::vector<int64_t>> zone_nodes_;
    double demand_scale_ = 1.0;
    double start_hour_ = 8.0;
    double sim_time_ = 0.0;
    std::mt19937 od_rng_{20240607};
    std::mt19937 respawn_rng_{20240607};
    int64_t next_agent_id_ = 0;

    // Snapshots for thread-safe parallel reads
    std::vector<double> snap_x_, snap_y_, snap_v_;
    std::vector<double> snap_lat_, snap_lon_;
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

    // Signal controllers (one per signalized intersection)
    std::unordered_map<int64_t, std::unique_ptr<SignalController>> signals_;

    // Metrics
    double avg_wait_time_ = 0.0;
    double gini_coefficient_ = 0.0;
    std::vector<std::pair<int32_t, double>> zone_wait_times_;

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

    void update_od_spawns(double dt) {
        if (od_pairs_.empty()) return;
        double hour = std::fmod(start_hour_ + sim_time_ / 3600.0, 24.0);
        if (hour < 0) hour += 24.0;
        int h0 = static_cast<int>(hour);
        int h1 = (h0 + 1) % 24;
        double frac = hour - h0;
        for (auto& p : od_pairs_) {
            double rate = (p.hourly[h0] * (1.0 - frac)
                           + p.hourly[h1] * frac) * demand_scale_;
            if (rate <= 0.0) continue;
            p.accum += rate * dt / 3600.0;
            while (p.accum >= 1.0) {
                p.accum -= 1.0;
                spawn_od_agent(p.origin, p.destination);
            }
        }
    }

    void spawn_od_agent(int32_t zone_o, int32_t zone_d) {
        auto oit = zone_nodes_.find(zone_o);
        auto dit = zone_nodes_.find(zone_d);
        if (oit == zone_nodes_.end() || dit == zone_nodes_.end()) return;
        const auto& onodes = oit->second;
        const auto& dnodes = dit->second;
        if (onodes.empty() || dnodes.empty()) return;

        for (int attempt = 0; attempt < 8; ++attempt) {
            int64_t start = onodes[od_rng_() % onodes.size()];
            int64_t end = dnodes[od_rng_() % dnodes.size()];
            if (start == end) continue;

            AgentType t = AgentType::Car;
            size_t idx = agents_.add_agent(next_agent_id_++, start, end, t);
            agents_.path[idx] = Pathfinder::compute_path_stochastic(
                graph_, start, end, od_rng_, route_spread_);
            if (agents_.path[idx].size() < 2) {
                agents_.state[idx] = AgentState::Arrived;
                agents_.journey_time[idx] = -1.0;
                return;
            }
            agents_.target_speed[idx] =
                get_default_idm_params(t, chaos_coefficient_).v0
                * speed_factor_;
            agents_.lane[idx] = 0;
            agents_.start_time[idx] = sim_time_;
            return;
        }
    }

    void mark_arrived(size_t i) {
        agents_.state[i] = AgentState::Arrived;
        if (agents_.start_time[i] >= 0.0)
            agents_.journey_time[i] = sim_time_ - agents_.start_time[i];
    }

    void init_signals() {
        for (const auto& [id, node] : graph_.get_nodes()) {
            int degree = static_cast<int>(graph_.get_edges_from(id).size());
            for (const auto& e : graph_.get_edges())
                if (e.v == id) degree++;

            if (!node.is_signal && degree < 7) continue;

            auto sc = std::make_unique<SignalController>(id);

            std::vector<int64_t> incoming;
            for (const auto& e : graph_.get_edges())
                if (e.v == id) incoming.push_back(e.u);

            if (incoming.size() < 2) continue;

            struct EdgeAngle { int64_t from; double angle; };
            std::vector<EdgeAngle> ea;
            for (int64_t u : incoming) {
                const Node* nu = graph_.get_node(u);
                if (!nu) continue;
                double dx = node.x - nu->x;
                double dy = node.y - nu->y;
                ea.push_back({u, std::atan2(dy, dx)});
            }
            std::sort(ea.begin(), ea.end(),
                [](const EdgeAngle& a, const EdgeAngle& b) { return a.angle < b.angle; });

            size_t split = ea.size() / 2;
            std::vector<std::vector<int64_t>> phase_edges(2);
            std::vector<double> phase_volumes(2);
            for (size_t i = 0; i < ea.size(); ++i) {
                int ph = (i < split) ? 0 : 1;
                phase_edges[ph].push_back(ea[i].from);
                phase_volumes[ph] += 200.0 + degree * 30.0;
            }

            sc->calculate_webster_timing(phase_edges, phase_volumes);
            signals_[id] = std::move(sc);
        }
        if (!signals_.empty())
            std::cout << "Initialized " << signals_.size() << " signal controllers\n";
    }

    int32_t get_num_lanes(int64_t u, int64_t v) const {
        for (const auto& e : graph_.get_edges_from(u))
            if (e.v == v) return e.lanes;
        return 1;
    }

    void compute_world(size_t i) {
        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        const auto& p = agents_.path[i];
        if (p.empty()) { snap_x_[i] = 0; snap_y_[i] = 0; snap_lat_[i] = 0; snap_lon_[i] = 0; return; }
        if (ei + 1 >= p.size()) {
            const Node* n = graph_.get_node(p.back());
            snap_x_[i] = n ? n->x : 0;
            snap_y_[i] = n ? n->y : 0;
            snap_lat_[i] = n ? n->lat : 0;
            snap_lon_[i] = n ? n->lon : 0;
            snap_edge_dir_x_[i] = 0;
            snap_edge_dir_y_[i] = 0;
            return;
        }
        int64_t u = p[ei], v = p[ei + 1];
        const Node* nu = graph_.get_node(u);
        const Node* nv = graph_.get_node(v);
        if (!nu || !nv) { snap_x_[i] = 0; snap_y_[i] = 0; snap_lat_[i] = 0; snap_lon_[i] = 0; return; }

        double elen = lookup_edge_len(u, v);
        double t = (elen > 0)
            ? std::max(0.0, std::min(1.0, agents_.position[i] / elen))
            : 0.0;
        snap_x_[i] = nu->x + (nv->x - nu->x) * t;
        snap_y_[i] = nu->y + (nv->y - nu->y) * t;
        snap_lat_[i] = nu->lat + (nv->lat - nu->lat) * t;
        snap_lon_[i] = nu->lon + (nv->lon - nu->lon) * t;

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
        p.v0 *= speed_factor_;
        double v_lead = p.v0;
        double s = 10000.0;

        // Proximity-based deceleration via quadtree
        find_leader(i, v_lead, s);

        double acc = compute_idm_acceleration(p, agents_.velocity[i],
                                              v_lead, s);
        agents_.velocity[i] += acc * dt;
        agents_.velocity[i] = std::max(0.0, agents_.velocity[i]);

        // Signal check: stop at red lights
        const auto& path = agents_.path[i];
        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        if (ei + 1 < path.size()) {
            int64_t next_node = path[ei + 1];
            auto sig_it = signals_.find(next_node);
            if (sig_it != signals_.end()) {
                int64_t u = path[ei];
                if (!sig_it->second->is_green(u)) {
                    agents_.velocity[i] = 0.0;
                    agents_.wait_time[i] += dt;
                    return;
                }
            }
        }

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
            mark_arrived(i);
            return;
        }
        int64_t u = path[ei], v = path[ei + 1];
        double elen = lookup_edge_len(u, v);

        if (agents_.position[i] >= elen) {
            agents_.position[i] -= elen;
            agents_.current_edge_idx[i]++;
            if (agents_.current_edge_idx[i] + 1
                >= static_cast<int64_t>(path.size()))
                mark_arrived(i);
            else {
                agents_.lane[i] = 0;
            }
        }
    }

    int32_t get_agent_zone(size_t i) const {
        size_t ei = static_cast<size_t>(agents_.current_edge_idx[i]);
        const auto& p = agents_.path[i];
        if (p.empty()) return 0;
        int64_t node_id = (ei < p.size()) ? p[ei] : p.back();
        const Node* n = graph_.get_node(node_id);
        return n ? n->zone_id : 0;
    }

    void compute_zone_metrics() {
        std::unordered_map<int32_t, std::vector<double>> zone_waits;
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (agents_.state[i] != AgentState::Navigating
                && agents_.state[i] != AgentState::Spawned)
                continue;
            zone_waits[get_agent_zone(i)].push_back(agents_.wait_time[i]);
        }
        zone_wait_times_.clear();
        double total_wait = 0.0;
        size_t total_count = 0;
        for (auto& [z, waits] : zone_waits) {
            double avg = std::accumulate(waits.begin(), waits.end(), 0.0)
                         / waits.size();
            zone_wait_times_.push_back({z, avg});
            total_wait += std::accumulate(waits.begin(), waits.end(), 0.0);
            total_count += waits.size();
        }
        avg_wait_time_ = total_count > 0 ? total_wait / total_count : 0.0;
        std::vector<double> zone_avgs;
        for (auto& [z, avg] : zone_wait_times_) zone_avgs.push_back(avg);
        gini_coefficient_ = compute_gini(zone_avgs);
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
