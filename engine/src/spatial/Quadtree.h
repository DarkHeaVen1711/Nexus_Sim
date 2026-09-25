#pragma once
#include <vector>
#include <array>
#include <cmath>
#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace nexussim {

template <typename T = double>
struct QuadPoint {
    T x, y;
    size_t idx;
};

template <typename T = double>
class Quadtree {
    struct Bounds {
        T x, y, w, h;
        bool contains(T px, T py) const {
            return px >= x && px < x + w && py >= y && py < y + h;
        }
        bool intersects_circle(T cx, T cy, T r) const {
            T nx = std::max(x, std::min(cx, x + w));
            T ny = std::max(y, std::min(cy, y + h));
            T dx = cx - nx;
            T dy = cy - ny;
            return (dx * dx + dy * dy) <= (r * r);
        }
    };

    static constexpr size_t CAPACITY = 16;

    struct Node {
        Bounds bounds;
        std::vector<QuadPoint<T>> points;
        int32_t child_base{-1};
        bool is_leaf() const { return child_base == -1; }
    };

    std::vector<Node> nodes_;

public:
    explicit Quadtree(T x, T y, T w, T h) {
        nodes_.push_back({Bounds{x, y, w, h}, {}, -1});
    }

    void insert(T px, T py, size_t agent_idx) {
        if (nodes_.empty()) return;
        insert_recursive(0, px, py, agent_idx);
    }

    void query_radius(T cx, T cy, T r, std::vector<QuadPoint<T>>& out) const {
        if (nodes_.empty()) return;
        query_radius_recursive(0, cx, cy, r, out);
    }

    void clear() {
        if (!nodes_.empty()) {
            Bounds root_b = nodes_[0].bounds;
            nodes_.clear();
            nodes_.push_back({root_b, {}, -1});
        }
    }

    size_t point_count() const {
        if (nodes_.empty()) return 0;
        return count_recursive(0);
    }

    void rebuild(const std::vector<T>& xs,
                 const std::vector<T>& ys,
                 const std::vector<size_t>& indices) {
        nodes_.clear();
        if (xs.empty()) return;
        T min_x = xs[0], max_x = xs[0], min_y = ys[0], max_y = ys[0];
        for (size_t i = 1; i < xs.size(); ++i) {
            min_x = std::min(min_x, xs[i]);
            max_x = std::max(max_x, xs[i]);
            min_y = std::min(min_y, ys[i]);
            max_y = std::max(max_y, ys[i]);
        }
        T pad = static_cast<T>(1.0);
        nodes_.push_back({Bounds{min_x - pad, min_y - pad,
                                 max_x - min_x + 2 * pad,
                                 max_y - min_y + 2 * pad}, {}, -1});
        for (size_t i = 0; i < xs.size(); ++i) {
            insert(xs[i], ys[i], indices[i]);
        }
    }

private:
    void subdivide(size_t node_idx) {
        Bounds b = nodes_[node_idx].bounds;
        T hx = b.w / static_cast<T>(2);
        T hy = b.h / static_cast<T>(2);
        int32_t child_base = static_cast<int32_t>(nodes_.size());
        nodes_.resize(nodes_.size() + 4);
        nodes_[child_base + 0] = {Bounds{b.x, b.y, hx, hy}, {}, -1};
        nodes_[child_base + 1] = {Bounds{b.x + hx, b.y, hx, hy}, {}, -1};
        nodes_[child_base + 2] = {Bounds{b.x, b.y + hy, hx, hy}, {}, -1};
        nodes_[child_base + 3] = {Bounds{b.x + hx, b.y + hy, hx, hy}, {}, -1};
        nodes_[node_idx].child_base = child_base;

        std::vector<QuadPoint<T>> old_points = std::move(nodes_[node_idx].points);
        nodes_[node_idx].points.clear();

        for (const auto& p : old_points) {
            insert_children(child_base, p.x, p.y, p.idx);
        }
    }

    void insert_children(int32_t child_base, T px, T py, size_t agent_idx) {
        for (int i = 0; i < 4; ++i) {
            if (nodes_[child_base + i].bounds.contains(px, py)) {
                insert_recursive(child_base + i, px, py, agent_idx);
                return;
            }
        }
    }

    void insert_recursive(size_t node_idx, T px, T py, size_t agent_idx) {
        if (!nodes_[node_idx].bounds.contains(px, py)) return;
        if (nodes_[node_idx].is_leaf()) {
            if (nodes_[node_idx].points.size() < CAPACITY) {
                nodes_[node_idx].points.push_back({px, py, agent_idx});
                return;
            }
            subdivide(node_idx);
            insert_children(nodes_[node_idx].child_base, px, py, agent_idx);
            return;
        }
        insert_children(nodes_[node_idx].child_base, px, py, agent_idx);
    }

    void query_radius_recursive(size_t node_idx, T cx, T cy, T r, std::vector<QuadPoint<T>>& out) const {
        if (node_idx >= nodes_.size() || !nodes_[node_idx].bounds.intersects_circle(cx, cy, r)) return;
        const auto& node = nodes_[node_idx];
        for (const auto& p : node.points) {
            T dx = p.x - cx;
            T dy = p.y - cy;
            if (dx * dx + dy * dy <= r * r) {
                out.push_back(p);
            }
        }
        if (!node.is_leaf()) {
            int32_t base = node.child_base;
            query_radius_recursive(base + 0, cx, cy, r, out);
            query_radius_recursive(base + 1, cx, cy, r, out);
            query_radius_recursive(base + 2, cx, cy, r, out);
            query_radius_recursive(base + 3, cx, cy, r, out);
        }
    }

    size_t count_recursive(size_t node_idx) const {
        if (node_idx >= nodes_.size()) return 0;
        const auto& node = nodes_[node_idx];
        size_t cnt = node.points.size();
        if (!node.is_leaf()) {
            int32_t base = node.child_base;
            cnt += count_recursive(base + 0) + count_recursive(base + 1)
                 + count_recursive(base + 2) + count_recursive(base + 3);
        }
        return cnt;
    }
};

} // namespace nexussim
