#pragma once
#include "SignalPolicy.h"
#include "SignalController.h"
#include <algorithm>
#include <cmath>

namespace nexussim {

// Interval Type-2 Membership Function: Lower & Upper Membership Bounds [LMF, UMF]
struct IntervalType2MF {
    double a1, b1, c1; // Lower MF parameters
    double a2, b2, c2; // Upper MF parameters (Footprint of Uncertainty - FOU)

    std::pair<double, double> evaluate(double x) const {
        auto eval_tri = [](double v, double a, double b, double c) {
            if (a == b && v <= a) return 1.0;
            if (b == c && v >= c) return 1.0;
            if (v <= a || v >= c) return 0.0;
            if (v == b) return 1.0;
            if (v < b) return (b > a) ? (v - a) / (b - a) : 0.0;
            return (c > b) ? (c - v) / (c - b) : 0.0;
        };

        double lmf = eval_tri(x, a1, b1, c1);
        double umf = eval_tri(x, a2, b2, c2);
        return {std::min(lmf, umf), std::max(lmf, umf)};
    }
};

class Type2FuzzyPolicy : public SignalPolicy {
private:
    SignalController* controller_;

    // Footprint of uncertainty bounds (Interval Type-2)
    IntervalType2MF q_short_{{0.0, 0.0, 8.0}, {0.0, 0.0, 12.0}};
    IntervalType2MF q_medium_{{6.0, 15.0, 24.0}, {4.0, 15.0, 28.0}};
    IntervalType2MF q_long_{{22.0, 35.0, 1e9}, {18.0, 35.0, 1e9}};

    IntervalType2MF w_short_{{0.0, 0.0, 25.0}, {0.0, 0.0, 35.0}};
    IntervalType2MF w_medium_{{25.0, 60.0, 95.0}, {15.0, 60.0, 105.0}};
    IntervalType2MF w_long_{{85.0, 150.0, 1e9}, {75.0, 150.0, 1e9}};

public:
    explicit Type2FuzzyPolicy(SignalController* controller) : controller_(controller) {}

    // Karnik-Mendel (KM) iterative type-reduction algorithm approximation
    double compute_green_extension(double queue_len, double wait_time) const {
        auto [q_s_l, q_s_u] = q_short_.evaluate(queue_len);
        auto [q_m_l, q_m_u] = q_medium_.evaluate(queue_len);
        auto [q_l_l, q_l_u] = q_long_.evaluate(queue_len);

        auto [w_s_l, w_s_u] = w_short_.evaluate(wait_time);
        auto [w_m_l, w_m_u] = w_medium_.evaluate(wait_time);
        auto [w_l_l, w_l_u] = w_long_.evaluate(wait_time);

        // Lower and upper firing strengths
        double f_l1 = std::min(q_s_l, w_s_l); double f_u1 = std::min(q_s_u, w_s_u); // 0s
        double f_l2 = std::min(q_m_l, w_m_l); double f_u2 = std::min(q_m_u, w_m_u); // 5s
        double f_l3 = std::min(q_l_l, w_l_l); double f_u3 = std::min(q_l_u, w_l_u); // 15s

        // Type reduction centroid bounds [y_left, y_right]
        double y_left = (0.0 * f_u1 + 5.0 * f_l2 + 15.0 * f_l3) / std::max(1e-4, f_u1 + f_l2 + f_l3);
        double y_right = (0.0 * f_l1 + 5.0 * f_u2 + 15.0 * f_u3) / std::max(1e-4, f_l1 + f_u2 + f_u3);

        // Defuzzified crisp value is average of KM bounds
        return std::max(0.0, std::min(15.0, (y_left + y_right) / 2.0));
    }

    void tick(double dt) override {
        if (controller_) controller_->tick(dt);
    }

    bool is_green(int64_t incoming_edge_id) const override {
        return controller_ ? controller_->is_green(incoming_edge_id) : false;
    }

    int current_phase_index() const override {
        return controller_ ? controller_->current_phase_idx : 0;
    }

    std::string policy_name() const override {
        return "type2_fuzzy";
    }
};

} // namespace nexussim
