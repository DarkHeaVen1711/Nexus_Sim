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

// Default params based on typical IDM literature
inline IDMParams get_default_idm_params(AgentType type, double chaos_coefficient) {
    IDMParams p;
    p.delta = 4.0;
    
    switch (type) {
        case AgentType::Car:
            p.v0 = 15.0; p.T = 1.5; p.s0 = 2.0; p.a = 1.4; p.b = 2.0; p.length = 4.5; p.lane_discipline = 1.0;
            break;
        case AgentType::Bus:
            p.v0 = 12.0; p.T = 2.0; p.s0 = 3.0; p.a = 0.8; p.b = 1.5; p.length = 12.0; p.lane_discipline = 0.9;
            break;
        case AgentType::AutoRickshaw:
            p.v0 = 10.0; p.T = 1.2; p.s0 = 1.0; p.a = 1.2; p.b = 2.5; p.length = 2.5; p.lane_discipline = 0.4;
            break;
        case AgentType::TwoWheeler:
            p.v0 = 12.0; p.T = 1.0; p.s0 = 0.5; p.a = 1.8; p.b = 3.0; p.length = 2.0; p.lane_discipline = 0.2;
            break;
        case AgentType::Pedestrian:
            p.v0 = 1.5; p.T = 0.5; p.s0 = 0.2; p.a = 2.0; p.b = 4.0; p.length = 0.5; p.lane_discipline = 0.1;
            break;
    }
    
    p.lane_discipline *= (1.0 - chaos_coefficient);
    p.lane_discipline = std::max(0.0, std::min(1.0, p.lane_discipline));
    
    return p;
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
