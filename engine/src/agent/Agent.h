#pragma once
#include <cstdint>
#include <vector>
#include <algorithm>

namespace nexussim {

enum class AgentState {
    Spawned,
    Navigating,
    Arrived,
    Charging
};

enum class AgentType {
    Car,
    Bus,
    AutoRickshaw,
    TwoWheeler,
    Pedestrian,
    ElectricVehicle,
    Emergency
};

struct AgentKinematics {
    double max_speed_mps;
    double max_accel_mps2;
    double max_decel_mps2;
    double length_m;
    double width_m;

    static AgentKinematics for_type(AgentType t) {
        switch (t) {
            case AgentType::Bus:
                return {13.89, 1.0, 2.0, 12.0, 2.5}; // 50 km/h, 12m
            case AgentType::TwoWheeler:
                return {11.11, 1.8, 3.0, 2.0, 0.8};  // 40 km/h, 2m
            case AgentType::AutoRickshaw:
                return {10.0, 1.5, 2.5, 2.8, 1.3};   // 36 km/h, 2.8m
            case AgentType::Pedestrian:
                return {1.39, 0.8, 1.5, 0.5, 0.5};   // 5 km/h, 0.5m
            case AgentType::ElectricVehicle:
                return {16.67, 2.8, 4.0, 4.8, 1.8};  // 60 km/h, 4.8m, EV
            case AgentType::Emergency:
                return {22.22, 3.5, 4.5, 6.5, 2.2};  // 80 km/h, 6.5m
            case AgentType::Car:
            default:
                return {16.67, 2.5, 3.5, 4.8, 1.8};  // 60 km/h, 4.8m
        }
    }
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
    alignas(64) std::vector<double> wait_time;
    alignas(64) std::vector<double> start_time;
    alignas(64) std::vector<double> journey_time;
    alignas(64) std::vector<double> cur_edge_len;
    alignas(64) std::vector<std::vector<int64_t>> path;
    alignas(64) std::vector<uint8_t> needs_reroute;
    alignas(64) std::vector<double> battery_soc;
    alignas(64) std::vector<double> battery_capacity_kwh;
    alignas(64) std::vector<double> dwell_time_remaining;

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
        target_speed.push_back(AgentKinematics::for_type(t).max_speed_mps);
        current_edge_idx.push_back(0);
        lane.push_back(0);
        wait_time.push_back(0.0);
        start_time.push_back(-1.0);
        journey_time.push_back(-1.0);
        cur_edge_len.push_back(0.0);
        path.push_back({});
        needs_reroute.push_back(0);
        battery_soc.push_back(t == AgentType::ElectricVehicle ? 0.90 : 1.0);
        battery_capacity_kwh.push_back(t == AgentType::ElectricVehicle ? 60.0 : 0.0);
        dwell_time_remaining.push_back(0.0);
        return idx;
    }

    size_t size() const {
        return id.size();
    }
};

inline void simulate_ev_consumption(AgentSystem& agents, size_t idx, double distance_m, double dt_s) {
    if (idx >= agents.size()) return;
    if (agents.type[idx] != AgentType::ElectricVehicle) return;
    if (agents.battery_capacity_kwh[idx] <= 0.0) return;

    double dist_km = distance_m / 1000.0;
    // 0.18 kWh per km traction + 1.5 kW auxiliary
    double energy_kwh = (dist_km * 0.18) + (1.5 * (dt_s / 3600.0));
    double delta_soc = energy_kwh / agents.battery_capacity_kwh[idx];
    agents.battery_soc[idx] = std::max(0.0, agents.battery_soc[idx] - delta_soc);
}

inline bool simulate_ev_dwell(AgentSystem& agents, size_t idx, double dt_s, double charge_rate_kw = 50.0) {
    if (idx >= agents.size()) return false;
    if (agents.state[idx] != AgentState::Charging) return false;

    // Fast DC charging recovery
    if (agents.battery_capacity_kwh[idx] > 0.0) {
        double added_kwh = charge_rate_kw * (dt_s / 3600.0);
        double delta_soc = added_kwh / agents.battery_capacity_kwh[idx];
        agents.battery_soc[idx] = std::min(1.0, agents.battery_soc[idx] + delta_soc);
    }

    agents.dwell_time_remaining[idx] -= dt_s;
    if (agents.dwell_time_remaining[idx] <= 0.0) {
        agents.dwell_time_remaining[idx] = 0.0;
        agents.state[idx] = AgentState::Navigating;
        return true; // Dwell complete, resumed trip
    }
    return false; // Still charging
}

} // namespace nexussim
