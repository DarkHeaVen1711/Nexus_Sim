#include <gtest/gtest.h>
#include "../src/agent/SnapshotBuffer.h"

using namespace nexussim;

TEST(SnapshotBufferTest, EmptyOnConstruction) {
    SnapshotRingBuffer buf(10);
    EXPECT_EQ(buf.capacity(), 10u);
    EXPECT_EQ(buf.size(), 0u);
    EXPECT_TRUE(buf.empty());
    EXPECT_TRUE(buf.get_available_ticks().empty());
}

TEST(SnapshotBufferTest, PushAndRetrieveExactTick) {
    SnapshotRingBuffer buf(10);
    AgentSystem agents;
    agents.add_agent(101, 1, 2, AgentType::Car);
    agents.position[0] = 45.5;
    agents.velocity[0] = 12.3;
    agents.wait_time[0] = 3.0;

    std::unordered_map<int64_t, SignalController> controllers;
    SignalController sc(500);
    sc.current_phase_idx = 1;
    sc.current_state = SignalController::PhaseState::YELLOW;
    sc.current_timer = 2.5;
    controllers.emplace(500, sc);

    EXPECT_TRUE(buf.push_snapshot(100, agents, controllers, 42));
    EXPECT_EQ(buf.size(), 1u);
    EXPECT_FALSE(buf.empty());
    EXPECT_TRUE(buf.has_tick(100));
    EXPECT_FALSE(buf.has_tick(101));

    AgentSystem restored_agents;
    std::unordered_map<int64_t, SignalController> restored_controllers;
    restored_controllers.emplace(500, SignalController(500));
    SnapshotHeader hdr;

    EXPECT_TRUE(buf.restore_snapshot(100, restored_agents, restored_controllers, &hdr));
    EXPECT_EQ(hdr.tick, 100u);
    EXPECT_EQ(hdr.prng_state, 42u);
    EXPECT_EQ(hdr.agent_count, 1u);
    EXPECT_EQ(hdr.controller_count, 1u);

    EXPECT_EQ(restored_agents.size(), 1u);
    EXPECT_EQ(restored_agents.id[0], 101);
    EXPECT_DOUBLE_EQ(restored_agents.position[0], 45.5);
    EXPECT_DOUBLE_EQ(restored_agents.velocity[0], 12.3);
    EXPECT_DOUBLE_EQ(restored_agents.wait_time[0], 3.0);

    EXPECT_EQ(restored_controllers[500].current_phase_idx, 1);
    EXPECT_EQ(restored_controllers[500].current_state, SignalController::PhaseState::YELLOW);
    EXPECT_DOUBLE_EQ(restored_controllers[500].current_timer, 2.5);
}

TEST(SnapshotBufferTest, RingBufferWraparound) {
    SnapshotRingBuffer buf(5);
    AgentSystem agents;
    std::unordered_map<int64_t, SignalController> controllers;

    for (uint64_t t = 1; t <= 10; ++t) {
        buf.push_snapshot(t, agents, controllers);
    }

    EXPECT_EQ(buf.size(), 5u);
    EXPECT_EQ(buf.capacity(), 5u);

    // Oldest ticks 1..5 should have dropped off; 6..10 should be present
    for (uint64_t t = 1; t <= 5; ++t) {
        EXPECT_FALSE(buf.has_tick(t));
    }
    for (uint64_t t = 6; t <= 10; ++t) {
        EXPECT_TRUE(buf.has_tick(t));
    }

    auto ticks = buf.get_available_ticks();
    ASSERT_EQ(ticks.size(), 5u);
    for (size_t i = 0; i < 5; ++i) {
        EXPECT_EQ(ticks[i], 6u + i);
    }
}

TEST(SnapshotBufferTest, Crc32ChecksumValidation) {
    const char* sample_text = "NexusSim Deterministic Digital Twin";
    uint32_t crc1 = calculate_crc32(reinterpret_cast<const uint8_t*>(sample_text), strlen(sample_text));
    uint32_t crc2 = calculate_crc32(reinterpret_cast<const uint8_t*>(sample_text), strlen(sample_text));
    EXPECT_EQ(crc1, crc2);
    EXPECT_NE(crc1, 0u);

    const char* corrupted_text = "NexusSim Deterministic Digital Twin!";
    uint32_t crc_diff = calculate_crc32(reinterpret_cast<const uint8_t*>(corrupted_text), strlen(corrupted_text));
    EXPECT_NE(crc1, crc_diff);
}

TEST(SnapshotBufferTest, MultiAgentStateRoundTrip) {
    SnapshotRingBuffer buf(5);
    AgentSystem src_agents;
    for (int i = 0; i < 25; ++i) {
        src_agents.add_agent(1000 + i, 10, 20, static_cast<AgentType>(i % 5));
        src_agents.position[i] = i * 4.2;
        src_agents.velocity[i] = (i % 3) * 5.5;
        src_agents.wait_time[i] = i * 0.5;
        src_agents.current_edge_idx[i] = i * 2;
    }

    std::unordered_map<int64_t, SignalController> src_ctrls;
    SignalController c1(10);
    c1.current_phase_idx = 2;
    c1.current_state = SignalController::PhaseState::RED;
    c1.current_timer = 5.0;
    src_ctrls.emplace(10, c1);

    EXPECT_TRUE(buf.push_snapshot(777, src_agents, src_ctrls, 99999));

    AgentSystem dst_agents;
    std::unordered_map<int64_t, SignalController> dst_ctrls;
    dst_ctrls.emplace(10, SignalController(10));
    SnapshotHeader hdr;

    EXPECT_TRUE(buf.restore_snapshot(777, dst_agents, dst_ctrls, &hdr));
    EXPECT_EQ(hdr.tick, 777u);
    EXPECT_EQ(hdr.agent_count, 25u);
    EXPECT_EQ(hdr.prng_state, 99999u);
    EXPECT_EQ(dst_agents.size(), 25u);

    for (size_t i = 0; i < 25; ++i) {
        EXPECT_EQ(dst_agents.id[i], 1000 + static_cast<int64_t>(i));
        EXPECT_DOUBLE_EQ(dst_agents.position[i], i * 4.2);
        EXPECT_DOUBLE_EQ(dst_agents.velocity[i], (i % 3) * 5.5);
        EXPECT_EQ(dst_agents.current_edge_idx[i], static_cast<int64_t>(i * 2));
    }
}
