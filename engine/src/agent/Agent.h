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

struct AgentSystem {
    alignas(64) std::vector<int64_t> id;
    alignas(64) std::vector<int64_t> origin;
    alignas(64) std::vector<int64_t> destination;
    alignas(64) std::vector<AgentType> type;
    alignas(64) std::vector<AgentState> state;
    alignas(64) std::vector<double> position;
    alignas(64) std::vector<double> velocity;
    alignas(64) std::vector<double> target_speed;
    alignas(64) std::vector<int64_t> current_edge_idx;
    alignas(64) std::vector<int32_t> lane;
    alignas(64) std::vector<std::vector<int64_t>> path;

    size_t add_agent(int64_t agent_id, int64_t orig, int64_t dest,
                     AgentType t) {
        size_t idx = id.size();
        id.push_back(agent_id);
        origin.push_back(orig);
        destination.push_back(dest);
        type.push_back(t);
        state.push_back(AgentState::Spawned);
        position.push_back(0.0);
        velocity.push_back(0.0);
        target_speed.push_back(0.0);
        current_edge_idx.push_back(0);
        lane.push_back(0);
        path.push_back({});
        return idx;
    }

    size_t size() const {
        return id.size();
    }
};

} // namespace nexussim
