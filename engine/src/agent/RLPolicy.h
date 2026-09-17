#pragma once
#include "SignalPolicy.h"
#include "SignalController.h"

namespace nexussim {

class RLPolicy : public SignalPolicy {
private:
    SignalController* controller_;
public:
    explicit RLPolicy(SignalController* controller) : controller_(controller) {}

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
        return "rl";
    }
};

} // namespace nexussim
