#pragma once
#include <cmath>
#include <algorithm>
#include "Agent.h"

namespace nexussim {

struct IDMParams {
    double v0; // Desired speed (m/s)
    double T;  // Safe time headway (s)
    double s0; // Minimum gap (m)
    double a;  // Maximum acceleration (m/s^2)
    double b;  // Comfortable deceleration (m/s^2)
    double delta; // Acceleration exponent
    double length; // Vehicle length (m)
    double lane_discipline; // Base lane discipline (0-1)
};

// Default params based on updated high-throughput IDM dynamics
inline IDMParams get_default_idm_params(AgentType type, double chaos_coefficient) {
    IDMParams p;
    p.delta = 4.0;
    
    switch (type) {
        case AgentType::Car:
            p.v0 = 20.0; p.T = 1.2; p.s0 = 2.0; p.a = 2.2; p.b = 2.5; p.length = 4.5; p.lane_discipline = 1.0;
            break;
        case AgentType::Bus:
            p.v0 = 15.0; p.T = 1.6; p.s0 = 2.5; p.a = 1.2; p.b = 2.0; p.length = 12.0; p.lane_discipline = 0.9;
            break;
        case AgentType::AutoRickshaw:
            p.v0 = 13.5; p.T = 1.0; p.s0 = 1.0; p.a = 1.6; p.b = 2.8; p.length = 2.5; p.lane_discipline = 0.4;
            break;
        case AgentType::TwoWheeler:
            p.v0 = 16.5; p.T = 0.8; p.s0 = 0.5; p.a = 2.4; p.b = 3.5; p.length = 2.0; p.lane_discipline = 0.2;
            break;
        case AgentType::Pedestrian:
            p.v0 = 1.8; p.T = 0.5; p.s0 = 0.2; p.a = 2.0; p.b = 4.0; p.length = 0.5; p.lane_discipline = 0.1;
            break;
    }
    
    p.lane_discipline *= (1.0 - chaos_coefficient);
    p.lane_discipline = std::max(0.0, std::min(1.0, p.lane_discipline));
    
    return p;
}

// Hybrid modal split matrix based on lane count and zone classification
template <typename RNG>
inline AgentType select_agent_type_for_road(int32_t lanes, int32_t zone_id, RNG& rng) {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    double r = dist(rng);

    // Freeways / Highways (4+ lanes or Highway zone ID 999)
    if (lanes >= 4 || zone_id == 999) {
        if (r < 0.65) return AgentType::Car;
        if (r < 0.80) return AgentType::Bus;
        return AgentType::TwoWheeler;
    }
    // Narrow Streets / Residential (1 lane or Residential zone ID 1)
    else if (lanes <= 1 || zone_id == 1) {
        if (r < 0.45) return AgentType::Pedestrian;
        if (r < 0.75) return AgentType::TwoWheeler;
        if (r < 0.90) return AgentType::AutoRickshaw;
        return AgentType::Car;
    }
    // Standard Urban Arterial Roads (2-3 lanes)
    else {
        if (r < 0.50) return AgentType::Car;
        if (r < 0.70) return AgentType::TwoWheeler;
        if (r < 0.85) return AgentType::AutoRickshaw;
        if (r < 0.95) return AgentType::Bus;
        return AgentType::Pedestrian;
    }
}

inline double compute_idm_acceleration(const IDMParams& params, double v, double v_lead, double s) {
    // If no leader (s is infinity or very large)
    if (s > 1000.0) {
        return params.a * (1.0 - std::pow(v / params.v0, params.delta));
    }
    
    double dv = v - v_lead;
    double s_star = params.s0 + v * params.T + (v * dv) / (2.0 * std::sqrt(params.a * params.b));
    s_star = std::max(params.s0, s_star); // Cannot be less than minimum gap
    
    double acc = params.a * (1.0 - std::pow(v / params.v0, params.delta) - std::pow(s_star / s, 2.0));
    return acc;
}

} // namespace nexussim
