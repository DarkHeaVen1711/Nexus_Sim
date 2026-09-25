#pragma once
#include <vector>
#include <queue>
#include <unordered_map>
#include <cmath>
#include <limits>
#include <algorithm>
#include <random>
#include <cstdint>
#include "../graph/Graph.h"

namespace nexussim {

struct AStarNode {
    int64_t id;
    double f_score;
    bool operator>(const AStarNode& other) const {
        return f_score > other.f_score;
    }
};

struct PathfinderState {
    double g_score;
    double f_score;
    int64_t came_from;
    uint32_t session;
};

class Pathfinder {
    struct ThreadContext {
        std::unordered_map<int64_t, PathfinderState> node_state;
        std::priority_queue<AStarNode, std::vector<AStarNode>, std::greater<AStarNode>> open_set;
        uint32_t current_session{0};

        void reset_session() {
            ++current_session;
            if (current_session == 0) {
                node_state.clear();
                current_session = 1;
            }
            while (!open_set.empty()) open_set.pop();
        }
    };

    static ThreadContext& get_context() {
        static thread_local ThreadContext ctx;
        return ctx;
    }

public:
    static std::vector<int64_t> compute_path(const Graph& g, int64_t start, int64_t goal) {
        const Node* goal_node = g.get_node(goal);
        if (!goal_node) return {};

        ThreadContext& ctx = get_context();
        ctx.reset_session();
        uint32_t sess = ctx.current_session;
        auto& state_map = ctx.node_state;
        auto& open_set = ctx.open_set;

        double h_start = heuristic(g.get_node(start), goal_node);
        state_map[start] = {0.0, h_start, -1, sess};
        open_set.push({start, h_start});

        while (!open_set.empty()) {
            int64_t current = open_set.top().id;
            double cur_f = open_set.top().f_score;
            open_set.pop();

            auto it = state_map.find(current);
            if (it != state_map.end() && it->second.session == sess && it->second.f_score < cur_f - 1e-9) {
                continue;
            }

            if (current == goal) {
                return reconstruct_path(state_map, current, sess);
            }

            double current_g = (it != state_map.end() && it->second.session == sess) ? it->second.g_score : 0.0;

            for (const auto& edge : g.get_edges_from(current)) {
                double tentative_g_score = current_g + edge.length_m;
                auto v_it = state_map.find(edge.v);
                bool visited = (v_it != state_map.end() && v_it->second.session == sess);
                
                if (!visited || tentative_g_score < v_it->second.g_score) {
                    double f = tentative_g_score + heuristic(g.get_node(edge.v), goal_node);
                    state_map[edge.v] = {tentative_g_score, f, current, sess};
                    open_set.push({edge.v, f});
                }
            }
        }
        return {};
    }

    static std::vector<int64_t> compute_path_stochastic(
            const Graph& g, int64_t start, int64_t goal,
            std::mt19937& rng, double spread = 0.15) {
        if (spread <= 0.0) return compute_path(g, start, goal);
        std::lognormal_distribution<double> noise(0.0, spread);

        const Node* goal_node = g.get_node(goal);
        if (!goal_node) return {};

        ThreadContext& ctx = get_context();
        ctx.reset_session();
        uint32_t sess = ctx.current_session;
        auto& state_map = ctx.node_state;
        auto& open_set = ctx.open_set;

        double h_start = heuristic(g.get_node(start), goal_node);
        state_map[start] = {0.0, h_start, -1, sess};
        open_set.push({start, h_start});

        while (!open_set.empty()) {
            int64_t current = open_set.top().id;
            double cur_f = open_set.top().f_score;
            open_set.pop();

            auto it = state_map.find(current);
            if (it != state_map.end() && it->second.session == sess && it->second.f_score < cur_f - 1e-9) {
                continue;
            }

            if (current == goal) {
                return reconstruct_path(state_map, current, sess);
            }

            double current_g = (it != state_map.end() && it->second.session == sess) ? it->second.g_score : 0.0;

            for (const auto& edge : g.get_edges_from(current)) {
                double tentative_g_score = current_g + edge.length_m * noise(rng);
                auto v_it = state_map.find(edge.v);
                bool visited = (v_it != state_map.end() && v_it->second.session == sess);

                if (!visited || tentative_g_score < v_it->second.g_score) {
                    double f = tentative_g_score + heuristic(g.get_node(edge.v), goal_node);
                    state_map[edge.v] = {tentative_g_score, f, current, sess};
                    open_set.push({edge.v, f});
                }
            }
        }
        return {};
    }

private:
    static double heuristic(const Node* a, const Node* b) {
        if (!a || !b) return 0.0;
        return std::hypot(a->x - b->x, a->y - b->y);
    }

    static std::vector<int64_t> reconstruct_path(const std::unordered_map<int64_t, PathfinderState>& state_map, int64_t current, uint32_t sess) {
        std::vector<int64_t> total_path;
        total_path.push_back(current);
        while (true) {
            auto it = state_map.find(current);
            if (it == state_map.end() || it->second.session != sess || it->second.came_from == -1) {
                break;
            }
            current = it->second.came_from;
            total_path.push_back(current);
        }
        std::reverse(total_path.begin(), total_path.end());
        return total_path;
    }
};

} // namespace nexussim
