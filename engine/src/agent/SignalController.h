#pragma once
#include <vector>
#include <cmath>
#include <algorithm>
#include <unordered_map>
#include <iostream>
#include <string>

namespace nexussim {

class SignalController {
public:
    enum class PhaseState { GREEN, YELLOW, RED };
    
    struct Phase {
        std::vector<int64_t> allowed_edges; // incoming edge IDs that get green
        double green_time;
        double yellow_time = 3.0; // standard 3s yellow
        double red_clearance = 2.0; // all-red clearance
        
        double get_total_time() const { return green_time + yellow_time + red_clearance; }
    };

    struct EmergencyVehicleBeacon {
        int64_t vehicle_id;
        int64_t approach_edge_id;
        double distance_to_stopline_m;
        double speed_mps;
        double timestamp_s;
    };

    struct PreemptionTelemetry {
        bool is_preempted = false;
        double remaining_s = 0.0;
        int64_t active_edge = -1;
        int phase_idx = 0;
    };

    PreemptionTelemetry get_preemption_telemetry() const {
        return {is_preempted, preemption_hold_remaining, active_preemption_edge, current_phase_idx};
    }

    int64_t node_id;
    std::vector<Phase> phases;
    
    int current_phase_idx = 0;
    double current_timer = 0.0;
    PhaseState current_state = PhaseState::GREEN;
    std::string mode = "webster";

    bool is_preempted = false;
    double preemption_hold_remaining = 0.0;
    int preemption_saved_phase = 0;
    PhaseState preemption_saved_state = PhaseState::GREEN;
    double preemption_saved_timer = 0.0;
    int64_t active_preemption_edge = -1;
    double preemption_clearance_buffer = 3.0; // 3.0s safety buffer post exit
    bool starvation_compensation_pending = false;
    double starved_extra_green = 5.0; // 5s compensation for starved phases

    SignalController(int64_t node_id = 0) : node_id(node_id) {}

    bool trigger_green_wave(int64_t approach_edge_id, double hold_duration = 10.0) {
        if (phases.empty()) return false;
        int target_idx = -1;
        for (size_t i = 0; i < phases.size(); ++i) {
            for (int64_t e : phases[i].allowed_edges) {
                if (e == approach_edge_id) {
                    target_idx = static_cast<int>(i);
                    break;
                }
            }
            if (target_idx != -1) break;
        }
        if (target_idx == -1) return false;

        if (!is_preempted) {
            preemption_saved_phase = current_phase_idx;
            preemption_saved_state = current_state;
            preemption_saved_timer = current_timer;
        }

        current_phase_idx = target_idx;
        current_state = PhaseState::GREEN;
        current_timer = hold_duration + preemption_clearance_buffer;
        is_preempted = true;
        preemption_hold_remaining = hold_duration + preemption_clearance_buffer;
        active_preemption_edge = approach_edge_id;
        return true;
    }

    void set_mode(const std::string& m) { mode = m; }
    std::string get_mode() const { return mode; }

    // Implements Webster's Formula for fixed cycle timing
    void calculate_webster_timing(const std::vector<std::vector<int64_t>>& phase_edges, 
                                  const std::vector<double>& phase_volumes,
                                  double saturation_flow = 1800.0) {
        phases.clear();
        int n_phases = static_cast<int>(phase_edges.size());
        if (n_phases == 0) return;

        double L = n_phases * 5.0; // 5 seconds lost time per phase (3s yellow + 2s all-red)
        
        double Y = 0.0;
        std::vector<double> y_i(n_phases);
        for (int i = 0; i < n_phases; ++i) {
            y_i[i] = phase_volumes[i] / saturation_flow;
            Y += y_i[i];
        }

        // Cap Y to 0.9 to prevent infinite cycle length
        if (Y >= 0.9) Y = 0.9;
        
        double cycle_length = (1.5 * L + 5.0) / (1.0 - Y);
        cycle_length = std::max(30.0, std::min(120.0, cycle_length));

        for (int i = 0; i < n_phases; ++i) {
            double g_i = (y_i[i] / (Y > 1e-6 ? Y : 1.0)) * (cycle_length - L);
            g_i = std::max(5.0, g_i); // minimum 5s green
            
            Phase p;
            p.allowed_edges = phase_edges[i];
            p.green_time = g_i;
            phases.push_back(p);
        }
        
        current_phase_idx = 0;
        current_timer = phases[0].green_time;
        current_state = PhaseState::GREEN;
    }

    bool end_green() {
        if (phases.empty() || current_state != PhaseState::GREEN) return false;
        current_state = PhaseState::YELLOW;
        current_timer = phases[current_phase_idx].yellow_time;
        return true;
    }

    void tick(double dt) {
        if (phases.empty()) return;

        if (is_preempted) {
            preemption_hold_remaining -= dt;
            current_timer = preemption_hold_remaining;
            if (preemption_hold_remaining <= 0.0) {
                is_preempted = false;
                active_preemption_edge = -1;
                starvation_compensation_pending = true;
                // Transition gracefully to clearance yellow
                current_state = PhaseState::YELLOW;
                current_timer = phases[current_phase_idx].yellow_time;
            }
            return;
        }

        current_timer -= dt;
        
        if (current_timer <= 0) {
            // State transition
            if (current_state == PhaseState::GREEN) {
                current_state = PhaseState::YELLOW;
                current_timer = phases[current_phase_idx].yellow_time;
            } else if (current_state == PhaseState::YELLOW) {
                current_state = PhaseState::RED;
                current_timer = phases[current_phase_idx].red_clearance;
            } else if (current_state == PhaseState::RED) {
                // Move to next phase
                current_phase_idx = (current_phase_idx + 1) % phases.size();
                current_state = PhaseState::GREEN;
                double extra = (starvation_compensation_pending ? starved_extra_green : 0.0);
                starvation_compensation_pending = false;
                current_timer = phases[current_phase_idx].green_time + extra;
            }
        }
    }

    bool is_green(int64_t incoming_edge_id) const {
        if (phases.empty() || current_state == PhaseState::RED) return false;
        if (current_state == PhaseState::YELLOW) return false;
        
        const auto& allowed = phases[current_phase_idx].allowed_edges;
        return std::find(allowed.begin(), allowed.end(), incoming_edge_id) != allowed.end();
    }
};

inline size_t trigger_corridor_green_wave(
    const std::vector<int64_t>& route_edges,
    std::unordered_map<int64_t, SignalController>& controllers,
    double hold_duration = 15.0) {
    size_t preempted = 0;
    for (int64_t edge_id : route_edges) {
        for (auto& [node_id, ctrl] : controllers) {
            if (ctrl.trigger_green_wave(edge_id, hold_duration)) {
                preempted++;
            }
        }
    }
    return preempted;
}

} // namespace nexussim
