#include <gtest/gtest.h>
#include "../src/agent/SignalController.h"

using namespace nexussim;

TEST(GreenWaveTest, SingleIntersectionPreemption) {
    SignalController ctrl(100);
    SignalController::Phase p0;
    p0.allowed_edges = {1, 2};
    p0.green_time = 20.0;
    p0.yellow_time = 3.0;
    p0.red_clearance = 2.0;

    SignalController::Phase p1;
    p1.allowed_edges = {3, 4}; // Cross street
    p1.green_time = 25.0;
    p1.yellow_time = 3.0;
    p1.red_clearance = 2.0;

    ctrl.phases = {p0, p1};
    ctrl.current_phase_idx = 1; // Currently cross street gets green
    ctrl.current_state = SignalController::PhaseState::GREEN;
    ctrl.current_timer = 25.0;

    EXPECT_FALSE(ctrl.is_green(1));
    EXPECT_TRUE(ctrl.is_green(3));

    // Emergency vehicle approaches on edge 1
    bool success = ctrl.trigger_green_wave(1, 12.0);
    EXPECT_TRUE(success);
    EXPECT_TRUE(ctrl.is_preempted);
    EXPECT_EQ(ctrl.current_phase_idx, 0); // Preempted to phase 0!
    EXPECT_TRUE(ctrl.is_green(1));
    EXPECT_FALSE(ctrl.is_green(3));

    auto telem = ctrl.get_preemption_telemetry();
    EXPECT_TRUE(telem.is_preempted);
    EXPECT_EQ(telem.active_edge, 1);
}
