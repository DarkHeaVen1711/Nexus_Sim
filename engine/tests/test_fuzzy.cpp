#include <gtest/gtest.h>
#include "../src/agent/SignalController.h"
#include "../src/agent/FuzzyPolicy.h"
#include <memory>

using namespace nexussim;

class FuzzyPolicyTest : public ::testing::Test {
protected:
    void SetUp() override {
        sc = std::make_unique<SignalController>(101);
        std::vector<std::vector<int64_t>> phase_edges = {{10, 11}, {12, 13}};
        std::vector<double> phase_volumes = {500.0, 500.0};
        sc->calculate_webster_timing(phase_edges, phase_volumes);
        fuzzy = std::make_unique<FuzzyPolicy>(sc.get());
    }

    std::unique_ptr<SignalController> sc;
    std::unique_ptr<FuzzyPolicy> fuzzy;
};

TEST_F(FuzzyPolicyTest, PolicyNameReturnsFuzzy) {
    EXPECT_EQ(fuzzy->policy_name(), "fuzzy");
}

TEST_F(FuzzyPolicyTest, ZeroQueueZeroWaitGivesZeroExtension) {
    double ext = fuzzy->compute_green_extension(0.0, 0.0);
    EXPECT_NEAR(ext, 0.0, 1e-3);
}

TEST_F(FuzzyPolicyTest, MaxQueueMaxWaitGivesMaxExtension) {
    double ext = fuzzy->compute_green_extension(50.0, 300.0);
    EXPECT_NEAR(ext, 15.0, 1e-3);
}

TEST_F(FuzzyPolicyTest, MediumQueueMediumWaitGivesMidExtension) {
    double ext = fuzzy->compute_green_extension(15.0, 60.0);
    EXPECT_GT(ext, 2.0);
    EXPECT_LT(ext, 10.0);
}

TEST_F(FuzzyPolicyTest, DefuzzifiedRangeIsBounded) {
    for (double q = 0.0; q <= 60.0; q += 15.0) {
        for (double w = 0.0; w <= 350.0; w += 50.0) {
            double ext = fuzzy->compute_green_extension(q, w);
            EXPECT_GE(ext, 0.0);
            EXPECT_LE(ext, 15.0);
        }
    }
}

TEST_F(FuzzyPolicyTest, IsGreenMatchesControllerState) {
    EXPECT_TRUE(fuzzy->is_green(10));
    EXPECT_FALSE(fuzzy->is_green(12));
}

TEST_F(FuzzyPolicyTest, CurrentPhaseIndexMatchesController) {
    EXPECT_EQ(fuzzy->current_phase_index(), 0);
}
