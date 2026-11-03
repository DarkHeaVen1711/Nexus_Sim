#include <gtest/gtest.h>
#include "../src/agent/Agent.h"
#include "../src/graph/Graph.h"
#include "../src/agent/Pathfinder.h"

using namespace nexussim;

TEST(MultiModalTest, KinematicProfilesByMode) {
    auto car_kin = AgentKinematics::for_type(AgentType::Car);
    EXPECT_DOUBLE_EQ(car_kin.length_m, 4.8);
    EXPECT_DOUBLE_EQ(car_kin.max_accel_mps2, 2.5);

    auto bus_kin = AgentKinematics::for_type(AgentType::Bus);
    EXPECT_DOUBLE_EQ(bus_kin.length_m, 12.0);
    EXPECT_DOUBLE_EQ(bus_kin.max_accel_mps2, 1.0);
    EXPECT_DOUBLE_EQ(bus_kin.max_speed_mps, 13.89);

    auto bike_kin = AgentKinematics::for_type(AgentType::TwoWheeler);
    EXPECT_DOUBLE_EQ(bike_kin.length_m, 2.0);
    EXPECT_DOUBLE_EQ(bike_kin.max_accel_mps2, 1.8);

    auto emg_kin = AgentKinematics::for_type(AgentType::Emergency);
    EXPECT_DOUBLE_EQ(emg_kin.length_m, 6.5);
    EXPECT_DOUBLE_EQ(emg_kin.max_accel_mps2, 3.5);
    EXPECT_DOUBLE_EQ(emg_kin.max_speed_mps, 22.22);
}

TEST(MultiModalTest, AgentSystemSoAInitialization) {
    AgentSystem agents;
    size_t c_idx = agents.add_agent(1, 10, 20, AgentType::Car);
    size_t ev_idx = agents.add_agent(2, 10, 20, AgentType::ElectricVehicle);
    size_t bus_idx = agents.add_agent(3, 10, 20, AgentType::Bus);

    EXPECT_EQ(agents.size(), 3u);
    EXPECT_DOUBLE_EQ(agents.battery_soc[c_idx], 1.0);
    EXPECT_DOUBLE_EQ(agents.battery_capacity_kwh[c_idx], 0.0);

    EXPECT_DOUBLE_EQ(agents.battery_soc[ev_idx], 0.90);
    EXPECT_DOUBLE_EQ(agents.battery_capacity_kwh[ev_idx], 60.0);

    EXPECT_DOUBLE_EQ(agents.target_speed[bus_idx], 13.89);
}

TEST(EVTest, BatteryDrainDuringCruising) {
    AgentSystem agents;
    size_t ev = agents.add_agent(100, 1, 2, AgentType::ElectricVehicle);
    agents.battery_soc[ev] = 0.50; // 50%
    agents.battery_capacity_kwh[ev] = 60.0; // 60 kWh pack

    // Cruise for 10 km (10,000 m) over 600 seconds (10 minutes)
    simulate_ev_consumption(agents, ev, 10000.0, 600.0);

    // Energy used: 10 km * 0.18 kWh/km = 1.8 kWh traction + 1.5 kW * (600/3600) h = 0.25 kWh aux = 2.05 kWh
    // Delta SoC = 2.05 / 60.0 = 0.034166...
    // Expected new SoC ~ 0.50 - 0.034166 = 0.46583
    EXPECT_LT(agents.battery_soc[ev], 0.50);
    EXPECT_NEAR(agents.battery_soc[ev], 0.4658, 0.001);
}

TEST(EVTest, AutonomousRerouteToNearestDepot) {
    Graph g;
    g.add_node({1, 0, 0, 0.0, 0.0, 1});
    g.add_node({2, 0, 0, 50.0, 0.0, 1});
    g.add_node({3, 0, 0, 100.0, 0.0, 1}); // Far depot
    g.add_node({4, 0, 0, 10.0, 10.0, 1});  // Near depot

    g.add_edge({1, 2, 50.0, 2});
    g.add_edge({2, 3, 50.0, 2});
    g.add_edge({1, 4, 15.0, 2});

    ChargingStation cs_far{3, 4, 0, 50.0, "Far Fast Charger"};
    ChargingStation cs_near{4, 2, 0, 50.0, "Near Quick Charger"};
    g.add_charging_station(cs_far);
    g.add_charging_station(cs_near);

    auto path = Pathfinder::find_nearest_charging_station(g, 1);
    ASSERT_EQ(path.size(), 2u);
    EXPECT_EQ(path[0], 1);
    EXPECT_EQ(path[1], 4); // Chose nearest depot (node 4)!
}

TEST(EVTest, DwellCompletionAndResume) {
    AgentSystem agents;
    size_t ev = agents.add_agent(999, 1, 10, AgentType::ElectricVehicle);
    agents.state[ev] = AgentState::Charging;
    agents.battery_soc[ev] = 0.10; // 10%
    agents.battery_capacity_kwh[ev] = 60.0;
    agents.dwell_time_remaining[ev] = 600.0; // 10 minutes dwell

    // Tick 300s - still charging
    bool resumed = simulate_ev_dwell(agents, ev, 300.0, 50.0);
    EXPECT_FALSE(resumed);
    EXPECT_EQ(agents.state[ev], AgentState::Charging);
    EXPECT_GT(agents.battery_soc[ev], 0.10); // Battery recharged

    // Tick 301s more - dwell completes
    resumed = simulate_ev_dwell(agents, ev, 301.0, 50.0);
    EXPECT_TRUE(resumed);
    EXPECT_EQ(agents.state[ev], AgentState::Navigating); // Resumed navigation!
    EXPECT_DOUBLE_EQ(agents.dwell_time_remaining[ev], 0.0);
}
