#pragma once
#include <cstdint>
#include <vector>

namespace nexussim {

enum class AgentState {
    Spawned,
    Navigating,
    Arrived
};

enum class AgentType {
    Car,
    Bus,
    AutoRickshaw,
    TwoWheeler,
    Pedestrian
};

// Struct-of-Arrays (SoA) layout for Agents
struct AgentSystem {
    std::vector<int64_t> id;
    std::vector<int64_t> origin;
    std::vector<int64_t> destination;
    std::vector<AgentType> type;
    std::vector<AgentState> state;
    std::vector<double> position; // Position along current edge (meters)
    std::vector<double> velocity; // Current velocity (m/s)
    std::vector<int64_t> current_edge_idx; // Index of the current edge in the path
    std::vector<std::vector<int64_t>> path; // Sequence of node IDs
    
    // Add a new agent and return its internal index
    size_t add_agent(int64_t agent_id, int64_t orig, int64_t dest, AgentType t) {
        size_t idx = id.size();
        id.push_back(agent_id);
        origin.push_back(orig);
        destination.push_back(dest);
        type.push_back(t);
        state.push_back(AgentState::Spawned);
        position.push_back(0.0);
        velocity.push_back(0.0);
        current_edge_idx.push_back(0);
        path.push_back({});
        return idx;
    }

    size_t size() const {
        return id.size();
    }
};

} // namespace nexussim
