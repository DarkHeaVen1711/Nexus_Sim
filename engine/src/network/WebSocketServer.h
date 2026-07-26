#pragma once

#include <iostream>
#include <vector>
#include <functional>
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
        behavior.open = [this](uWS::WebSocket<false, true, int> *ws) {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            clients_.push_back(ws);
            std::cout << "Client connected\n";
        };
        behavior.message = [](uWS::WebSocket<false, true, int> *ws, std::string_view message, uWS::OpCode opCode) {
            // Handle LOD bounds from client if needed
        };
        behavior.close = [this](uWS::WebSocket<false, true, int> *ws, int code, std::string_view message) {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            auto it = std::find(clients_.begin(), clients_.end(), ws);
            if (it != clients_.end()) {
                clients_.erase(it);
            }
            std::cout << "Client disconnected\n";
        };

        thread_ = std::thread([this, behavior = std::move(behavior)]() mutable {
            uWS::App().ws<int>("/*", std::move(behavior)).listen(port_, [this](auto *listen_socket) {
                if (listen_socket) {
                    std::cout << "WebSocket server listening on port " << port_ << "\n";
                }
            }).run();
        });
    }

    void broadcast(const uint8_t* data, size_t size) {
        std::lock_guard<std::mutex> lock(clients_mutex_);
        std::string_view payload(reinterpret_cast<const char*>(data), size);
        for (auto *ws : clients_) {
            ws->send(payload, uWS::OpCode::BINARY);
        }
    }

    void broadcast_text(const std::string& msg) {
        std::lock_guard<std::mutex> lock(clients_mutex_);
        for (auto *ws : clients_) {
            ws->send(msg, uWS::OpCode::TEXT);
        }
    }

    ~WebSocketServer() {
        if (thread_.joinable()) {
            thread_.detach(); // In a real app we should gracefully shut down the uWS loop
        }
    }

private:
    int port_;
    std::thread thread_;
    std::vector<uWS::WebSocket<false, true, int>*> clients_;
    std::mutex clients_mutex_;
};

} // namespace network
} // namespace nexussim
