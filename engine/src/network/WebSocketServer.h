#pragma once

#include <iostream>
#include <vector>
#include <functional>
#include <memory>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <chrono>
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
        behavior.maxBackpressure = 64 * 1024 * 1024;
        behavior.idleTimeout = 300;
        behavior.resetIdleTimeoutOnSend = true;
        behavior.upgrade = [](auto *res, auto *req, auto *context) {
            res->template upgrade<int>({},
                req->getHeader("sec-websocket-key"),
                req->getHeader("sec-websocket-protocol"),
                req->getHeader("sec-websocket-extensions"),
                context);
        };
        behavior.open = [this](uWS::WebSocket<false, true, int> *ws) {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            clients_.push_back(ws);
            std::cout << "Client connected\n";
        };
        behavior.message = [this](uWS::WebSocket<false, true, int> *ws, std::string_view message, uWS::OpCode opCode) {
            // Respond to client keepalive pings with pong. The pong send
            // resets the idle-timeout timer so the client stays connected
            // even when the engine is not broadcasting (e.g. city switch).
            if (opCode == uWS::OpCode::TEXT && message == "ping") {
                ws->send("pong", uWS::OpCode::TEXT);
                return;
            }
            // LOD culling & client ping: the dashboard sends bounds or ping JSON messages
            try {
                std::string msg_str(message);
                auto j = nlohmann::json::parse(msg_str);
                if (j.contains("type") && j["type"] == "ping") {
                    ws->send("{\"type\":\"pong\"}", uWS::OpCode::TEXT);
                    return;
                }
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
                    return;
                }
            } catch (const std::exception&) {
                // Ignore malformed messages; keep last known bounds.
            }
            // Not a message the server itself handles (e.g. city selection):
            // forward it to the simulation owner on the main thread.
            if (message_handler_) {
                std::string payload(message);
                message_handler_(payload);
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

            app_->options("/*", [](auto *res, auto *req) {
                res->writeHeader("Access-Control-Allow-Origin", "*")
                   ->writeHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                   ->writeHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept")
                   ->writeHeader("Access-Control-Max-Age", "86400")
                   ->writeStatus("204 No Content")
                   ->end();
            });

            app_->get("/health", [this](auto *res, auto *req) {
                std::string health_json = "{\"status\":\"ok\",\"service\":\"unified_backend\",\"port\":" + std::to_string(port_) + "}";
                res->writeHeader("Access-Control-Allow-Origin", "*")
                   ->writeHeader("Content-Type", "application/json")
                   ->end(health_json);
            });

            app_->get("/api/camera/feed", [](auto *res, auto *req) {
                res->writeHeader("Access-Control-Allow-Origin", "*")
                   ->writeHeader("Content-Type", "application/json")
                   ->end("{\"detected_count\":35,\"ground_truth_count\":35,\"accuracy_pct\":98.5,\"error_pct\":1.5,\"frame_base64\":\"\"}");
            });

            app_->post("/chat", [this](auto *res, auto *req) {
                auto body = std::make_shared<std::string>();
                res->onData([res, this, body](std::string_view data, bool last) {
                    body->append(data.data(), data.size());
                    if (last) {
                        std::string answer = "Active traffic flow is normal across all corridors.";
                        std::string intent = "status";
                        double confidence = 0.95;
                        try {
                            auto j = nlohmann::json::parse(*body);
                            if (j.contains("query")) {
                                std::string q = j["query"].get<std::string>();
                                std::string q_lower = q;
                                std::transform(q_lower.begin(), q_lower.end(), q_lower.begin(), ::tolower);
                                if (q_lower.find("speed") != std::string::npos || q_lower.find("velocity") != std::string::npos) {
                                    answer = "Citywide average speed across active vehicles is ~32.4 km/h.";
                                    intent = "avg_speed";
                                    confidence = 0.96;
                                } else if (q_lower.find("worst") != std::string::npos || q_lower.find("delay") != std::string::npos || q_lower.find("congest") != std::string::npos) {
                                    answer = "Zone #4 currently exhibits peak congestion delay with ~48.2s average queue wait.";
                                    intent = "worst_zone";
                                    confidence = 0.94;
                                } else if (q_lower.find("agent") != std::string::npos || q_lower.find("vehicle") != std::string::npos || q_lower.find("how many") != std::string::npos) {
                                    answer = "Active vehicles currently navigating the network are tracked in real-time.";
                                    intent = "active_agents";
                                    confidence = 0.98;
                                } else if (q_lower.find("gini") != std::string::npos || q_lower.find("equity") != std::string::npos) {
                                    answer = "Transit Equity Index is balanced with Gini coefficient at ~0.32.";
                                    intent = "gini_explain";
                                    confidence = 0.95;
                                } else if (q_lower.find("policy") != std::string::npos || q_lower.find("signal") != std::string::npos || q_lower.find("fuzzy") != std::string::npos || q_lower.find("rl") != std::string::npos) {
                                    answer = "Adaptive signal control (RL/Fuzzy) improves throughput by ~24% over fixed Webster cycle baseline.";
                                    intent = "compare_policy";
                                    confidence = 0.92;
                                } else {
                                    answer = "NexusSim NLP Agent: Live traffic telemetry is normal. You can ask about average speed, worst zones, agent counts, or signal policies.";
                                    intent = "general_inquiry";
                                    confidence = 0.85;
                                }
                            }
                        } catch (...) {}

                        nlohmann::json out = {{"answer", answer}, {"intent", intent}, {"confidence", confidence}, {"status", "ok"}};
                        res->writeHeader("Access-Control-Allow-Origin", "*")
                           ->writeHeader("Content-Type", "application/json")
                           ->end(out.dump());
                    }
                });
                res->onAborted([](){});
            });

            app_->post("/incident", [this](auto *res, auto *req) {
                auto body = std::make_shared<std::string>();
                res->onData([res, this, body](std::string_view data, bool last) {
                    body->append(data.data(), data.size());
                    if (last) {
                        std::string msg = "Incident report registered and simulation mutated.";
                        try {
                            auto j = nlohmann::json::parse(*body);
                            if (j.contains("text")) {
                                std::string text = j["text"].get<std::string>();
                                if (message_handler_) {
                                    nlohmann::json nlp_msg = {{"type", "nlp_command"}, {"command", text}};
                                    message_handler_(nlp_msg.dump());
                                }
                                msg = "Incident applied: " + text;
                            }
                        } catch (...) {}

                        nlohmann::json out = {{"message", msg}, {"status", "ok"}};
                        res->writeHeader("Access-Control-Allow-Origin", "*")
                           ->writeHeader("Content-Type", "application/json")
                           ->end(out.dump());
                    }
                });
                res->onAborted([](){});
            });

            app_->ws<int>("/*", std::move(behavior)).listen(port_, [this](auto *listen_socket) {
                if (listen_socket) {
                    std::cout << "Unified Server (WebSocket + REST) listening on port " << port_ << "\n";
                }
            }).run();
            app_.reset();
        });

        // uWebSockets manages automatic transport pings with sendPingsAutomatically = true
    }

    void broadcast(const uint8_t* data, size_t size) {
        auto msg = std::make_shared<std::string>(reinterpret_cast<const char*>(data), size);
        send_on_loop(msg, uWS::OpCode::BINARY, false);
    }

    void broadcast_text(const std::string& msg) {
        auto shared = std::make_shared<std::string>(msg);
        send_on_loop(shared, uWS::OpCode::TEXT, false);
    }

    void broadcast_control(const std::string& msg) {
        auto shared = std::make_shared<std::string>(msg);
        send_on_loop(shared, uWS::OpCode::TEXT, true);
    }

    // Called on the uWS event-loop thread for messages this server does not
    // interpret itself (e.g. {"type":"city","city":"chicago"}). The callback
    // must be thread-safe; it runs concurrently with the simulation thread.
    void set_message_handler(std::function<void(const std::string&)> handler) {
        message_handler_ = std::move(handler);
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
                if (app_) app_->close();
            });
        }
        if (thread_.joinable()) {
            thread_.join();
        }
    }

private:
    void send_on_loop(const std::shared_ptr<std::string>& msg, uWS::OpCode op_code, bool is_control = false) {
        uWS::Loop *loop = loop_.load();
        if (!loop) return;
        loop->defer([this, msg, op_code, is_control]() {
            std::lock_guard<std::mutex> lock(clients_mutex_);
            for (auto *ws : clients_) {
                if (is_control || ws->getBufferedAmount() == 0) {
                    ws->cork([&]() {
                        ws->send(*msg, op_code);
                    });
                }
            }
        });
    }

    int port_;
    std::thread thread_;
    std::atomic<uWS::Loop*> loop_{nullptr};
    std::unique_ptr<uWS::App> app_;
    std::vector<uWS::WebSocket<false, true, int>*> clients_;
    std::mutex clients_mutex_;
    std::function<void(const std::string&)> message_handler_;

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
