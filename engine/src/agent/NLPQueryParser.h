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
    Unknown
};

struct NLPCommand {
    NLPActionType type = NLPActionType::Unknown;
    double double_value = 0.0;
    int64_t node_id = -1;
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

        // Match Speed Factor (e.g. "set speed factor 0.8", "speed 1.2", "speed factor 0.5")
        std::smatch m;
        std::regex speed_regex(R"(speed(?:\s+factor)?\s*(?:to|=)?\s*([0-9]+(?:\.[0-9]+)?))");
        if (std::regex_search(lower, m, speed_regex) && m.size() > 1) {
            cmd.type = NLPActionType::SetSpeedFactor;
            cmd.double_value = std::stod(m[1].str());
            return cmd;
        }

        // Match Chaos Coefficient (e.g. "set chaos 0.3", "increase chaos to 0.4", "rain chaos 0.25")
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

        // Match Signal Policy Mode (e.g. "set signal mode rl", "webster signal", "signal mode webster")
        if (lower.find("rl") != std::string::npos || lower.find("ai") != std::string::npos) {
            cmd.type = NLPActionType::SetSignalMode;
            cmd.string_value = "rl";
            return cmd;
        } else if (lower.find("webster") != std::string::npos) {
            cmd.type = NLPActionType::SetSignalMode;
            cmd.string_value = "webster";
            return cmd;
        }

        return cmd;
    }
};

} // namespace nexussim
