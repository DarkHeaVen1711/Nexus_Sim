#include <iostream>
#include "core/CliConfig.h"
#include "core/NexusEngine.h"

int main(int argc, char** argv) {
    std::cout << "NexusSim Engine v3.1\n";
    auto config = nexussim::CliParser::parse(argc, argv);
    nexussim::NexusEngine engine(config);
    engine.run();
    return 0;
}
