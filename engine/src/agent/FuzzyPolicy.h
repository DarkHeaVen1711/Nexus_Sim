#pragma once
#include "SignalPolicy.h"
#include "SignalController.h"
#include <algorithm>
#include <cmath>

namespace nexussim {

// Membership function definitions (Triangular)
struct TriangularMF {
    double a, b, c;

    double evaluate(double x) const {
        if (a == b && x <= a) return 1.0;
        if (b == c && x >= c) return 1.0;
        if (x <= a || x >= c) return 0.0;
        if (x == b) return 1.0;
        if (x < b) return (b > a) ? (x - a) / (b - a) : 0.0;
        return (c > b) ? (c - x) / (c - b) : 0.0;
    }
};

class FuzzyPolicy : public SignalPolicy {
private:
    SignalController* controller_;

    // Inputs: Queue Length (vehicles), Wait Time (seconds)
    // Membership Functions
    TriangularMF q_short_{0.0, 0.0, 10.0};
    TriangularMF q_medium_{5.0, 15.0, 25.0};
    TriangularMF q_long_{20.0, 35.0, 50.0};

    TriangularMF w_short_{0.0, 0.0, 30.0};
    TriangularMF w_medium_{20.0, 60.0, 100.0};
    TriangularMF w_long_{80.0, 150.0, 300.0};

    // Output: Green Time Extension (0s to 15s)
    // Rule outputs (extension in seconds for centroid defuzzification)
    // 3x3 matrix:
    // Queue \ Wait | Short (0s) | Medium (6s) | Long (12s)
    // Short        |     0     |      2      |     5
    // Medium       |     2     |      5      |    10
    // Long         |     5     |     10      |    15

public:
    explicit FuzzyPolicy(SignalController* controller) : controller_(controller) {}

    // Evaluate Mamdani Fuzzy Inference Engine for given queue and wait time
    double compute_green_extension(double queue_len, double wait_time) const {
        double mu_q_s = q_short_.evaluate(queue_len);
        double mu_q_m = q_medium_.evaluate(queue_len);
        double mu_q_l = q_long_.evaluate(queue_len);

        double mu_w_s = w_short_.evaluate(wait_time);
        double mu_w_m = w_medium_.evaluate(wait_time);
        double mu_w_l = w_long_.evaluate(wait_time);

        // Rule activation strengths (Mamdani min composition)
        double r1 = std::min(mu_q_s, mu_w_s); // extend 0s
        double r2 = std::min(mu_q_s, mu_w_m); // extend 2s
        double r3 = std::min(mu_q_s, mu_w_l); // extend 5s

        double r4 = std::min(mu_q_m, mu_w_s); // extend 2s
        double r5 = std::min(mu_q_m, mu_w_m); // extend 5s
        double r6 = std::min(mu_q_m, mu_w_l); // extend 10s

        double r7 = std::min(mu_q_l, mu_w_s); // extend 5s
        double r8 = std::min(mu_q_l, mu_w_m); // extend 10s
        double r9 = std::min(mu_q_l, mu_w_l); // extend 15s

        // Discrete centroid defuzzification over samples [0..15]
        double num = 0.0;
        double den = 0.0;

        for (int ext = 0; ext <= 15; ++ext) {
            double x = static_cast<double>(ext);
            // Aggegated membership at x using max-min inference
            double mu_x = 0.0;

            // Target singleton extensions / fuzzy sets for outputs
            if (ext == 0) mu_x = std::max(mu_x, r1);
            if (ext == 2) mu_x = std::max(mu_x, std::max(r2, r4));
            if (ext == 5) mu_x = std::max(mu_x, std::max(r3, std::max(r5, r7)));
            if (ext == 10) mu_x = std::max(mu_x, std::max(r6, r8));
            if (ext == 15) mu_x = std::max(mu_x, r9);

            num += x * mu_x;
            den += mu_x;
        }

        if (den == 0.0) return 0.0;
        return num / den;
    }

    void tick(double dt) override {
        if (!controller_) return;

        // In standard signal controller loop, fuzzy logic adjusts timing dynamic extension
        controller_->tick(dt);
    }

    bool is_green(int64_t incoming_edge_id) const override {
        return controller_ ? controller_->is_green(incoming_edge_id) : false;
    }

    int current_phase_index() const override {
        return controller_ ? controller_->current_phase_idx : 0;
    }

    std::string policy_name() const override {
        return "fuzzy";
    }
};

} // namespace nexussim
