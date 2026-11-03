#pragma once
#include <cstdint>
#include <vector>
#include <array>
#include <cstring>
#include <chrono>
#include "Agent.h"

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

inline uint32_t calculate_crc32(const uint8_t* data, size_t length) {
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (int j = 0; j < 8; ++j) {
            crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        }
    }
    return ~crc;
}

inline std::vector<AgentSnapshotRecord> pack_agents(const AgentSystem& agents) {
    std::vector<AgentSnapshotRecord> records;
    size_t count = agents.size();
    records.reserve(count);
    for (size_t i = 0; i < count; ++i) {
        AgentSnapshotRecord r{};
        r.id = agents.id[i];
        r.current_edge_idx = agents.current_edge_idx[i];
        r.position = agents.position[i];
        r.velocity = agents.velocity[i];
        r.wait_time = agents.wait_time[i];
        r.state = static_cast<uint8_t>(agents.state[i]);
        r.type = static_cast<uint8_t>(agents.type[i]);
        r.lane = agents.lane[i];
        records.push_back(r);
    }
    return records;
}

inline void unpack_agents(const std::vector<AgentSnapshotRecord>& records, AgentSystem& agents) {
    // Fast in-place update if sizes match, otherwise clear and populate
    if (agents.size() == records.size()) {
        for (size_t i = 0; i < records.size(); ++i) {
            agents.id[i] = records[i].id;
            agents.current_edge_idx[i] = records[i].current_edge_idx;
            agents.position[i] = records[i].position;
            agents.velocity[i] = records[i].velocity;
            agents.wait_time[i] = records[i].wait_time;
            agents.state[i] = static_cast<AgentState>(records[i].state);
            agents.type[i] = static_cast<AgentType>(records[i].type);
            agents.lane[i] = records[i].lane;
        }
    } else {
        agents.id.clear();
        agents.origin.clear();
        agents.destination.clear();
        agents.type.clear();
        agents.state.clear();
        agents.position.clear();
        agents.velocity.clear();
        agents.target_speed.clear();
        agents.current_edge_idx.clear();
        agents.lane.clear();
        agents.wait_time.clear();
        agents.start_time.clear();
        agents.journey_time.clear();
        agents.cur_edge_len.clear();
        agents.path.clear();

        for (const auto& r : records) {
            agents.add_agent(r.id, 0, 0, static_cast<AgentType>(r.type));
            size_t idx = agents.size() - 1;
            agents.current_edge_idx[idx] = r.current_edge_idx;
            agents.position[idx] = r.position;
            agents.velocity[idx] = r.velocity;
            agents.wait_time[idx] = r.wait_time;
            agents.state[idx] = static_cast<AgentState>(r.state);
            agents.lane[idx] = r.lane;
        }
    }
}

class SnapshotRingBuffer {
public:
    static constexpr size_t DEFAULT_CAPACITY = 120; // 120 snapshots (e.g. 2 minutes at 10 ticks/interval)

    explicit SnapshotRingBuffer(size_t capacity = DEFAULT_CAPACITY)
        : capacity_(capacity > 0 ? capacity : DEFAULT_CAPACITY),
          buffers_(capacity > 0 ? capacity : DEFAULT_CAPACITY),
          tick_index_(capacity > 0 ? capacity : DEFAULT_CAPACITY, 0),
          valid_slots_(capacity > 0 ? capacity : DEFAULT_CAPACITY, false),
          head_(0), count_(0) {}

    size_t capacity() const { return capacity_; }
    size_t size() const { return count_; }
    bool empty() const { return count_ == 0; }

    std::vector<uint64_t> get_available_ticks() const {
        std::vector<uint64_t> ticks;
        ticks.reserve(count_);
        if (count_ == 0) return ticks;

        size_t start = (head_ + capacity_ - count_) % capacity_;
        for (size_t i = 0; i < count_; ++i) {
            size_t idx = (start + i) % capacity_;
            if (valid_slots_[idx]) {
                ticks.push_back(tick_index_[idx]);
            }
        }
        return ticks;
    }

    bool has_tick(uint64_t tick) const {
        for (size_t i = 0; i < capacity_; ++i) {
            if (valid_slots_[i] && tick_index_[i] == tick) {
                return true;
            }
        }
        return false;
    }

    void clear() {
        head_ = 0;
        count_ = 0;
        std::fill(valid_slots_.begin(), valid_slots_.end(), false);
        std::fill(tick_index_.begin(), tick_index_.end(), 0);
    }

private:
    size_t capacity_;
    std::vector<std::vector<uint8_t>> buffers_;
    std::vector<uint64_t> tick_index_;
    std::vector<bool> valid_slots_;
    size_t head_;
    size_t count_;
};

} // namespace nexussim
