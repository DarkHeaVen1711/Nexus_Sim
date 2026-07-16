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

    void clear() {
        points_.clear();
        nw_.reset(); ne_.reset(); sw_.reset(); se_.reset();
        divided_ = false;
    }

    size_t point_count() const {
        size_t c = points_.size();
        if (divided_)
            c += nw_->point_count() + ne_->point_count()
               + sw_->point_count() + se_->point_count();
        return c;
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
