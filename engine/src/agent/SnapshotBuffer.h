#pragma once
#include <cstdint>
#include <vector>
#include <array>
#include <cstring>
#include <chrono>

namespace nexussim {

#pragma pack(push, 1)

struct SnapshotHeader {
    uint32_t magic = 0x4E585353; // "NXSS" (NexusSim Snapshot)
    uint32_t version = 1;
    uint64_t tick = 0;
    uint64_t timestamp_ns = 0;
    uint32_t agent_count = 0;
    uint32_t controller_count = 0;
    uint32_t crc32 = 0;
    uint64_t prng_state = 0;
};

struct AgentSnapshotRecord {
    int64_t id;
    int64_t current_edge_idx;
    double position;
    double velocity;
    double wait_time;
    uint8_t state;
    uint8_t type;
    int32_t lane;
};

struct ControllerSnapshotRecord {
    int64_t node_id;
    int32_t current_phase_idx;
    uint8_t current_state;
    double current_timer;
    double queue_length;
};

#pragma pack(pop)

} // namespace nexussim
