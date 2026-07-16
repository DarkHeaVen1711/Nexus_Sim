#pragma once

#include <iostream>
#include <thread>
#include <vector>
#include <mutex>
#include "uWebSockets/App.h"
#include "agent_delta_generated.h" // FlatBuffers generated header

namespace nexussim {
namespace network {

class WebSocketServer {
public:
    WebSocketServer(int port) : port_(port) {}

    void start() {
        thread_ = std::thread([this]() {
            uWS::App().ws<int>("/*", {
                .compression = uWS::SHARED_COMPRESSOR,
                .maxPayloadLength = 16 * 1024 * 1024,
                .idleTimeout = 120,
                .open = [this](auto *ws) {
                    std::lock_guard<std::mutex> lock(clients_mutex_);
                    clients_.push_back(ws);
                    std::cout << "Client connected\n";
                },
                .message = [](auto *ws, std::string_view message, uWS::OpCode opCode) {
                    // Handle LOD bounds from client if needed
                },
                .close = [this](auto *ws, int code, std::string_view message) {
                    std::lock_guard<std::mutex> lock(clients_mutex_);
                    auto it = std::find(clients_.begin(), clients_.end(), ws);
                    if (it != clients_.end()) {
                        clients_.erase(it);
                    }
                    std::cout << "Client disconnected\n";
                }
            }).listen(port_, [this](auto *listen_socket) {
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
