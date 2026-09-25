#pragma once
#include <chrono>
#include <thread>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <windows.h>
#endif

namespace nexussim {
namespace core {

class FramePacer {
public:
    explicit FramePacer(double target_fps = 60.0) {
        set_target_fps(target_fps);
        reset();
    }

    void set_target_fps(double target_fps) {
        if (target_fps <= 0.0) target_fps = 60.0;
        frame_interval_us_ = static_cast<int64_t>(1000000.0 / target_fps);
    }

    void reset() {
        next_frame_time_ = std::chrono::high_resolution_clock::now();
    }

    void pace() {
        if (frame_interval_us_ <= 0) return;

        next_frame_time_ += std::chrono::microseconds(frame_interval_us_);
        auto now = std::chrono::high_resolution_clock::now();

        if (now >= next_frame_time_) {
            // Frame overrun: don't let backlog accumulate indefinitely
            if (std::chrono::duration_cast<std::chrono::microseconds>(now - next_frame_time_).count() > frame_interval_us_ * 2) {
                next_frame_time_ = now;
            }
            return;
        }

        auto remaining_us = std::chrono::duration_cast<std::chrono::microseconds>(next_frame_time_ - now).count();

        // Coarse sleep if more than 3ms remain
        if (remaining_us > 3000) {
            int sleep_ms = static_cast<int>((remaining_us - 2000) / 1000);
            if (sleep_ms > 0) {
#ifdef _WIN32
                Sleep(sleep_ms);
#else
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
#endif
            }
        }

        // Fine-grained spin-yield for remainder
        while (std::chrono::high_resolution_clock::now() < next_frame_time_) {
            std::this_thread::yield();
        }
    }

private:
    int64_t frame_interval_us_{16666}; // 60 FPS = ~16.666 ms
    std::chrono::high_resolution_clock::time_point next_frame_time_;
};

} // namespace core
} // namespace nexussim
