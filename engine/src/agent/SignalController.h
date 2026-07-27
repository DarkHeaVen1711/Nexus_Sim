#pragma once
#include <vector>
#include <cmath>
#include <algorithm>
#include <unordered_map>
#include <iostream>

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

    int64_t node_id;
    std::vector<Phase> phases;
    
    int current_phase_idx = 0;
    double current_timer = 0.0;
    PhaseState current_state = PhaseState::GREEN;

    SignalController(int64_t node_id) : node_id(node_id) {}

    // Implements Webster's Formula for fixed cycle timing
    // volumes: traffic flow on each phase (vph)
    // saturation_flow: assumed capacity per lane (vph)
    void calculate_webster_timing(const std::vector<std::vector<int64_t>>& phase_edges, 
                                  const std::vector<double>& phase_volumes,
                                  double saturation_flow = 1800.0) {
        
        phases.clear();
        int n_phases = phase_edges.size();
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
        
        // Practical constraints for cycle length (min 30s, max 120s)
        cycle_length = std::max(30.0, std::min(120.0, cycle_length));

        for (int i = 0; i < n_phases; ++i) {
            double g_i = (y_i[i] / Y) * (cycle_length - L);
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

    void tick(double dt) {
        if (phases.empty()) return;

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
                current_timer = phases[current_phase_idx].green_time;
            }
        }
    }

    bool is_green(int64_t incoming_edge_id) const {
        if (phases.empty() || current_state == PhaseState::RED) return false;
        if (current_state == PhaseState::YELLOW) return false; // treat yellow as red for new approaching agents (simplified)
        
        const auto& allowed = phases[current_phase_idx].allowed_edges;
        return std::find(allowed.begin(), allowed.end(), incoming_edge_id) != allowed.end();
    }
};

} // namespace nexussim
