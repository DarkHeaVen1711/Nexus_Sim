#include <gtest/gtest.h>
#include "../src/agent/Agent.h"

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
