#pragma once
#include <vector>
#include <thread>
#include <mutex>
#include <future>
#include <fstream>
#include <random>
#include <iostream>
#include "Agent.h"
#include "IDM.h"
#include "Pathfinder.h"
#include "../graph/Graph.h"

namespace nexussim {

class Simulation {
public:
    Simulation(const Graph& graph, double chaos_coeff = 0.1) 
        : graph_(graph), chaos_coefficient_(chaos_coeff) {
        
        for (const auto& pair : graph_.get_nodes()) {
            valid_nodes_.push_back(pair.first);
        }
    }

    void spawn_agents(size_t target_count) {
        if (valid_nodes_.empty()) return;
        std::mt19937 rng(42);
        std::uniform_int_distribution<size_t> dist(0, valid_nodes_.size() - 1);
        std::uniform_int_distribution<int> type_dist(0, 4);

        for (size_t i = agents_.size(); i < target_count; ++i) {
            int64_t start = valid_nodes_[dist(rng)];
            int64_t end = valid_nodes_[dist(rng)];
            while (start == end && valid_nodes_.size() > 1) {
                end = valid_nodes_[dist(rng)];
            }

            AgentType t = static_cast<AgentType>(type_dist(rng));
            size_t idx = agents_.add_agent(i, start, end, t);
            
            agents_.path[idx] = Pathfinder::compute_path(graph_, start, end);
            if (agents_.path[idx].size() < 2) {
                agents_.state[idx] = AgentState::Arrived; // No path found, just mark arrived
            }
        }
    }

    void tick(double dt) {
        size_t num_agents = agents_.size();
        size_t num_threads = std::thread::hardware_concurrency();
        if (num_threads == 0) num_threads = 4;
        
        std::vector<std::future<void>> futures;
        size_t chunk_size = (num_agents + num_threads - 1) / num_threads;

        for (size_t t = 0; t < num_threads; ++t) {
            size_t start_idx = t * chunk_size;
            size_t end_idx = std::min(start_idx + chunk_size, num_agents);
            
            if (start_idx >= end_idx) continue;

            futures.push_back(std::async(std::launch::async, [this, start_idx, end_idx, dt]() {
                this->update_agents(start_idx, end_idx, dt);
            }));
        }

        for (auto& f : futures) {
            f.get();
        }
    }

    void log_journey_times(const std::string& filepath) {
        std::ofstream file(filepath);
        file << "agent_id,type,origin,destination,status\n";
        for (size_t i = 0; i < agents_.size(); ++i) {
            if (agents_.state[i] == AgentState::Arrived) {
                file << agents_.id[i] << ","
                     << static_cast<int>(agents_.type[i]) << ","
                     << agents_.origin[i] << ","
                     << agents_.destination[i] << ","
                     << "Arrived\n";
            }
        }
    }

    size_t active_agents() const {
        size_t count = 0;
        for (auto s : agents_.state) {
            if (s != AgentState::Arrived) count++;
        }
        return count;
    }

private:
    const Graph& graph_;
    AgentSystem agents_;
    double chaos_coefficient_;
    std::vector<int64_t> valid_nodes_;

    void update_agents(size_t start, size_t end, double dt) {
        for (size_t i = start; i < end; ++i) {
            if (agents_.state[i] != AgentState::Spawned && agents_.state[i] != AgentState::Navigating) {
                continue;
            }
            agents_.state[i] = AgentState::Navigating;

            IDMParams p = get_default_idm_params(agents_.type[i], chaos_coefficient_);
            
            double v_lead = p.v0;
            double s = 10000.0; // Infinite distance for now

            double acc = compute_idm_acceleration(p, agents_.velocity[i], v_lead, s);
            
            agents_.velocity[i] += acc * dt;
            agents_.velocity[i] = std::max(0.0, agents_.velocity[i]); 
            
            double dist_moved = agents_.velocity[i] * dt;
            agents_.position[i] += dist_moved;

            size_t edge_idx = agents_.current_edge_idx[i];
            if (edge_idx + 1 < agents_.path[i].size()) {
                int64_t u = agents_.path[i][edge_idx];
                int64_t v = agents_.path[i][edge_idx + 1];
                
                double edge_len = 100.0;
                for (const auto& e : graph_.get_edges_from(u)) {
                    if (e.v == v) { edge_len = e.length_m; break; }
                }

                if (agents_.position[i] >= edge_len) {
                    agents_.position[i] -= edge_len;
                    agents_.current_edge_idx[i]++;
                    
                    if (agents_.current_edge_idx[i] + 1 >= agents_.path[i].size()) {
                        agents_.state[i] = AgentState::Arrived;
                    }
                }
            } else {
                agents_.state[i] = AgentState::Arrived;
            }
        }
    }
};

} // namespace nexussim
