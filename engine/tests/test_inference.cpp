// Unit tests for the InferenceEngine ONNX wrapper (Phase 8.3).
// The fixture policy_toy.onnx is a 11 -> 16 -> 16 -> 2 MLP exported with
// torch.manual_seed(0); only structural properties are asserted so the
// tests never depend on specific weight values.

#include "ai/InferenceEngine.h"
#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>

namespace fs = std::filesystem;

namespace {

std::string fixture_path() {
    return (fs::path(TESTS_SOURCE_DIR) / "fixtures" / "policy_toy.onnx")
        .string();
}

std::vector<float> make_batch(size_t batch, float seed) {
    std::vector<float> obs(batch * 11);
    for (size_t i = 0; i < obs.size(); ++i)
        obs[i] = static_cast<float>((i % 7) + seed) * 0.1f;
    return obs;
}

} // namespace

TEST(InferenceEngine, LoadFailsForMissingFile) {
    nexussim::ai::InferenceEngine engine;
    EXPECT_FALSE(engine.load("does_not_exist.onnx"));
    EXPECT_FALSE(engine.is_loaded());
}

TEST(InferenceEngine, LoadFailsForNonModel) {
    auto path = fs::temp_directory_path() / "not_a_model.onnx";
    { std::ofstream f(path); f << "garbage"; }
    nexussim::ai::InferenceEngine engine;
    EXPECT_FALSE(engine.load(path.string()));
}

TEST(InferenceEngine, LoadReportsModelShape) {
    nexussim::ai::InferenceEngine engine;
    ASSERT_TRUE(engine.load(fixture_path()));
    EXPECT_TRUE(engine.is_loaded());
    EXPECT_EQ(engine.obs_dim(), 11u);
    EXPECT_EQ(engine.num_actions(), 2u);
}

TEST(InferenceEngine, BatchInferReturnsOneActionPerRow) {
    nexussim::ai::InferenceEngine engine;
    ASSERT_TRUE(engine.load(fixture_path()));
    for (size_t batch : {1u, 4u, 9u}) {
        auto actions = engine.batch_infer(make_batch(batch, 1.0f), batch);
        ASSERT_EQ(actions.size(), batch);
        for (int a : actions) {
            EXPECT_GE(a, 0);
            EXPECT_LT(a, 2);
        }
    }
}

TEST(InferenceEngine, InferenceIsDeterministic) {
    nexussim::ai::InferenceEngine engine;
    ASSERT_TRUE(engine.load(fixture_path()));
    auto first = engine.batch_infer(make_batch(5, 2.0f), 5);
    auto second = engine.batch_infer(make_batch(5, 2.0f), 5);
    EXPECT_EQ(first, second);
}

TEST(InferenceEngine, WrongInputSizeReturnsEmpty) {
    nexussim::ai::InferenceEngine engine;
    ASSERT_TRUE(engine.load(fixture_path()));
    auto too_few = engine.batch_infer(std::vector<float>(10, 0.5f), 1);
    EXPECT_TRUE(too_few.empty());
    auto wrong_batch = engine.batch_infer(std::vector<float>(22, 0.5f), 4);
    EXPECT_TRUE(wrong_batch.empty());
}
