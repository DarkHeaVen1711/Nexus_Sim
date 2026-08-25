// InferenceEngine implementation. The ONNX Runtime backend is compiled only
// when NEXUS_HAS_ONNX is defined (ENABLE_ONNX=ON); otherwise load() fails
// gracefully so callers fall back to Webster timing (Phase 8.5).

#include "InferenceEngine.h"
#include <iostream>

#if defined(NEXUS_HAS_ONNX)
#define WIN32_LEAN_AND_MEAN
#include <onnxruntime_cxx_api.h>
#include <optional>
#ifdef _WIN32
#include <windows.h>
#endif

namespace nexussim {
namespace ai {

// ORTCHAR_T is wchar_t on Windows and char elsewhere; model paths arrive as
// UTF-8 std::string.
static std::basic_string<ORTCHAR_T> to_ort_path(const std::string& path) {
#ifdef _WIN32
    if (path.empty()) return {};
    int size = MultiByteToWideChar(CP_UTF8, 0, path.c_str(),
                                   static_cast<int>(path.size()),
                                   nullptr, 0);
    std::wstring wide(static_cast<size_t>(size), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, path.c_str(), static_cast<int>(path.size()),
                        &wide[0], size);
    return wide;
#else
    return path;
#endif
}

struct InferenceEngine::Impl {
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "NexusSim"};
    std::optional<Ort::Session> session;
};

InferenceEngine::InferenceEngine() = default;
InferenceEngine::~InferenceEngine() = default;
InferenceEngine::InferenceEngine(InferenceEngine&&) noexcept = default;
InferenceEngine& InferenceEngine::operator=(InferenceEngine&&) noexcept = default;

bool InferenceEngine::load(const std::string& model_path) {
    loaded_ = false;
    impl_.reset();
    obs_dim_ = 0;
    num_actions_ = 0;
    try {
        impl_ = std::make_unique<Impl>();
        Ort::SessionOptions options;
        options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        options.SetIntraOpNumThreads(1); // must not fight the sim thread pool
        impl_->session.emplace(impl_->env,
                               to_ort_path(model_path).c_str(),
                               options);

        auto input_shape = impl_->session->GetInputTypeInfo(0)
                               .GetTensorTypeAndShapeInfo().GetShape();
        auto output_shape = impl_->session->GetOutputTypeInfo(0)
                                .GetTensorTypeAndShapeInfo().GetShape();
        if (input_shape.size() != 2 || output_shape.size() != 2
            || input_shape[1] < 1 || output_shape[1] < 1) {
            // Symbolic feature dims cannot be validated against callers; the
            // exporter pins dim 1 (only batch is dynamic).
            std::cerr << "[InferenceEngine] expected [batch, features] "
                         "tensors with concrete feature dims: "
                      << model_path << "\n";
            return false;
        }
        obs_dim_ = static_cast<size_t>(input_shape[1]);
        num_actions_ = static_cast<size_t>(output_shape[1]);
        loaded_ = true;
        std::cout << "[InferenceEngine] loaded " << model_path
                  << " (obs_dim=" << obs_dim_
                  << ", actions=" << num_actions_ << ")\n";
        return true;
    } catch (const Ort::Exception& e) {
        std::cerr << "[InferenceEngine] failed to load " << model_path
                  << ": " << e.what() << "\n";
        loaded_ = false;
        impl_.reset();
        return false;
    }
}

std::vector<int> InferenceEngine::batch_infer(
    const std::vector<float>& observations, size_t batch_size) {
    if (!loaded_ || !impl_ || !impl_->session) return {};
    if (observations.size() != batch_size * obs_dim_) {
        std::cerr << "[InferenceEngine] input size "
                  << observations.size() << " != batch " << batch_size
                  << " x obs_dim " << obs_dim_ << "\n";
        return {};
    }

    try {
        Ort::MemoryInfo mem = Ort::MemoryInfo::CreateCpu(
            OrtArenaAllocator, OrtMemTypeDefault);
        int64_t dims[2] = {static_cast<int64_t>(batch_size),
                           static_cast<int64_t>(obs_dim_)};
        Ort::Value tensor = Ort::Value::CreateTensor<float>(
            mem, const_cast<float*>(observations.data()),
            observations.size(), dims, 2);

        Ort::AllocatorWithDefaultOptions alloc;
        Ort::AllocatedStringPtr input_name =
            impl_->session->GetInputNameAllocated(0, alloc);
        Ort::AllocatedStringPtr output_name =
            impl_->session->GetOutputNameAllocated(0, alloc);
        const char* input_names[] = {input_name.get()};
        const char* output_names[] = {output_name.get()};

        auto outputs = impl_->session->Run(Ort::RunOptions{nullptr},
                                           input_names, &tensor, 1,
                                           output_names, 1);
        float* logits = outputs[0].GetTensorMutableData<float>();

        std::vector<int> actions(batch_size);
        const int64_t n_actions = static_cast<int64_t>(num_actions_);
        for (size_t b = 0; b < batch_size; ++b) {
            const float* row = logits + b * n_actions;
            int best = 0;
            for (int64_t a = 1; a < n_actions; ++a)
                if (row[a] > row[best]) best = static_cast<int>(a);
            actions[b] = best;
        }
        return actions;
    } catch (const Ort::Exception& e) {
        std::cerr << "[InferenceEngine] inference failed: " << e.what() << "\n";
        return {};
    }
}

} // namespace ai
} // namespace nexussim

#else
// !NEXUS_HAS_ONNX: stub so the engine builds without ONNX support. The
// empty Impl keeps the PIMPL member well-formed.
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

#endif
