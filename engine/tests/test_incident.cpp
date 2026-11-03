#include <gtest/gtest.h>
#include "../src/graph/Graph.h"
#include "../src/agent/Pathfinder.h"

using namespace nexussim;

TEST(EdgePenaltyTest, SetAndGetPenalty) {
    Graph g;
    EXPECT_DOUBLE_EQ(g.get_edge_penalty(10, 20), 1.0);

    g.set_edge_penalty(10, 20, 5.0);
    EXPECT_DOUBLE_EQ(g.get_edge_penalty(10, 20), 5.0);

    // Setting penalty <= 1.0 removes it (returns to 1.0)
    g.set_edge_penalty(10, 20, 1.0);
    EXPECT_DOUBLE_EQ(g.get_edge_penalty(10, 20), 1.0);
}

TEST(EdgePenaltyTest, InfinitePenaltyPreventsTraversal) {
    Graph g;
    // Nodes 1 -> 2 -> 3 (direct path)
    // Nodes 1 -> 4 -> 3 (detour path)
    g.add_node({1, 0.0, 0.0, 0.0, 0.0, 1});
    g.add_node({2, 0.0, 1.0, 100.0, 0.0, 1});
    g.add_node({3, 0.0, 2.0, 200.0, 0.0, 1});
    g.add_node({4, 1.0, 1.0, 100.0, 50.0, 1});

    g.add_edge({1, 2, 100.0, 2});
    g.add_edge({2, 3, 100.0, 2});
    g.add_edge({1, 4, 120.0, 2});
    g.add_edge({4, 3, 120.0, 2});

    // Baseline: shortest path is 1 -> 2 -> 3
    auto p1 = Pathfinder::compute_path(g, 1, 3);
    ASSERT_EQ(p1.size(), 3u);
    EXPECT_EQ(p1[0], 1);
    EXPECT_EQ(p1[1], 2);
    EXPECT_EQ(p1[2], 3);

    // Block edge 1 -> 2
    g.set_edge_penalty(1, 2, Graph::INFINITY_PENALTY);
    auto p2 = Pathfinder::compute_path(g, 1, 3);
    ASSERT_EQ(p2.size(), 3u);
    EXPECT_EQ(p2[0], 1);
    EXPECT_EQ(p2[1], 4);
    EXPECT_EQ(p2[2], 3);
}
