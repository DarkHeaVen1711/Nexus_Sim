#pragma once
#include "Graph.h"
#include <string>

namespace nexussim {

Graph load_from_json(const std::string& filepath);

} // namespace nexussim
