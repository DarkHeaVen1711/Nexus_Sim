#pragma once
#include <string>
#include <vector>
#include <iostream>

namespace nexussim {

struct EngineConfig {
    std::string city = "piedmont";
    int agent_count = 500;
    int duration_min = 5;
    double chaos = 0.1;
    double speed_factor = 0.55;
    double route_spread = 0.2;
    double dt = 0.1;
    bool fast = false;
    bool no_ws = false;
    int port = 9002;
    std::string journey_csv = "journey_times.csv";
    std::string policy_path;
    std::string od_path;
    double demand_scale = 1.0;
    double start_hour = 8.0;
    bool auto_scale = true;
};

class CliParser {
public:
    static EngineConfig parse(int argc, char** argv) {
        EngineConfig cfg;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--city" && i + 1 < argc) {
                cfg.city = argv[++i];
            } else if (arg == "--agents" && i + 1 < argc) {
                cfg.agent_count = std::stoi(argv[++i]);
            } else if (arg == "--duration" && i + 1 < argc) {
                cfg.duration_min = std::stoi(argv[++i]);
            } else if (arg == "--dt" && i + 1 < argc) {
                cfg.dt = std::stod(argv[++i]);
            } else if (arg == "--speed-factor" && i + 1 < argc) {
                cfg.speed_factor = std::stod(argv[++i]);
            } else if (arg == "--route-spread" && i + 1 < argc) {
                cfg.route_spread = std::stod(argv[++i]);
            } else if (arg == "--chaos" && i + 1 < argc) {
                cfg.chaos = std::stod(argv[++i]);
            } else if (arg == "--fast") {
                cfg.fast = true;
            } else if (arg == "--no-ws") {
                cfg.no_ws = true;
            } else if (arg == "--port" && i + 1 < argc) {
                cfg.port = std::stoi(argv[++i]);
            } else if (arg == "--journey" && i + 1 < argc) {
                cfg.journey_csv = argv[++i];
            } else if (arg == "--policy" && i + 1 < argc) {
                cfg.policy_path = argv[++i];
            } else if (arg == "--od" && i + 1 < argc) {
                cfg.od_path = argv[++i];
            } else if (arg == "--demand-scale" && i + 1 < argc) {
                cfg.demand_scale = std::stod(argv[++i]);
                cfg.auto_scale = false;
            } else if (arg == "--start-hour" && i + 1 < argc) {
                cfg.start_hour = std::stod(argv[++i]);
            }
        }
        return cfg;
    }
};

} // namespace nexussim
