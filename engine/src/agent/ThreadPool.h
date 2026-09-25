#pragma once
#include <vector>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <future>
#include <atomic>
#include <algorithm>

namespace nexussim {

class ThreadPool {
public:
    explicit ThreadPool(size_t threads = std::max(1u, std::thread::hardware_concurrency()))
        : stop_(false), active_tasks_(0) {
        for (size_t i = 0; i < threads; ++i) {
            workers_.emplace_back([this]() {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex_);
                        cv_task_.wait(lock, [this]() {
                            return stop_ || !tasks_.empty();
                        });
                        if (stop_ && tasks_.empty()) return;
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex_);
                        --active_tasks_;
                        if (active_tasks_ == 0 && tasks_.empty()) {
                            cv_done_.notify_all();
                        }
                    }
                }
            });
        }
    }

    ~ThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            stop_ = true;
        }
        cv_task_.notify_all();
        for (auto& worker : workers_) {
            if (worker.joinable()) worker.join();
        }
    }

    size_t size() const { return workers_.size(); }

    template <typename F>
    void parallel_for(size_t start, size_t end, F&& func, size_t min_chunk = 64) {
        if (start >= end) return;
        size_t total = end - start;
        size_t nthreads = workers_.size();
        if (nthreads <= 1 || total <= min_chunk) {
            for (size_t i = start; i < end; ++i) func(i);
            return;
        }

        size_t chunk_size = std::max(min_chunk, (total + nthreads - 1) / nthreads);
        size_t num_chunks = (total + chunk_size - 1) / chunk_size;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            active_tasks_ += num_chunks;
            for (size_t c = 0; c < num_chunks; ++c) {
                size_t c_start = start + c * chunk_size;
                size_t c_end = std::min(c_start + chunk_size, end);
                tasks_.emplace([c_start, c_end, &func]() {
                    for (size_t i = c_start; i < c_end; ++i) {
                        func(i);
                    }
                });
            }
        }
        cv_task_.notify_all();

        std::unique_lock<std::mutex> lock(queue_mutex_);
        cv_done_.wait(lock, [this]() {
            return active_tasks_ == 0 && tasks_.empty();
        });
    }

private:
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex queue_mutex_;
    std::condition_variable cv_task_;
    std::condition_variable cv_done_;
    size_t active_tasks_;
    bool stop_;
};

} // namespace nexussim
