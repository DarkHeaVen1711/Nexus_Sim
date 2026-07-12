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

    void update_agents(size_t start, size_t end, double dt) {}
};

} // namespace nexussim
