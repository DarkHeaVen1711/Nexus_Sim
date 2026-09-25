#pragma once
#include <string>
#include <algorithm>
#include <cctype>
#include <regex>
#include <iostream>

namespace nexussim {

enum class NLPActionType {
    SetSpeedFactor,
    SetChaos,
    SetRouteSpread,
    SetSignalMode,
    SetBusLane,
    SetCongestionPricing,
    SetBlockEdge,
    SetEvRatio,
    QueryMetrics,
    Unknown
};

struct NLPCommand {
    NLPActionType type = NLPActionType::Unknown;
    double double_value = 0.0;
    int64_t node_u = -1;
    int64_t node_v = -1;
    int32_t zone_id = -1;
    std::string string_value;
    std::string original_prompt;
};

class NLPQueryParser {
public:
    static NLPCommand parse(const std::string& input) {
        NLPCommand cmd;
        cmd.original_prompt = input;

        std::string lower = input;
        std::transform(lower.begin(), lower.end(), lower.begin(),
                       [](unsigned char c){ return std::tolower(c); });

        // Match Speed Factor (e.g. "set speed factor 0.8", "speed 1.2")
        std::smatch m;
        std::regex speed_regex(R"(speed(?:\s+factor)?\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?))");
        if (std::regex_search(lower, m, speed_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetSpeedFactor;
            cmd.double_value = std::stod(m[1].str());
            return cmd;
        }

        // Match Chaos Coefficient (e.g. "set chaos 0.3", "increase chaos to 0.4")
        std::regex chaos_regex(R"(chaos\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?))");
        if (std::regex_search(lower, m, chaos_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetChaos;
            cmd.double_value = std::stod(m[1].str());
            return cmd;
        }

        // Match Route Spread (e.g. "route spread 0.3", "spread 0.5")
        std::regex spread_regex(R"(spread\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?))");
        if (std::regex_search(lower, m, spread_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetRouteSpread;
            cmd.double_value = std::stod(m[1].str());
            return cmd;
        }

        // Match Congestion Pricing / Toll (e.g. "congestion pricing 5.0", "toll 3.5")
        std::regex toll_regex(R"((?:congestion\s+pricing|toll)\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?))");
        if (std::regex_search(lower, m, toll_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetCongestionPricing;
            cmd.double_value = std::stod(m[1].str());
            return cmd;
        }

        // Match EV Ratio (e.g. "ev ratio 0.4", "ev percentage 35%", "ev 0.5")
        std::regex ev_regex(R"(ev(?:\s+ratio|\s+percentage|\s+fleet)?\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?)\s*%?)");
        if (std::regex_search(lower, m, ev_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetEvRatio;
            double val = std::stod(m[1].str());
            if (val > 1.0) val /= 100.0;
            cmd.double_value = val;
            return cmd;
        }

        // Match Bus Lane (e.g. "bus lane 101 102", "add bus lane 101 to 102")
        std::regex bus_regex(R"(bus\s+lane\s+(?:on\s+)?([0-9]+)\s+(?:to\s+)?([0-9]+))");
        if (std::regex_search(lower, m, bus_regex) && m.size() > 2) {
            cmd.type = NLPActionType::SetBusLane;
            cmd.node_u = std::stoll(m[1].str());
            cmd.node_v = std::stoll(m[2].str());
            return cmd;
        }

        // Match Accident / Road Block (e.g. "accident 101 102", "block edge 101 102")
        std::regex block_regex(R"((?:accident|block(?:\s+edge)?|incident)\s+(?:on\s+)?([0-9]+)\s+(?:to\s+)?([0-9]+))");
        if (std::regex_search(lower, m, block_regex) && m.size() > 2) {
            cmd.type = NLPActionType::SetBlockEdge;
            cmd.node_u = std::stoll(m[1].str());
            cmd.node_v = std::stoll(m[2].str());
            return cmd;
        }

        // Match Signal Policy Mode (e.g. "set signal mode rl", "webster", "fuzzy")
        if (lower.find("rl") != std::string::npos || lower.find("ai") != std::string::npos) {
            cmd.type = NLPActionType::SetSignalMode;
            cmd.string_value = "rl";
            return cmd;
        } else if (lower.find("fuzzy") != std::string::npos) {
            cmd.type = NLPActionType::SetSignalMode;
            cmd.string_value = "fuzzy";
            return cmd;
        } else if (lower.find("webster") != std::string::npos) {
            cmd.type = NLPActionType::SetSignalMode;
            cmd.string_value = "webster";
            return cmd;
        }

        // Match Query Metrics (e.g. "what is the average wait time", "show equity", "gini score")
        if (lower.find("wait") != std::string::npos || lower.find("gini") != std::string::npos ||
            lower.find("equity") != std::string::npos || lower.find("emission") != std::string::npos) {
            cmd.type = NLPActionType::QueryMetrics;
            return cmd;
        }

        return cmd;
    }
};

} // namespace nexussim
