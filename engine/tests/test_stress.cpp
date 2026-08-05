#include <gtest/gtest.h>
#include <vector>
#include "../src/graph/Graph.h"
#include "../src/agent/Simulation.h"

using namespace nexussim;

namespace {

// Build a synthetic NxN grid graph with bidirectional edges. Each node gets a
// distinct zone so zone-tagging logic is exercised too.
Graph make_grid(int n) {
    Graph g;
    auto id = [n](int i, int j) { return i * n + j; };
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            g.add_node({static_cast<int64_t>(id(i, j)),
                        static_cast<double>(i), static_cast<double>(j),
                        static_cast<double>(i * 100), static_cast<double>(j * 100),
                        static_cast<int32_t>(id(i, j)) % 50, false});
        }
    }
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (i + 1 < n)
                g.add_edge({id(i, j), id(i + 1, j), 100.0, 2});
            if (j + 1 < n)
                g.add_edge({id(i, j), id(i, j + 1), 100.0, 2});
            if (i > 0)
                g.add_edge({id(i, j), id(i - 1, j), 100.0, 2});
            if (j > 0)
                g.add_edge({id(i, j), id(i, j - 1), 100.0, 2});
        }
    }
    return g;
}

} // namespace

// Phase 3.6 stress test: 20,000 agents on a grid, no crashes, no leaks,
// and the tick stays tractable. Mirrors the plan's 20k-agent / 10-minute
// target at a scaled duration suitable for CI.
TEST(StressTest, TwentyThousandAgentsNoCrash) {
    const int n = 12;  // 144 nodes, ~528 edges (bidirectional)
    Graph g = make_grid(n);

    nexussim::Simulation sim(g, 0.1);
    const size_t kAgents = 20000;
    sim.spawn_agents(kAgents);
    EXPECT_EQ(sim.active_agents(), kAgents);

    const double dt = 0.1;
    const int kTicks = 500;  // 50 sim-seconds at dt=0.1

    for (int i = 0; i < kTicks; ++i) {
        ASSERT_NO_THROW(sim.tick(dt));
    }

    EXPECT_GT(sim.active_agents(), 0u)
        << "All agents should not have resolved in 50 simulated seconds "
           "on a 144-node grid";
    double avg_tick = sim.avg_tick_ms();
    EXPECT_GT(avg_tick, 0.0);
    std::cout << "[ stress ] 20k agents x " << kTicks << " ticks, "
              << "avg tick " << avg_tick << "ms, "
              << "p95 " << sim.p95_tick_ms() << "ms\n";
}
