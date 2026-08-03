#pragma once
#include <vector>
#include <queue>
#include <unordered_map>
#include <cmath>
#include <limits>
#include <algorithm>
#include <random>
#include "../graph/Graph.h"

namespace nexussim {

struct AStarNode {
    int64_t id;
    double f_score;
    bool operator>(const AStarNode& other) const {
        return f_score > other.f_score;
    }
};

class Pathfinder {
public:
    static std::vector<int64_t> compute_path(const Graph& g, int64_t start, int64_t goal) {
        std::priority_queue<AStarNode, std::vector<AStarNode>, std::greater<AStarNode>> open_set;
        std::unordered_map<int64_t, int64_t> came_from;
        std::unordered_map<int64_t, double> g_score;
        std::unordered_map<int64_t, double> f_score;

        const Node* goal_node = g.get_node(goal);
        if (!goal_node) return {};

        open_set.push({start, 0.0});
        g_score[start] = 0.0;
        f_score[start] = heuristic(g.get_node(start), goal_node);

        while (!open_set.empty()) {
            int64_t current = open_set.top().id;
            
            if (current == goal) {
                return reconstruct_path(came_from, current);
            }
            open_set.pop();

            for (const auto& edge : g.get_edges_from(current)) {
                double tentative_g_score = g_score[current] + edge.length_m;
                
                if (g_score.find(edge.v) == g_score.end() || tentative_g_score < g_score[edge.v]) {
                    came_from[edge.v] = current;
                    g_score[edge.v] = tentative_g_score;
                    f_score[edge.v] = tentative_g_score + heuristic(g.get_node(edge.v), goal_node);
                    open_set.push({edge.v, f_score[edge.v]});
                }
            }
        }
        return {}; // No path found
    }

    // Stochastic route choice: A* over lognormally-perturbed edge costs, a
    // logit-style approximation of driver route preferences. Agents spread
    // across near-optimal alternatives instead of all taking the identical
    // shortest path, which prevents artificial queue concentration on a
    // single bottleneck (Phase 6 calibration).
    static std::vector<int64_t> compute_path_stochastic(
            const Graph& g, int64_t start, int64_t goal,
            std::mt19937& rng, double spread = 0.15) {
        if (spread <= 0.0) return compute_path(g, start, goal);
        std::lognormal_distribution<double> noise(0.0, spread);
        std::priority_queue<AStarNode, std::vector<AStarNode>, std::greater<AStarNode>> open_set;
        std::unordered_map<int64_t, int64_t> came_from;
        std::unordered_map<int64_t, double> g_score;
        std::unordered_map<int64_t, double> f_score;

        const Node* goal_node = g.get_node(goal);
        if (!goal_node) return {};

        open_set.push({start, 0.0});
        g_score[start] = 0.0;
        f_score[start] = heuristic(g.get_node(start), goal_node);

        while (!open_set.empty()) {
            int64_t current = open_set.top().id;
            if (current == goal) {
                return reconstruct_path(came_from, current);
            }
            open_set.pop();

            for (const auto& edge : g.get_edges_from(current)) {
                double tentative_g_score =
                    g_score[current] + edge.length_m * noise(rng);
                if (g_score.find(edge.v) == g_score.end()
                    || tentative_g_score < g_score[edge.v]) {
                    came_from[edge.v] = current;
                    g_score[edge.v] = tentative_g_score;
                    f_score[edge.v] = tentative_g_score
                        + heuristic(g.get_node(edge.v), goal_node);
                    open_set.push({edge.v, f_score[edge.v]});
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

    static std::vector<int64_t> reconstruct_path(const std::unordered_map<int64_t, int64_t>& came_from, int64_t current) {
        std::vector<int64_t> total_path = {current};
        while (came_from.find(current) != came_from.end()) {
            current = came_from.at(current);
            total_path.push_back(current);
        }
        std::reverse(total_path.begin(), total_path.end());
        return total_path;
    }
};

} // namespace nexussim
