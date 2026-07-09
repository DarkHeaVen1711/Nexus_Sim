#include <gtest/gtest.h>
#include "../src/graph/Graph.h"

using namespace nexussim;

TEST(GraphTest, NodeEdgeCounts) {
    Graph g;
    g.add_node({1, 41.0, -87.0, 10});
    g.add_node({2, 41.1, -87.1, 10});
    g.add_node({3, 41.2, -87.2, 11});
    
    g.add_edge({1, 2, 100.0, 2});
    g.add_edge({2, 3, 150.0, 1});

    EXPECT_EQ(g.node_count(), 3);
    EXPECT_EQ(g.edge_count(), 2);
    EXPECT_EQ(g.zone_count(), 2);
    EXPECT_EQ(g.total_lanes(), 3);
    
    const auto* node = g.get_node(1);
    ASSERT_NE(node, nullptr);
    EXPECT_EQ(node->zone_id, 10);
    
    const auto& edges = g.get_edges_from(2);
    ASSERT_EQ(edges.size(), 1);
    EXPECT_EQ(edges[0].v, 3);
}
