#include <gtest/gtest.h>
#include "../src/graph/Graph.h"
#include "../src/agent/Pathfinder.h"
#include "../src/agent/IDM.h"
#include <cmath>

using namespace nexussim;

TEST(PathfinderTest, ShortestPath) {
    Graph g;
    // Simple 3-node graph: 1 -> 2 -> 3
    // 1 -> 3 is direct but longer
    g.add_node({1, 0.0, 0.0, 0.0, 0.0, 10});
    g.add_node({2, 1.0, 0.0, 10.0, 0.0, 10});
    g.add_node({3, 2.0, 0.0, 20.0, 0.0, 10});
    
    g.add_edge({1, 2, 10.0, 1});
    g.add_edge({2, 3, 10.0, 1});
    g.add_edge({1, 3, 30.0, 1}); // Worse path

    auto path = Pathfinder::compute_path(g, 1, 3);
    ASSERT_EQ(path.size(), 3);
    EXPECT_EQ(path[0], 1);
    EXPECT_EQ(path[1], 2);
    EXPECT_EQ(path[2], 3);
}

TEST(IDMTest, Interaction) {
    auto params = get_default_idm_params(AgentType::Car, 0.0);
    
    // Free road: high acceleration
    double acc_free = compute_idm_acceleration(params, 0.0, params.v0, 1000.0);
    EXPECT_NEAR(acc_free, params.a, 0.01);
    
    // Following a slower vehicle closely: should decelerate
    double acc_following = compute_idm_acceleration(params, params.v0, 5.0, 10.0);
    EXPECT_LT(acc_following, 0.0);
}
