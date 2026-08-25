#include <gtest/gtest.h>
#include "../src/agent/SignalController.h"
#include "../src/agent/Simulation.h"
#include <vector>
#include <cmath>

using namespace nexussim;

class SignalControllerTest : public ::testing::Test {
protected:
    void SetUp() override {
        sc = std::make_unique<SignalController>(100);
        std::vector<std::vector<int64_t>> phase_edges = {{1, 2}, {3, 4}};
        std::vector<double> phase_volumes = {400.0, 300.0};
        sc->calculate_webster_timing(phase_edges, phase_volumes);
    }
    std::unique_ptr<SignalController> sc;
};

TEST_F(SignalControllerTest, InitialStateIsGreen) {
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::GREEN);
}

TEST_F(SignalControllerTest, TransitionsGreenToYellow) {
    double green_time = sc->phases[0].green_time;
    sc->tick(green_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::YELLOW);
}

TEST_F(SignalControllerTest, TransitionsYellowToRed) {
    sc->tick(sc->phases[0].green_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::YELLOW);
    sc->tick(sc->phases[0].yellow_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::RED);
}

TEST_F(SignalControllerTest, TransitionsRedToNextGreen) {
    sc->tick(sc->phases[0].green_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::YELLOW);
    sc->tick(sc->phases[0].yellow_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::RED);
    sc->tick(sc->phases[0].red_clearance + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::GREEN);
    EXPECT_EQ(sc->current_phase_idx, 1);
}

TEST_F(SignalControllerTest, FullCycleBackToFirstPhase) {
    for (const auto& p : sc->phases) {
        sc->tick(p.green_time + 0.1);
        sc->tick(p.yellow_time + 0.1);
        sc->tick(p.red_clearance + 0.1);
    }
    EXPECT_EQ(sc->current_phase_idx, 0);
}

TEST_F(SignalControllerTest, IsGreenForAllowedEdge) {
    EXPECT_TRUE(sc->is_green(1));
    EXPECT_TRUE(sc->is_green(2));
}

TEST_F(SignalControllerTest, IsRedForDisallowedEdge) {
    EXPECT_FALSE(sc->is_green(3));
    EXPECT_FALSE(sc->is_green(4));
}

TEST_F(SignalControllerTest, WebsterCycleLengthInRange) {
    double total = 0;
    for (const auto& p : sc->phases) total += p.get_total_time();
    EXPECT_GE(total, 30.0);
    EXPECT_LE(total, 120.0);
}

TEST_F(SignalControllerTest, GreenTimeProportionalToVolume) {
    EXPECT_GT(sc->phases[0].green_time, sc->phases[1].green_time);
}

TEST_F(SignalControllerTest, EmptyPhasesNoCrash) {
    SignalController empty_sc(200);
    empty_sc.tick(1.0);
    EXPECT_FALSE(empty_sc.is_green(1));
}

TEST_F(SignalControllerTest, EndGreenSwitchesToYellow) {
    ASSERT_TRUE(sc->end_green());
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::YELLOW);
}

TEST_F(SignalControllerTest, EndGreenOnlyWorksDuringGreen) {
    sc->tick(sc->phases[0].green_time + 0.1); // now YELLOW
    EXPECT_FALSE(sc->end_green());
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::YELLOW);
}

TEST_F(SignalControllerTest, EndGreenFollowsNormalSequence) {
    ASSERT_TRUE(sc->end_green());
    sc->tick(sc->phases[0].yellow_time + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::RED);
    sc->tick(sc->phases[0].red_clearance + 0.1);
    EXPECT_EQ(sc->current_state, SignalController::PhaseState::GREEN);
    EXPECT_EQ(sc->current_phase_idx, 1);
}

TEST(GiniTest, UniformDistribution) {
    std::vector<double> v = {5.0, 5.0, 5.0, 5.0};
    EXPECT_NEAR(Simulation::compute_gini(v), 0.0, 1e-10);
}

TEST(GiniTest, ExtremeDistribution) {
    std::vector<double> v = {0.0, 0.0, 0.0, 100.0};
    double gini = Simulation::compute_gini(v);
    EXPECT_GT(gini, 0.7);
}

TEST(GiniTest, TwoElements) {
    std::vector<double> v = {1.0, 3.0};
    double expected = (std::abs(1.0 - 1.0) + std::abs(1.0 - 3.0)
                     + std::abs(3.0 - 1.0) + std::abs(3.0 - 3.0))
                    / (2.0 * 2.0 * 4.0);
    EXPECT_NEAR(Simulation::compute_gini(v), expected, 1e-10);
}

TEST(GiniTest, EmptyInput) {
    std::vector<double> v;
    EXPECT_DOUBLE_EQ(Simulation::compute_gini(v), 0.0);
}

TEST(GiniTest, SingleElement) {
    std::vector<double> v = {42.0};
    EXPECT_DOUBLE_EQ(Simulation::compute_gini(v), 0.0);
}

TEST(GiniTest, AllZeros) {
    std::vector<double> v = {0.0, 0.0, 0.0};
    EXPECT_DOUBLE_EQ(Simulation::compute_gini(v), 0.0);
}
