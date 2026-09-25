#pragma once
#include <string>
#include <iostream>
#include <cstdlib>

namespace nexussim {

struct EngineConfig {
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
    double speed_factor = 0.55;
    double route_spread = 0.2;
    double chaos = 0.1;
    std::string policy_path;
    double dt = 0.1;
    int port = 9001;
};

class CliParser {
public:
    static EngineConfig parse(int argc, char** argv) {
        EngineConfig cfg;

        for (int i = 1; i < argc; ++i) {
            std::string arg(argv[i]);
            auto next = [&](const char* name) -> const char* {
                if (i + 1 >= argc) {
                    std::cerr << "Missing value for " << name << "\n";
                    std::exit(1);
                }
                return argv[++i];
            };

            if (arg == "--city") cfg.city = next("--city");
            else if (arg == "--agents") {
                try {
                    long long val = std::stoll(next("--agents"));
                    if (val < 0) {
                        std::cerr << "Invalid --agents value: must be non-negative\n";
                        std::exit(1);
                    }
                    cfg.agent_count = static_cast<size_t>(val);
                } catch (...) {
                    std::cerr << "Invalid --agents format\n";
                    std::exit(1);
                }
            }
            else if (arg == "--duration") {
                int val = std::atoi(next("--duration"));
                if (val < 0) {
                    std::cerr << "Invalid --duration value: must be non-negative\n";
                    std::exit(1);
                }
                cfg.duration_min = val;
            }
            else if (arg == "--od") cfg.od_path = next("--od");
            else if (arg == "--demand-scale") { cfg.demand_scale = std::atof(next("--demand-scale")); cfg.auto_scale = false; }
            else if (arg == "--start-hour") cfg.start_hour = std::atof(next("--start-hour"));
            else if (arg == "--journey") cfg.journey_csv = next("--journey");
            else if (arg == "--speed-factor") cfg.speed_factor = std::atof(next("--speed-factor"));
            else if (arg == "--route-spread") cfg.route_spread = std::atof(next("--route-spread"));
            else if (arg == "--chaos") cfg.chaos = std::atof(next("--chaos"));
            else if (arg == "--policy") cfg.policy_path = next("--policy");
            else if (arg == "--port") {
                int val = std::atoi(next("--port"));
                if (val <= 0 || val > 65535) {
                    std::cerr << "Invalid --port value: must be between 1 and 65535\n";
                    std::exit(1);
                }
                cfg.port = val;
            }
            else if (arg == "--dt") {
                cfg.dt = std::atof(next("--dt"));
                if (cfg.dt <= 0.0) {
                    std::cerr << "Invalid --dt value: must be positive\n";
                    std::exit(1);
                }
            }
            else if (arg == "--fast") cfg.fast = true;
            else if (arg == "--no-ws") cfg.no_ws = true;
        }

        return cfg;
    }
};

} // namespace nexussim
