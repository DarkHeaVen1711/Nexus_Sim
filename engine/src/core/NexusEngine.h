#pragma once
#include <string>
#include <memory>
#include <mutex>
#include <atomic>
#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <vector>
#include <csignal>
#include "CliConfig.h"
#include "Metrics.h"
#include "Pacer.h"
#include "../graph/GraphLoader.h"
#include "../agent/Simulation.h"
#include "../agent/NLPQueryParser.h"
#include "../ai/InferenceEngine.h"
#include "../network/WebSocketServer.h"
#include <nlohmann/json.hpp>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <windows.h>
#endif

namespace nexussim {

class NexusEngine {
public:
    explicit NexusEngine(const EngineConfig& cfg)
        : config_(cfg) {}

    ~NexusEngine() {
        stop();
    }

    void stop() {
        running_ = false;
    }

    void run() {
        running_ = true;
        setup_signals();

        if (!config_.policy_path.empty()) {
            load_policy(config_.policy_path);
        }

        std::cout << "Signal mode: " << (policy_ ? "rl" : "webster") << "\n";

        if (!config_.no_ws) {
            start_websocket_server();
        }

        if (config_.fast) {
            run_city_session(config_.city);
            std::cout << "Shutting down.\n";
            return;
        }

        std::string current_city;
        while (running_) {
            if (current_city.empty()) {
                std::cout << "Engine ready. Open the dashboard menu and pick a city to start.\n";
                while (running_) {
                    std::string req = take_city_request();
                    if (!req.empty()) {
                        current_city = req;
                        break;
                    }
#ifdef _WIN32
                    Sleep(50);
#else
                    std::this_thread::sleep_for(std::chrono::milliseconds(50));
#endif
                }
                if (!running_) break;
            }

            set_paused(false);
            run_city_session(current_city);

            if (!running_) break;

            ReloadKind reload = take_reload();
            std::string next_city = take_city_request();
            if (!next_city.empty()) {
                current_city = next_city;
                std::cout << "Switching to " << current_city << "...\n";
                continue;
            }

            if (reload == ReloadKind::Restart) {
                std::cout << "Restarting " << current_city << " from scratch...\n";
                continue;
            }

            set_current_city("");
            if (ws_server_) {
                ws_server_->broadcast_control("{\"type\":\"stopped\"}");
            }
            std::cout << "Simulation stopped; engine idling.\n";
            current_city.clear();
        }

        std::cout << "Shutting down.\n";
    }

private:
    enum class ReloadKind { None, Restart, Stop };

    struct ControlState {
        std::mutex m;
        bool paused = false;
        ReloadKind reload = ReloadKind::None;
        std::string city_request;
        std::string current_city;
        std::string policy_switch;
        int64_t policy_switch_intersection = -1;
        bool policy_switch_pending = false;
        std::vector<NLPCommand> pending_whatif;
    };

    EngineConfig config_;
    ControlState ctl_;
    std::atomic<bool> running_{false};
    std::unique_ptr<network::WebSocketServer> ws_server_;
    std::unique_ptr<ai::InferenceEngine> policy_;

    static inline NexusEngine* s_instance = nullptr;

    static void signal_handler(int) {
        if (s_instance) {
            s_instance->running_ = false;
        }
    }

    void setup_signals() {
        s_instance = this;
        std::signal(SIGINT, signal_handler);
        std::signal(SIGTERM, signal_handler);
    }

    static std::string resolve_file(const std::string& rel_path) {
        std::vector<std::string> prefixes = {"", "../", "../../"};
        for (const auto& pre : prefixes) {
            std::string candidate = pre + rel_path;
            std::ifstream test(candidate);
            if (test.good()) return candidate;
        }
        return rel_path;
    }

    static std::string city_data_path(const std::string& city, const std::string& file) {
        std::vector<std::string> prefixes = {"data/", "../data/", "../../data/"};
        for (const auto& pre : prefixes) {
            std::string candidate = pre + city + "/" + file;
            std::ifstream test(candidate);
            if (test.good()) return candidate;
        }
        return "data/" + city + "/" + file;
    }

    void load_policy(const std::string& policy_path) {
        if (policy_path.empty()) return;
        std::string resolved = resolve_file(policy_path);
        auto pol = std::make_unique<ai::InferenceEngine>();
        if (pol->load(resolved)) {
            std::cout << "AI policy loaded: " << resolved << " (obs_dim="
                      << pol->obs_dim() << ", actions=" << pol->num_actions() << ")\n";
            policy_ = std::move(pol);
        } else {
            std::cerr << "WARNING: failed to load policy '" << policy_path
                      << "'; falling back to Webster signal timing\n";
        }
    }

    double compute_peak_hourly_demand(const std::string& od_path) {
        std::ifstream f(od_path);
        if (!f.good()) return 0.0;
        try {
            nlohmann::json j;
            f >> j;
            double peak = 0.0;
            std::vector<double> hourly_sum(24, 0.0);
            for (const auto& e : j["od"]) {
                const auto& hourly = e["hourly"];
                for (size_t h = 0; h < hourly.size() && h < 24; ++h)
                    hourly_sum[h] += hourly[h].get<double>();
            }
            for (double s : hourly_sum)
                if (s > peak) peak = s;
            return peak;
        } catch (...) {
            return 0.0;
        }
    }

    void handle_ws_message(const std::string& payload) {
        try {
            auto j = nlohmann::json::parse(payload);
            if (!j.contains("type")) return;
            std::string type = j["type"].get<std::string>();

            if (type == "city" && j.contains("city")) {
                std::string target = j["city"].get<std::string>();
                std::lock_guard<std::mutex> lock(ctl_.m);
                ctl_.city_request = target;
            } else if (type == "get_city") {
                std::string c = get_current_city();
                std::string city_json = c.empty() ? "null" : "\"" + c + "\"";
                if (ws_server_) {
                    ws_server_->broadcast_control("{\"type\":\"city_loaded\",\"city\":" + city_json + "}");
                }
            } else if (type == "pause") {
                set_paused(true);
                if (ws_server_) ws_server_->broadcast_control("{\"type\":\"paused\"}");
            } else if (type == "resume") {
                set_paused(false);
                if (ws_server_) ws_server_->broadcast_control("{\"type\":\"resumed\"}");
            } else if (type == "restart") {
                std::lock_guard<std::mutex> lock(ctl_.m);
                ctl_.reload = ReloadKind::Restart;
            } else if (type == "reset" || type == "stop") {
                std::lock_guard<std::mutex> lock(ctl_.m);
                ctl_.reload = ReloadKind::Stop;
            } else if (type == "policy_switch") {
                if (!j.contains("policy")) return;
                std::string pol = j["policy"].get<std::string>();
                if (pol == "ai") pol = "rl";
                if (pol != "webster" && pol != "rl" && pol != "fuzzy") {
                    if (ws_server_) {
                        ws_server_->broadcast_control(
                            "{\"type\":\"policy_switched\",\"ok\":false,\"error\":\"unknown policy '" + pol + "'\"}");
                    }
                    return;
                }
                int64_t target_id = -1;
                if (j.contains("intersection_id") && j["intersection_id"].is_number_integer()) {
                    target_id = j["intersection_id"].get<int64_t>();
                }
                std::lock_guard<std::mutex> lock(ctl_.m);
                ctl_.policy_switch = pol;
                ctl_.policy_switch_intersection = target_id;
                ctl_.policy_switch_pending = true;
            } else if (type == "nlp_command" && j.contains("command")) {
                std::string prompt = j["command"].get<std::string>();
                auto cmd = NLPQueryParser::parse(prompt);
                std::cout << "[NLP Command] Prompt: \"" << prompt << "\"\n";
                if (cmd.type == NLPActionType::SetSignalMode) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.policy_switch = cmd.string_value;
                    ctl_.policy_switch_intersection = -1;
                    ctl_.policy_switch_pending = true;
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Switched signal mode to " + cmd.string_value + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetSpeedFactor) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Set speed factor to " + std::to_string(cmd.double_value) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetChaos) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Set chaos coefficient to " + std::to_string(cmd.double_value) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetRouteSpread) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Set route spread to " + std::to_string(cmd.double_value) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetBusLane) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Added bus lane on edge " + std::to_string(cmd.node_u) + " -> " + std::to_string(cmd.node_v) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetBlockEdge) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Simulated incident/roadblock on edge " + std::to_string(cmd.node_u) + " -> " + std::to_string(cmd.node_v) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetCongestionPricing) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Set congestion toll penalty to " + std::to_string(cmd.double_value) + "\"}");
                    }
                } else if (cmd.type == NLPActionType::SetEvRatio) {
                    std::lock_guard<std::mutex> lock(ctl_.m);
                    ctl_.pending_whatif.push_back(cmd);
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Set EV fleet ratio to " + std::to_string(cmd.double_value * 100.0) + "%\"}");
                    }
                } else if (cmd.type == NLPActionType::QueryMetrics) {
                    if (ws_server_) {
                        ws_server_->broadcast_control("{\"type\":\"nlp_ack\",\"message\":\"Telemetry and equity metrics stream active on dashboard.\"}");
                    }
                }
            }
        } catch (const std::exception&) {
        }
    }

    void start_websocket_server() {
        ws_server_ = std::make_unique<network::WebSocketServer>(config_.port);
        ws_server_->set_message_handler([this](const std::string& msg) {
            handle_ws_message(msg);
        });
        ws_server_->start();
        std::cout << "WebSocket Server starting on port " << config_.port << "...\n";
    }

    void set_paused(bool p) {
        std::lock_guard<std::mutex> lock(ctl_.m);
        ctl_.paused = p;
    }

    bool is_paused() {
        std::lock_guard<std::mutex> lock(ctl_.m);
        return ctl_.paused;
    }

    ReloadKind take_reload() {
        std::lock_guard<std::mutex> lock(ctl_.m);
        ReloadKind k = ctl_.reload;
        ctl_.reload = ReloadKind::None;
        return k;
    }

    std::string take_city_request() {
        std::lock_guard<std::mutex> lock(ctl_.m);
        std::string c = ctl_.city_request;
        ctl_.city_request.clear();
        return c;
    }

    bool take_policy_switch(std::string& out_pol, int64_t& out_id) {
        std::lock_guard<std::mutex> lock(ctl_.m);
        if (!ctl_.policy_switch_pending) return false;
        ctl_.policy_switch_pending = false;
        out_pol = ctl_.policy_switch;
        out_id = ctl_.policy_switch_intersection;
        return true;
    }

    std::vector<NLPCommand> take_whatif_commands() {
        std::lock_guard<std::mutex> lock(ctl_.m);
        if (ctl_.pending_whatif.empty()) return {};
        std::vector<NLPCommand> copy = std::move(ctl_.pending_whatif);
        ctl_.pending_whatif.clear();
        return copy;
    }

    void set_current_city(const std::string& c) {
        std::lock_guard<std::mutex> lock(ctl_.m);
        ctl_.current_city = c;
    }

    std::string get_current_city() {
        std::lock_guard<std::mutex> lock(ctl_.m);
        return ctl_.current_city;
    }

    void run_city_session(const std::string& city) {
        std::string filepath = city_data_path(city, "graph.json");
        std::ifstream test(filepath);
        if (!test.good()) {
            std::cerr << "No graph data for city: " << city << " (" << filepath << ")\n";
            if (ws_server_) {
                ws_server_->broadcast_control("{\"type\":\"error\",\"message\":\"No graph data for city " + city + "\"}");
            }
            return;
        }

        std::cout << "Loading graph for " << city << "...\n";
        auto g = std::make_shared<Graph>(load_from_json(filepath));
        set_current_city(city);

        std::cout << "Nodes: " << g->node_count()
                  << " Edges: " << g->edge_count()
                  << " Lanes: " << g->total_lanes()
                  << " Zones: " << g->zone_count() << "\n";

        Simulation sim(*g, config_.chaos);
        sim.set_chaos(config_.chaos);
        sim.set_speed_factor(config_.speed_factor);
        sim.set_route_spread(config_.route_spread);
        sim.set_city_name(city);
        sim.set_policy(policy_.get());
        sim.set_signal_mode(policy_ ? "rl" : "webster");

        // Explicit OD matrix if requested via CLI option --od
        if (!config_.od_path.empty()) {
            std::string od = config_.od_path;
            std::ifstream od_test(od);
            if (od_test.good()) {
                double demand_scale = config_.demand_scale;
                if (config_.auto_scale) {
                    double peak = compute_peak_hourly_demand(od);
                    if (peak > 0.0) {
                        demand_scale = 600.0 / peak;
                        std::cout << "Auto demand_scale = " << demand_scale
                                  << " (peak " << peak << " veh/hr -> target ~600 veh/hr)\n";
                    }
                }
                std::cout << "Spawning from OD demand...\n";
                sim.spawn_agents_from_od(od, demand_scale, config_.start_hour);
            } else {
                std::cerr << "OD file not found: " << config_.od_path << "; falling back to uniform spawning\n";
            }
        }

        // Always ensure the active fleet has vehicles navigating the network
        if (sim.active_agents() == 0 && config_.agent_count > 0) {
            std::cout << "Spawning " << config_.agent_count << " agents (uniform)...\n";
            sim.spawn_agents(config_.agent_count);
        }

        if (ws_server_) {
            ws_server_->broadcast_control(
                "{\"type\":\"city_loaded\",\"city\":\"" + city
                + "\",\"nodes\":" + std::to_string(g->node_count())
                + ",\"edges\":" + std::to_string(g->edge_count()) + "}");
        }

        if (config_.fast) {
            int ticks = static_cast<int>((config_.duration_min * 60.0) / config_.dt);
            std::cout << "Running " << config_.duration_min << "-min sim ("
                      << ticks << " ticks, dt=" << config_.dt << "s) [fast/headless]...\n";
            for (int i = 0; i < ticks; ++i) {
                if (!running_) break;
                sim.tick(config_.dt);
                if (!config_.no_ws && ws_server_) sim.broadcast_state(ws_server_.get());
                if (i % 500 == 0) {
                    std::cout << "Tick " << i << "/" << ticks
                              << " active=" << sim.active_agents() << "\n";
                }
            }
            sim.log_journey_times(config_.journey_csv);
            std::cout << "Avg tick: " << sim.avg_tick_ms() << "ms"
                      << " p50: " << sim.p50_tick_ms() << "ms"
                      << " p90: " << sim.p90_tick_ms() << "ms"
                      << " p95: " << sim.p95_tick_ms() << "ms"
                      << " p99: " << sim.p99_tick_ms() << "ms"
                      << " max: " << sim.max_tick_ms() << "ms\n";
            std::cout << "Emissions: CO2=" << sim.total_co2_kg() << "kg NOx=" << sim.total_nox_g()
                      << "g | Transit Equity Index=" << sim.transit_equity_index() << "\n";
            std::cout << "Saved " << config_.journey_csv << "\n";
            return;
        }

        std::cout << "Running " << city << " continuously. "
                  << "Use the dashboard controls to pause/restart/reset.\n";
        core::FramePacer pacer(60.0);
        int tick = 0;
        for (;;) {
            if (!running_) break;

            {
                std::lock_guard<std::mutex> lock(ctl_.m);
                if (ctl_.reload != ReloadKind::None || !ctl_.city_request.empty()) break;
            }

            if (is_paused()) {
#ifdef _WIN32
                Sleep(50);
#else
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
#endif
                continue;
            }

            std::string policy_switch;
            int64_t target_id = -1;
            if (take_policy_switch(policy_switch, target_id)) {
                if (policy_switch == "rl" && !(policy_ && policy_->is_loaded())) {
                    if (ws_server_) {
                        ws_server_->broadcast_control(
                            "{\"type\":\"policy_switched\",\"ok\":false,"
                            "\"error\":\"no AI policy loaded (start the engine with --policy policy.onnx)\"}");
                    }
                } else {
                    if (target_id >= 0) {
                        bool ok = sim.set_intersection_policy(target_id, policy_switch);
                        if (ws_server_) {
                            ws_server_->broadcast_control(
                                "{\"type\":\"policy_switched\",\"ok\":" + std::string(ok ? "true" : "false")
                                + ",\"mode\":\"" + policy_switch + "\",\"intersection_id\":" + std::to_string(target_id) + "}");
                        }
                    } else {
                        sim.set_signal_mode(policy_switch);
                        if (ws_server_) {
                            ws_server_->broadcast_control(
                                "{\"type\":\"policy_switched\",\"ok\":true,\"mode\":\""
                                + policy_switch + "\"}");
                        }
                    }
                }
            }

            auto whatifs = take_whatif_commands();
            for (const auto& w : whatifs) {
                if (w.type == NLPActionType::SetBusLane) {
                    sim.set_bus_lane(w.node_u, w.node_v);
                } else if (w.type == NLPActionType::SetBlockEdge) {
                    sim.set_blocked_edge(w.node_u, w.node_v);
                } else if (w.type == NLPActionType::SetCongestionPricing) {
                    // Apply congestion pricing across the network or specific zone
                    sim.routing_policy().toll_weight = w.double_value;
                } else if (w.type == NLPActionType::SetEvRatio) {
                    sim.set_ev_ratio(w.double_value);
                } else if (w.type == NLPActionType::SetSpeedFactor) {
                    sim.set_speed_factor(w.double_value);
                } else if (w.type == NLPActionType::SetChaos) {
                    sim.set_chaos(w.double_value);
                } else if (w.type == NLPActionType::SetRouteSpread) {
                    sim.set_route_spread(w.double_value);
                }
            }

            sim.tick(config_.dt);
            sim.respawn_arrived();

            if (!config_.no_ws && ws_server_ && (tick % 2 == 0)) {
                sim.broadcast_state(ws_server_.get());
            }

            if (++tick % 500 == 0) {
                std::cout << "Tick " << tick
                          << " active=" << sim.active_agents()
                          << " completed=" << sim.completed_agents()
                          << " CO2=" << sim.total_co2_kg() << "kg\n";
            }

            pacer.pace();
        }
    }
};

} // namespace nexussim
