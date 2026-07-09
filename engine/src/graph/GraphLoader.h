#pragma once
#include "Graph.h"
#include <string>

namespace nexussim {

class GraphLoader {
public:
    static Graph load_from_json(const std::string& filepath);
};

} // namespace nexussim
