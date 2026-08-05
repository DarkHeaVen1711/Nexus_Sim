#pragma once

#include <iostream>
#include <vector>
#include <functional>
#include <memory>
#include <atomic>
#include <mutex>
#include "../mingw_thread_compat.h"
#include "App.h"
#include <nlohmann/json.hpp>

#if !(defined(_WIN32) && !defined(_GLIBCXX_HAS_GTHREADS))
#include <mutex>
#endif

#include "agent_delta_generated.h" // FlatBuffers generated header

namespace nexussim {
namespace network {

class WebSocketServer {
public:
    WebSocketServer(int port) : port_(port) {}

    void start() {
        uWS::TemplatedApp<false>::WebSocketBehavior<int> behavior;
        // Compression (permessage-deflate) is disabled: the SHARED_COMPRESSOR
        // stream is a known source of "WebSocket Protocol Error 1002" closes
        // from browsers (corrupt deflate stream on MinGW/libuv builds). The
        // dashboard payload is small text JSON, so compression buys nothing.
        behavior.compression = uWS::DISABLED;
        behavior.maxPayloadLength = 16 * 1024 * 1024;
        behavior.idleTimeout = 120;
        // The server streams continuously; reset the idle timer on every send so
        // passive (never-sending) dashboard clients are not dropped by the timeout.
        behavior.resetIdleTimeoutOnSend = true;
        behavior.open = [this](uWS::WebSocket<false, true, int> *ws) {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            clients_.push_back(ws);
            std::cout << "Client connected\n";
        };
        behavior.message = [this](uWS::WebSocket<false, true, int> *ws, std::string_view message, uWS::OpCode opCode) {
            // LOD culling: the dashboard sends its current viewport bounds and
            // the engine only includes agents inside them in the next broadcast.
            try {
                auto j = nlohmann::json::parse(message);
                if (j.contains("type") && j["type"] == "bounds") {
                    std::lock_guard<std::mutex> lock(bounds_mutex_);
                    if (j.contains("clear") && j["clear"].get<bool>()) {
                        bounds_.set = false;
                    } else {
                        bounds_ = {true,
                                   j.at("min_lat").get<double>(),
                                   j.at("min_lon").get<double>(),
                                   j.at("max_lat").get<double>(),
                                   j.at("max_lon").get<double>()};
                    }
                }
            } catch (const std::exception&) {
                // Ignore malformed messages; keep last known bounds.
            }
        };
        behavior.close = [this](uWS::WebSocket<false, true, int> *ws, int code, std::string_view message) {
            {
                std::lock_guard<std::mutex> lock(clients_mutex_);
                auto it = std::find(clients_.begin(), clients_.end(), ws);
                if (it != clients_.end()) {
                    clients_.erase(it);
                }
            }
            std::cout << "Client disconnected code=" << code
                      << " reason=\"" << std::string(message) << "\"\n";
        };

        thread_ = std::thread([this, behavior = std::move(behavior)]() mutable {
            uWS::Loop *loop = uWS::Loop::get();
            loop_ = loop;
            app_ = std::make_unique<uWS::App>();
            app_->ws<int>("/*", std::move(behavior)).listen(port_, [this](auto *listen_socket) {
                if (listen_socket) {
                    std::cout << "WebSocket server listening on port " << port_ << "\n";
                }
            }).run();
            app_.reset();
        });
    }

    void broadcast(const uint8_t* data, size_t size) {
        auto msg = std::make_shared<std::string>(reinterpret_cast<const char*>(data), size);
        send_on_loop(msg, uWS::OpCode::BINARY);
    }

    void broadcast_text(const std::string& msg) {
        auto shared = std::make_shared<std::string>(msg);
        send_on_loop(shared, uWS::OpCode::TEXT);
    }

    // Returns false when no viewport bounds have been received (broadcast all).
    bool get_bounds(double& min_lat, double& min_lon,
                    double& max_lat, double& max_lon) const {
        std::lock_guard<std::mutex> lock(bounds_mutex_);
        if (!bounds_.set) return false;
        min_lat = bounds_.min_lat;
        min_lon = bounds_.min_lon;
        max_lat = bounds_.max_lat;
        max_lon = bounds_.max_lon;
        return true;
    }

    ~WebSocketServer() {
        // Gracefully stop the uWS loop so no queued callbacks outlive this object.
        // close() must run on the event-loop thread; deferring it is thread-safe.
        uWS::Loop *loop = loop_.load();
        if (loop) {
            loop->defer([this]() {
                app_->close();
            });
        }
        if (thread_.joinable()) {
            thread_.join();
        }
    }

private:
    // uWS is not thread-safe: ws->send() must only be called from the event-loop
    // thread. Queue sends and let the loop dispatch them via Loop::defer().
    void send_on_loop(const std::shared_ptr<std::string>& msg, uWS::OpCode op_code) {
        uWS::Loop *loop = loop_.load();
        if (!loop) return;
        loop->defer([this, msg, op_code]() {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            for (auto *ws : clients_) {
                ws->send(*msg, op_code);
            }
        });
    }

    int port_;
    std::thread thread_;
    std::atomic<uWS::Loop*> loop_{nullptr};
    std::unique_ptr<uWS::App> app_;
    std::vector<uWS::WebSocket<false, true, int>*> clients_;
    std::mutex clients_mutex_;

    struct Bounds {
        bool set = false;
        double min_lat = 0.0;
        double min_lon = 0.0;
        double max_lat = 0.0;
        double max_lon = 0.0;
    };
    mutable std::mutex bounds_mutex_;
    Bounds bounds_;
};

} // namespace network
} // namespace nexussim
