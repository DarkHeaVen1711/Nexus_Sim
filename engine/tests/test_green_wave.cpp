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

TEST(GreenWaveTest, SafetyHoldBufferAndRestoration) {
    SignalController ctrl(100);
    SignalController::Phase p0;
    p0.allowed_edges = {10};
    p0.green_time = 15.0;
    p0.yellow_time = 3.0;
    p0.red_clearance = 2.0;

    SignalController::Phase p1;
    p1.allowed_edges = {20};
    p1.green_time = 15.0;
    p1.yellow_time = 3.0;
    p1.red_clearance = 2.0;

    ctrl.phases = {p0, p1};
    ctrl.current_phase_idx = 1;
    ctrl.current_state = SignalController::PhaseState::GREEN;

    // Trigger preemption for 5.0 seconds (+ 3.0s buffer = 8.0s total hold)
    ctrl.trigger_green_wave(10, 5.0);
    EXPECT_TRUE(ctrl.is_preempted);
    EXPECT_TRUE(ctrl.is_green(10));

    // Tick 4.0 seconds - still preempted
    ctrl.tick(4.0);
    EXPECT_TRUE(ctrl.is_preempted);
    EXPECT_TRUE(ctrl.is_green(10));

    // Tick 4.5 seconds more - hold expires (8.0s exceeded) -> transitions to yellow clearance
    ctrl.tick(4.5);
    EXPECT_FALSE(ctrl.is_preempted);
    EXPECT_EQ(ctrl.current_state, SignalController::PhaseState::YELLOW);
}

TEST(GreenWaveTest, StarvationPreventionCompensatesCrossStreet) {
    SignalController ctrl(200);
    SignalController::Phase p0;
    p0.allowed_edges = {100};
    p0.green_time = 10.0;
    p0.yellow_time = 3.0;
    p0.red_clearance = 2.0;

    SignalController::Phase p1;
    p1.allowed_edges = {200}; // Starved cross street
    p1.green_time = 10.0;
    p1.yellow_time = 3.0;
    p1.red_clearance = 2.0;

    ctrl.phases = {p0, p1};
    ctrl.trigger_green_wave(100, 2.0); // preemption on p0

    // Advance past hold buffer (2 + 3 = 5s)
    ctrl.tick(5.5);
    EXPECT_EQ(ctrl.current_state, SignalController::PhaseState::YELLOW);

    // Yellow -> Red clearance (3s)
    ctrl.tick(3.1);
    EXPECT_EQ(ctrl.current_state, SignalController::PhaseState::RED);

    // Red clearance -> Green for phase 1 with +5s starvation compensation
    ctrl.tick(2.1);
    EXPECT_EQ(ctrl.current_state, SignalController::PhaseState::GREEN);
    EXPECT_EQ(ctrl.current_phase_idx, 1);
    EXPECT_DOUBLE_EQ(ctrl.current_timer, 15.0); // 10s base + 5s compensation!
}

TEST(GreenWaveTest, MultiHopCorridorPropagation) {
    std::unordered_map<int64_t, SignalController> controllers;
    // Create 3 chained intersections along corridor edges 101, 102, 103
    for (int i = 1; i <= 3; ++i) {
        SignalController sc(i * 10);
        SignalController::Phase p0;
        p0.allowed_edges = {100 + i};
        p0.green_time = 20.0;
        SignalController::Phase p1;
        p1.allowed_edges = {200 + i};
        p1.green_time = 20.0;
        sc.phases = {p0, p1};
        sc.current_phase_idx = 1; // Initially in red for the corridor
        controllers.emplace(i * 10, sc);
    }

    std::vector<int64_t> route = {101, 102, 103};
    size_t count = trigger_corridor_green_wave(route, controllers, 25.0);
    EXPECT_EQ(count, 3u);

    // All 3 controllers along the corridor should now have active green for the corridor edges
    for (int i = 1; i <= 3; ++i) {
        EXPECT_TRUE(controllers[i * 10].is_preempted);
        EXPECT_TRUE(controllers[i * 10].is_green(100 + i));
    }
}

TEST(GreenWaveTest, PriorityHierarchyEmergencyOverridesTransit) {
    SignalController ctrl(300);
    SignalController::Phase p0;
    p0.allowed_edges = {10}; // Transit bus approach
    p0.green_time = 15.0;

    SignalController::Phase p1;
    p1.allowed_edges = {20}; // Emergency vehicle approach
    p1.green_time = 15.0;

    ctrl.phases = {p0, p1};
    ctrl.current_phase_idx = 0;
    ctrl.current_state = SignalController::PhaseState::GREEN;
    ctrl.current_timer = 10.0;

    // Bus requests TSP extension -> granted (+5s)
    EXPECT_TRUE(ctrl.request_transit_priority(10, 5.0));
    EXPECT_DOUBLE_EQ(ctrl.current_timer, 15.0);

    // Emergency vehicle approaches on cross street edge 20 -> preempts immediately!
    EXPECT_TRUE(ctrl.trigger_green_wave(20, 10.0));
    EXPECT_TRUE(ctrl.is_preempted);
    EXPECT_EQ(ctrl.current_phase_idx, 1);
    EXPECT_TRUE(ctrl.is_green(20));

    // While emergency is preempted, any further bus TSP request is denied
    EXPECT_FALSE(ctrl.request_transit_priority(10, 5.0));
}
