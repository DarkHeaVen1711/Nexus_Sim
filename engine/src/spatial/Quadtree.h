#pragma once
#include <vector>
#include <memory>
#include <cmath>
#include <algorithm>
#include <cstddef>

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

    static constexpr int CAPACITY = 16;
    Bounds bounds_;
    std::vector<QuadPoint<T>> points_;
    std::unique_ptr<Quadtree> nw_, ne_, sw_, se_;
    bool divided_ = false;

public:
    explicit Quadtree(T x, T y, T w, T h)
        : bounds_{x, y, w, h} {}

    void insert(T px, T py, size_t agent_idx) {
        if (!bounds_.contains(px, py)) return;
        if (points_.size() < CAPACITY && !divided_) {
            points_.push_back({px, py, agent_idx});
            return;
        }
        if (!divided_) subdivide();
        nw_->insert(px, py, agent_idx);
        ne_->insert(px, py, agent_idx);
        sw_->insert(px, py, agent_idx);
        se_->insert(px, py, agent_idx);
    }

    void query_radius(T cx, T cy, T r,
                      std::vector<QuadPoint<T>>& out) const {
        if (!bounds_.intersects_circle(cx, cy, r)) return;
        for (const auto& p : points_) {
            T dx = p.x - cx;
            T dy = p.y - cy;
            if (dx * dx + dy * dy <= r * r)
                out.push_back(p);
        }
        if (divided_) {
            nw_->query_radius(cx, cy, r, out);
            ne_->query_radius(cx, cy, r, out);
            sw_->query_radius(cx, cy, r, out);
            se_->query_radius(cx, cy, r, out);
        }
    }

    void clear() {
        points_.clear();
        nw_.reset(); ne_.reset(); sw_.reset(); se_.reset();
        divided_ = false;
    }

    void rebuild(const std::vector<T>& xs,
                 const std::vector<T>& ys,
                 const std::vector<size_t>& indices) {
        clear();
        if (xs.empty()) return;
        T min_x = xs[0], max_x = xs[0], min_y = ys[0], max_y = ys[0];
        for (size_t i = 1; i < xs.size(); ++i) {
            min_x = std::min(min_x, xs[i]);
            max_x = std::max(max_x, xs[i]);
            min_y = std::min(min_y, ys[i]);
            max_y = std::max(max_y, ys[i]);
        }
        T pad = static_cast<T>(1.0);
        bounds_ = {min_x - pad, min_y - pad,
                   max_x - min_x + 2 * pad,
                   max_y - min_y + 2 * pad};
        divided_ = false;
        for (size_t i = 0; i < xs.size(); ++i)
            insert(xs[i], ys[i], indices[i]);
    }

private:
    void subdivide() {
        T hx = bounds_.w / static_cast<T>(2);
        T hy = bounds_.h / static_cast<T>(2);
        nw_ = std::make_unique<Quadtree>(bounds_.x, bounds_.y, hx, hy);
        ne_ = std::make_unique<Quadtree>(bounds_.x + hx, bounds_.y, hx, hy);
        sw_ = std::make_unique<Quadtree>(bounds_.x, bounds_.y + hy, hx, hy);
        se_ = std::make_unique<Quadtree>(bounds_.x + hx, bounds_.y + hy, hx, hy);
        divided_ = true;
        for (const auto& p : points_) {
            nw_->insert(p.x, p.y, p.idx);
            ne_->insert(p.x, p.y, p.idx);
            sw_->insert(p.x, p.y, p.idx);
            se_->insert(p.x, p.y, p.idx);
        }
        points_.clear();
    }
};

} // namespace nexussim
