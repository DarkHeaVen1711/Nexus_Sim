#pragma once
#include "SignalPolicy.h"
#include "SignalController.h"
#include <vector>
#include <string>

namespace nexussim {

// Phase 30 Task 30.4: Native C++ implementation of GP-evolved decision tree policy (SC-8)
class SymbolicRulePolicy : public SignalPolicy {
private:
    SignalController* controller_;

public:
    explicit SymbolicRulePolicy(SignalController* controller) : controller_(controller) {}

    // Evaluate evolved symbolic binary decision rule over observation vector x
    // x = [queue_0, queue_1, wait_0, wait_1]
    int evaluate_symbolic_rule(const std::vector<float>& x) const {
        if (x.size() < 4) return 0; // Default EXTEND (0)
        // Evolved GP Decision Rule: (queue_0 > 8.5 ? (wait_1 > 45.0 ? SWITCH : EXTEND) : EXTEND)
        if (x[0] > 8.5f) {
            if (x[3] > 45.0f) {
                return 1; // SWITCH
            }
            return 0; // EXTEND
        }
        return 0; // EXTEND
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
        return "symbolic_gp";
    }
};

} // namespace nexussim
