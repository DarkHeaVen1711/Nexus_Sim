#include <iostream>
#include <string>
#include <memory>
#include <cstdlib>
#include <csignal>
#include <fstream>
#include <mutex>
#include "graph/GraphLoader.h"
#include "agent/Simulation.h"
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

static std::string graph_path_for(const std::string& city) {
    std::string filepath = "data/" + city + "/graph.json";
    std::ifstream test(filepath);
    if (!test.good()) filepath = "../data/" + city + "/graph.json";
    return filepath;
}

int main(int argc, char** argv) {
    std::string city = "chicago";
    size_t agent_count = 500;
    int duration_min = 5;
    std::string od_path;
    double demand_scale = 1.0;
    double start_hour = 8.0;
    bool fast = false;
    bool no_ws = false;
    std::string journey_csv = "journey_times.csv";
    double speed_factor = 1.0;
    double route_spread = 0.0;
    double chaos = 0.1;

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
        else if (arg == "--demand-scale") demand_scale = std::atof(next("--demand-scale"));
        else if (arg == "--start-hour") start_hour = std::atof(next("--start-hour"));
        else if (arg == "--journey") journey_csv = next("--journey");
        else if (arg == "--speed-factor") speed_factor = std::atof(next("--speed-factor"));
        else if (arg == "--route-spread") route_spread = std::atof(next("--route-spread"));
        else if (arg == "--chaos") chaos = std::atof(next("--chaos"));
        else if (arg == "--fast") fast = true;
        else if (arg == "--no-ws") no_ws = true;
    }

    std::cout << "NexusSim Engine v3.0\n";
    std::signal(SIGINT, handle_signal);
    std::signal(SIGTERM, handle_signal);
    std::string filepath = "data/" + city + "/graph.json";
    std::ifstream test(filepath);
    if (!test.good()) {
        filepath = "../data/" + city + "/graph.json";
    }

    std::cout << "Loading graph for " << city << "...\n";
    auto g = nexussim::load_from_json(filepath);

    std::cout << "Nodes: " << g.node_count()
              << " Edges: " << g.edge_count()
              << " Lanes: " << g.total_lanes()
              << " Zones: " << g.zone_count() << "\n";

    nexussim::Simulation sim(g, chaos);
    sim.set_chaos(chaos);
    sim.set_speed_factor(speed_factor);
    sim.set_route_spread(route_spread);

    if (!od_path.empty()) {
        sim.spawn_agents_from_od(od_path, demand_scale, start_hour);
    } else {
        std::cout << "Spawning " << agent_count << " agents (uniform)...\n";
        sim.spawn_agents(agent_count);
    }

    double dt = 0.1;
    int ticks = static_cast<int>((duration_min * 60.0) / dt);
    std::cout << "Running " << duration_min << "-min sim ("
              << ticks << " ticks, dt=" << dt << "s)"
              << (fast ? " [fast/headless]" : "") << "...\n";

    nexussim::network::WebSocketServer ws_server(9001);
    if (!no_ws) {
        ws_server.start();
        std::cout << "WebSocket Server starting on port 9001...\n";
    }

    for (int i = 0; i < ticks; ++i) {
        sim.tick(dt);
        if (!no_ws)
            sim.broadcast_state(&ws_server);

        if (i % 500 == 0)
            std::cout << "Tick " << i << "/" << ticks
                      << " active=" << sim.active_agents() << "\n";

        // Pace at ~60fps so dashboard can visualize in real-time
        if (!fast) {
#ifdef _WIN32
            Sleep(16);
#else
            std::this_thread::sleep_for(std::chrono::milliseconds(16));
#endif
        }
    }

    sim.log_journey_times(journey_csv);
    std::cout << "Avg tick: " << sim.avg_tick_ms() << "ms"
              << " p95: " << sim.p95_tick_ms() << "ms\n";
    std::cout << "Saved " << journey_csv << "\n";

    if (fast)
        return 0;

    // Simulation finished. Keep the process alive so the WebSocket server (and
    // the dashboard connection) stays up. Exit with Ctrl+C.
    std::cout << "Simulation complete. Keeping WebSocket server alive on port 9001...\n";
    std::cout << "Press Ctrl+C to exit.\n";
    while (!g_stop) {
#ifdef _WIN32
        Sleep(500);
#else
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
#endif
    }
    std::cout << "Shutting down.\n";
    return 0;
}

