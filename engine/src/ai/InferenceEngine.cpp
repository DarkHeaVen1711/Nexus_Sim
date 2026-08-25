// InferenceEngine implementation. The ONNX Runtime backend is compiled only
// when NEXUS_HAS_ONNX is defined (ENABLE_ONNX=ON); otherwise load() fails
// gracefully so callers fall back to Webster timing (Phase 8.5).

#include "InferenceEngine.h"
#include <iostream>

#if !defined(NEXUS_HAS_ONNX)

namespace nexussim {
namespace ai {

// Empty Impl keeps the PIMPL member well-formed without ONNX Runtime.
struct InferenceEngine::Impl {};

InferenceEngine::InferenceEngine() = default;
InferenceEngine::~InferenceEngine() = default;
InferenceEngine::InferenceEngine(InferenceEngine&&) noexcept = default;
InferenceEngine& InferenceEngine::operator=(InferenceEngine&&) noexcept = default;

bool InferenceEngine::load(const std::string& model_path) {
    std::cerr << "[InferenceEngine] ONNX support not compiled in; cannot load "
              << model_path << "\n";
    return false;
}

std::vector<int> InferenceEngine::batch_infer(const std::vector<float>&,
                                              size_t) {
    return {};
}

} // namespace ai
} // namespace nexussim

#else
#error "ONNX backend wired in an upcoming commit"
#endif
