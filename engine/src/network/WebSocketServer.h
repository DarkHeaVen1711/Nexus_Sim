#pragma once

#include <iostream>
#include <vector>
#include <functional>
#include <memory>
#include <atomic>
#include "../mingw_thread_compat.h"
#include "App.h"

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
        behavior.compression = uWS::SHARED_COMPRESSOR;
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
        behavior.message = [](uWS::WebSocket<false, true, int> *ws, std::string_view message, uWS::OpCode opCode) {
            // Handle LOD bounds from client if needed
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
};

} // namespace network
} // namespace nexussim
