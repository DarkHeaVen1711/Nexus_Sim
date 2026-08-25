#pragma once
// InferenceEngine: ONNX Runtime wrapper for the exported MAPPO signal policy
// (Phase 8.3, US-E04). Loads a policy.onnx produced by ml/export and exposes
// batch_infer() -> one argmax action per observation row.
//
// The ONNX Runtime dependency is optional at build time (ENABLE_ONNX); when
// the engine is compiled without it, load() fails gracefully so callers fall
// back to Webster timing.
//
// The implementation is hidden behind a PIMPL so ORT headers stay out of the
// simulation headers and the session handle is never copied.

#include <memory>
#include <string>
#include <vector>

namespace nexussim {
namespace ai {

class InferenceEngine {
public:
    InferenceEngine();
    ~InferenceEngine();
    InferenceEngine(InferenceEngine&& other) noexcept;
    InferenceEngine& operator=(InferenceEngine&& other) noexcept;

    // Load an .onnx model. Returns false on failure (missing file, bad
    // graph, or no ONNX support compiled in) with the reason on stderr.
    bool load(const std::string& model_path);

    bool is_loaded() const { return loaded_; }

    // Per-row observation dimension reported by the loaded model.
    size_t obs_dim() const { return obs_dim_; }

    // Number of actions per observation reported by the loaded model.
    size_t num_actions() const { return num_actions_; }

    // Run greedy inference over a batch of observations laid out row-major
    // as [batch_size][obs_dim()]. Returns the argmax action index per row,
    // or an empty vector when not loaded / input size mismatches / ORT run
    // fails. Thread-safe for concurrent calls on distinct instances; a
    // single session also tolerates concurrent Run() calls.
    std::vector<int> batch_infer(const std::vector<float>& observations,
                                 size_t batch_size);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    size_t obs_dim_ = 0;
    size_t num_actions_ = 0;
    bool loaded_ = false;
};

} // namespace ai
} // namespace nexussim
