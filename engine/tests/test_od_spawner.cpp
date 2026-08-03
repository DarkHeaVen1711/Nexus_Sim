#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>
#include "../src/graph/Graph.h"
#include "../src/agent/Simulation.h"

using namespace nexussim;

namespace {

std::string write_od_json(int origin, int dest, double rate) {
    // Zone 1 -> zone 2 at `rate` vehicles/hour, flat across all hours.
    std::string hourly;
    for (int h = 0; h < 24; ++h) {
        if (h) hourly += ",";
        hourly += std::to_string(h == 8 ? rate : 0.0);
    }
    std::string tt;
    for (int h = 0; h < 24; ++h) {
        if (h) tt += ",";
        tt += std::to_string(h == 8 ? 900.0 : 0.0);
    }
    std::string json =
        "{\"schema_version\":\"1.0\",\"city\":\"test\",\"source\":\"test\","
        "\"zone_count\":2,\"zones\":{\"1\":{\"name\":\"A\",\"lat\":0,"
        "\"lon\":0},\"2\":{\"name\":\"B\",\"lat\":1,\"lon\":1}},"
        "\"od\":[{\"origin\":" + std::to_string(origin) +
        ",\"destination\":" + std::to_string(dest) +
        ",\"hourly\":[" + hourly + "],\"hourly_tt\":[" + tt + "]}]}";
    std::filesystem::path p = std::filesystem::temp_directory_path() /
                              "od_spawner_test.json";
    std::ofstream f(p);
    f << json;
    return p.string();
}

Graph make_graph() {
    Graph g;
    // Two zones: nodes 1-3 in zone 1, nodes 4-6 in zone 2.
    g.add_node({1, 0.0, 0.0, 0.0, 0.0, 1});
    g.add_node({2, 0.001, 0.0, 100.0, 0.0, 1});
    g.add_node({3, 0.002, 0.0, 200.0, 0.0, 1});
    g.add_node({4, 1.0, 0.0, 10000.0, 0.0, 2});
    g.add_node({5, 1.001, 0.0, 10100.0, 0.0, 2});
    g.add_node({6, 1.002, 0.0, 10200.0, 0.0, 2});
    g.add_edge({1, 4, 10000.0, 1});
    g.add_edge({1, 5, 10000.0, 1});
    g.add_edge({1, 6, 10000.0, 1});
    g.add_edge({2, 4, 10000.0, 1});
    g.add_edge({2, 5, 10000.0, 1});
    g.add_edge({2, 6, 10000.0, 1});
    g.add_edge({3, 4, 10000.0, 1});
    g.add_edge({3, 5, 10000.0, 1});
    g.add_edge({3, 6, 10000.0, 1});
    return g;
}

}  // namespace

TEST(ODSpawnerTest, SpawnsFromMatrix) {
    Graph g = make_graph();
    Simulation sim(g, 0.1);
    std::string od = write_od_json(1, 2, 3600.0);  // 1 vehicle/s at hour 8

    sim.spawn_agents_from_od(od, 1.0, 8.0);

    // Run 10 seconds of sim time at hour 8 => ~10 vehicles expected.
    for (int i = 0; i < 100; ++i) sim.tick(0.1);

    // Agents spawned from zone 1 to zone 2.
    EXPECT_GE(sim.active_agents(), 5);
    EXPECT_LE(sim.active_agents(), 15);
}

TEST(ODSpawnerTest, NoSpawnWhenRateZero) {
    Graph g = make_graph();
    Simulation sim(g, 0.1);
    // Rate 0 across all hours except we set hour 8 = 0 anyway.
    std::string od = write_od_json(1, 2, 0.0);
    sim.spawn_agents_from_od(od, 1.0, 12.0);  // start hour outside peak
    for (int i = 0; i < 100; ++i) sim.tick(0.1);
    EXPECT_EQ(sim.active_agents(), 0);
}

TEST(ODSpawnerTest, MissingOdFileIsGraceful) {
    Graph g = make_graph();
    Simulation sim(g, 0.1);
    sim.spawn_agents_from_od("does_not_exist.json", 1.0, 8.0);
    for (int i = 0; i < 50; ++i) sim.tick(0.1);
    EXPECT_EQ(sim.active_agents(), 0);
}
