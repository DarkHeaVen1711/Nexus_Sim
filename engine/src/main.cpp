#include <iostream>
#include <string>
#include <memory>
#include <cstdlib>
#include <csignal>
#include <fstream>
#include <mutex>
#include <vector>
#include "graph/GraphLoader.h"
#include "agent/Simulation.h"
#include "ai/InferenceEngine.h"
#include "network/WebSocketServer.h"
#include <nlohmann/json.hpp>

static volatile std::sig_atomic_t g_stop = 0;

static void handle_signal(int) {
    g_stop = 1;
}

// A city-selection request coming from the dashboard over WebSocket. Written on
// the uWS event-loop thread, read on the main simulation thread.
struct CityRequest {
    std::mutex m;
    std::string city;
    bool pending = false;
};
static CityRequest g_city_req;

// Current city the engine is simulating (for the get_city probe). Empty when
// the engine is idling and no simulation is running yet.
struct CurrentCity {
    std::mutex m;
    std::string city;
};
static CurrentCity g_current_city;

static std::string current_city() {
    std::lock_guard<std::mutex> lock(g_current_city.m);
    return g_current_city.city;
}

static bool city_change_requested() {
    std::lock_guard<std::mutex> lock(g_city_req.m);
    return g_city_req.pending;
}

static std::string take_city_request() {
    std::lock_guard<std::mutex> lock(g_city_req.m);
    if (!g_city_req.pending) return "";
    g_city_req.pending = false;
    return g_city_req.city;
}

// Resolves data/<city>/<file>, preferring a path that exists (running from the
// repo root or from engine/). Used for the graph and the per-city OD matrix.
static std::string city_data_path(const std::string& city,
                                  const std::string& file) {
    std::string filepath = "data/" + city + "/" + file;
    std::ifstream test(filepath);
    if (!test.good()) filepath = "../data/" + city + "/" + file;
    return filepath;
}

static std::string graph_path_for(const std::string& city) {
    return city_data_path(city, "graph.json");
}

// Target citywide peak vehicles/hour used to auto-derive demand_scale when the
// caller did not provide one. Keeps OD-driven runs live but tractable on the
// dashboard regardless of how small (or large) a city's OD matrix is.
constexpr double kAutoPeakVehiclesPerHour = 600.0;

// Reads an OD matrix and returns the peak citywide hourly demand (sum across
// all OD pairs for the busiest hour). Returns 0 on any error / empty matrix.
static double peak_hourly_demand(const std::string& od_path) {
    std::ifstream f(od_path);
    if (!f.good()) return 0.0;
    nlohmann::json j;
    try {
        f >> j;
    } catch (const std::exception&) {
        return 0.0;
    }
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
}

// Loads the ONNX traffic-signal policy when requested. A missing or invalid
// model is a warning, not an error: the engine falls back to Webster timing.
static std::unique_ptr<nexussim::ai::InferenceEngine> load_policy_or_warn(
    const std::string& policy_path) {
    if (policy_path.empty()) return nullptr;
    auto policy = std::make_unique<nexussim::ai::InferenceEngine>();
    if (policy->load(policy_path)) {
        std::cout << "AI policy loaded: " << policy_path << " (obs_dim="
                  << policy->obs_dim() << ", actions="
                  << policy->num_actions() << ")\n";
    } else {
        std::cerr << "WARNING: failed to load policy '" << policy_path
                  << "'; falling back to Webster signal timing\n";
        return nullptr;
    }
    return policy;
}

// Runs the simulation for one city until the dashboard asks for a different
// city (interactive mode) or the configured duration elapses (headless mode).
static void run_city(const std::string& city, int agent_count, int duration_min,
                     double chaos, double speed_factor, double route_spread,
                     double dt, bool fast, bool no_ws,
                     const std::string& journey_csv,
                     nexussim::network::WebSocketServer* ws_server,
                     nexussim::ai::InferenceEngine* policy,
                     const std::string& od_path, double demand_scale,
                     double start_hour, bool auto_scale) {
    std::string filepath = graph_path_for(city);
    std::ifstream test(filepath);
    if (!test.good()) {
        std::cerr << "No graph data for city: " << city << " (" << filepath << ")\n";
        if (ws_server) {
            ws_server->broadcast_text(
                "{\"type\":\"error\",\"message\":\"No graph data for city "
                + city + "\"}");
        }
        return;
    }

    std::cout << "Loading graph for " << city << "...\n";
    auto g = std::make_shared<nexussim::Graph>(
        nexussim::load_from_json(filepath));

    {
        std::lock_guard<std::mutex> lock(g_current_city.m);
        g_current_city.city = city;
    }

    std::cout << "Nodes: " << g->node_count()
              << " Edges: " << g->edge_count()
              << " Lanes: " << g->total_lanes()
              << " Zones: " << g->zone_count() << "\n";

    nexussim::Simulation sim(*g, chaos);
    sim.set_chaos(chaos);
    sim.set_speed_factor(speed_factor);
    sim.set_route_spread(route_spread);
    sim.set_city_name(city);
    sim.set_policy(policy);
    sim.set_signal_mode(policy ? "ai" : "webster");

    // OD-driven demand: an explicit --od path wins, otherwise the city's own
    // od_matrix.json is used when present. Cities without an OD matrix fall
    // back to uniform random spawning.
    std::string od = od_path.empty()
                         ? city_data_path(city, "od_matrix.json")
                         : od_path;
    std::ifstream od_test(od);
    if (od_test.good()) {
        if (auto_scale) {
            double peak = peak_hourly_demand(od);
            if (peak > 0.0) {
                double scale = kAutoPeakVehiclesPerHour / peak;
                std::cout << "Auto demand_scale = " << scale
                          << " (peak " << peak
                          << " veh/hr -> target ~"
                          << kAutoPeakVehiclesPerHour << " veh/hr)\n";
                demand_scale = scale;
            }
        }
        std::cout << "Spawning from OD demand...\n";
        sim.spawn_agents_from_od(od, demand_scale, start_hour);
    } else {
        if (!od_path.empty())
            std::cerr << "OD file not found: " << od_path
                      << "; falling back to uniform spawning\n";
        std::cout << "Spawning " << agent_count << " agents (uniform)...\n";
        sim.spawn_agents(agent_count);
    }

    if (ws_server) {
        ws_server->broadcast_text(
            "{\"type\":\"city_loaded\",\"city\":\"" + city
            + "\",\"nodes\":" + std::to_string(g->node_count())
            + ",\"edges\":" + std::to_string(g->edge_count()) + "}");
    }

    if (fast) {
        int ticks = static_cast<int>((duration_min * 60.0) / dt);
        std::cout << "Running " << duration_min << "-min sim ("
                  << ticks << " ticks, dt=" << dt << "s) [fast/headless]...\n";
        for (int i = 0; i < ticks; ++i) {
            sim.tick(dt);
            if (!no_ws) sim.broadcast_state(ws_server);
            if (i % 500 == 0)
                std::cout << "Tick " << i << "/" << ticks
                          << " active=" << sim.active_agents() << "\n";
        }
        sim.log_journey_times(journey_csv);
        std::cout << "Avg tick: " << sim.avg_tick_ms() << "ms"
                  << " p95: " << sim.p95_tick_ms() << "ms\n";
        std::cout << "Saved " << journey_csv << "\n";
        return;
    }

    // Interactive mode: keep simulating (respawn completed agents so traffic
    // stays live) until the dashboard picks another city or the engine stops.
    std::cout << "Running " << city << " continuously. "
              << "Select a city on the dashboard to switch.\n";
    int tick = 0;
    for (;;) {
        if (g_stop) break;
        if (city_change_requested()) {
            std::cout << "City switch requested; reloading...\n";
            break;
        }
        sim.tick(dt);
        sim.respawn_arrived();
        if (!no_ws) sim.broadcast_state(ws_server);
        if (++tick % 500 == 0)
            std::cout << "Tick " << tick
                      << " active=" << sim.active_agents()
                      << " completed=" << sim.completed_agents() << "\n";

        // Pace at ~60fps so dashboard can visualize in real-time
#ifdef _WIN32
        Sleep(16);
#else
        std::this_thread::sleep_for(std::chrono::milliseconds(16));
#endif
    }
}

int main(int argc, char** argv) {
    std::string city = "piedmont";
    size_t agent_count = 500;
    int duration_min = 5;
    std::string od_path;
    double demand_scale = 1.0;
    bool auto_scale = true;
    double start_hour = 8.0;
    bool fast = false;
    bool no_ws = false;
    std::string journey_csv = "journey_times.csv";
    double speed_factor = 1.0;
    double route_spread = 0.0;
    double chaos = 0.1;
    std::string policy_path;

    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        auto next = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << "\n";
                std::exit(1);
            }
            return argv[++i];
        };
        if (arg == "--city") city = next("--city");
        else if (arg == "--agents") agent_count = std::stoul(next("--agents"));
        else if (arg == "--duration") duration_min = std::atoi(next("--duration"));
        else if (arg == "--od") od_path = next("--od");
        else if (arg == "--demand-scale") { demand_scale = std::atof(next("--demand-scale")); auto_scale = false; }
        else if (arg == "--start-hour") start_hour = std::atof(next("--start-hour"));
        else if (arg == "--journey") journey_csv = next("--journey");
        else if (arg == "--speed-factor") speed_factor = std::atof(next("--speed-factor"));
        else if (arg == "--route-spread") route_spread = std::atof(next("--route-spread"));
        else if (arg == "--chaos") chaos = std::atof(next("--chaos"));
        else if (arg == "--policy") policy_path = next("--policy");
        else if (arg == "--fast") fast = true;
        else if (arg == "--no-ws") no_ws = true;
    }

    std::cout << "NexusSim Engine v3.0\n";
    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);

    nexussim::network::WebSocketServer ws_server(9001);
    if (!no_ws) {
        ws_server.set_message_handler([&ws_server](const std::string& payload) {
            try {
                auto j = nlohmann::json::parse(payload);
                if (!j.contains("type")) return;
                if (j["type"] == "city" && j.contains("city")) {
                    std::lock_guard<std::mutex> lock(g_city_req.m);
                    g_city_req.city = j["city"].get<std::string>();
                    g_city_req.pending = true;
                } else if (j["type"] == "get_city") {
                    // A dashboard connected late and missed the startup
                    // city_loaded broadcast; tell it which city we run (null
                    // while the engine is idling and no sim is running).
                    // broadcast_text is thread-safe (queues to the event loop).
                    std::string c = current_city();
                    std::string city_json =
                        c.empty() ? "null" : "\"" + c + "\"";
                    ws_server.broadcast_text(
                        "{\"type\":\"city_loaded\",\"city\":" + city_json
                        + "}");
                }
            } catch (const std::exception&) {
                // Ignore malformed messages.
            }
        });
        ws_server.start();
        std::cout << "WebSocket Server starting on port 9001...\n";
    }

    double dt = 0.1;
    auto policy = load_policy_or_warn(policy_path);
    std::cout << "Signal mode: "
              << (policy ? "ai" : "webster") << "\n";

    if (fast) {
        run_city(city, static_cast<int>(agent_count), duration_min,
                 chaos, speed_factor, route_spread, dt, fast, no_ws,
                 journey_csv, no_ws ? nullptr : &ws_server, policy.get(),
                 od_path, demand_scale, start_hour, auto_scale);
        return 0;
    }

    // Interactive mode: do NOT auto-start a simulation. The engine idles until
    // the dashboard sends a city selection, then runs that city continuously
    // (agents respawn so traffic stays live) until another city is picked.
    std::string current_city;
    for (;;) {
        if (g_stop) break;

        if (current_city.empty()) {
            std::cout << "Engine ready. Select a city on the dashboard to start.\n";
            while (!g_stop) {
                std::string next = take_city_request();
                if (!next.empty()) {
                    current_city = next;
                    break;
                }
#ifdef _WIN32
                Sleep(50);
#else
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
#endif
            }
            if (g_stop) break;
        }

        run_city(current_city, static_cast<int>(agent_count), duration_min,
                 chaos, speed_factor, route_spread, dt, fast, no_ws,
                 journey_csv, &ws_server, policy.get(),
                 od_path, demand_scale, start_hour, auto_scale);

        // run_city returned: the engine is stopping or the dashboard requested
        // a different city. Consume the request and continue with it.
        std::string next = take_city_request();
        current_city = next.empty() ? "" : next;
    }

    std::cout << "Shutting down.\n";
    return 0;
}
