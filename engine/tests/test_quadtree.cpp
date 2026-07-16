#include <gtest/gtest.h>
#include "../src/spatial/Quadtree.h"
#include <vector>

using namespace nexussim;

TEST(QuadtreeTest, InsertAndQueryRadius) {
    Quadtree<double> qt(0.0, 0.0, 100.0, 100.0);

    // Insert 100 points in a 10x10 grid
    for (int r = 0; r < 10; ++r) {
        for (int c = 0; c < 10; ++c) {
            qt.insert(static_cast<double>(c * 10),
                      static_cast<double>(r * 10),
                      r * 10 + c);
        }
    }

    EXPECT_EQ(qt.point_count(), 100u);

    // Query circle centered at (50, 50) radius 15
    // Should return points within 15 units of (50,50):
    // (40,40) d=14.14, (50,40) d=10, (60,40) d=14.14
    // (40,50) d=10,    (50,50) d=0,   (60,50) d=10
    // (40,60) d=14.14, (50,60) d=10,  (60,60) d=14.14
    std::vector<QuadPoint<double>> results;
    qt.query_radius(50.0, 50.0, 15.0, results);
    EXPECT_EQ(results.size(), 9u);

    // Verify none of the returned points are outside radius
    for (const auto& p : results) {
        double dx = p.x - 50.0;
        double dy = p.y - 50.0;
        EXPECT_LE(dx * dx + dy * dy, 15.0 * 15.0 + 1e-9);
    }
}

TEST(QuadtreeTest, ClearAndReuse) {
    Quadtree<double> qt(0.0, 0.0, 50.0, 50.0);
    qt.insert(10.0, 10.0, 0);
    qt.insert(20.0, 20.0, 1);
    EXPECT_EQ(qt.point_count(), 2u);

    qt.clear();
    EXPECT_EQ(qt.point_count(), 0u);

    qt.insert(5.0, 5.0, 2);
    EXPECT_EQ(qt.point_count(), 1u);

    std::vector<QuadPoint<double>> results;
    qt.query_radius(5.0, 5.0, 1.0, results);
    EXPECT_EQ(results.size(), 1u);
    EXPECT_EQ(results[0].idx, 2u);
}

TEST(QuadtreeTest, Rebuild) {
    Quadtree<double> qt(0.0, 0.0, 10.0, 10.0);
    qt.insert(1.0, 1.0, 0);
    qt.insert(9.0, 9.0, 1);

    std::vector<double> xs = {2.0, 8.0};
    std::vector<double> ys = {2.0, 8.0};
    std::vector<size_t> ids = {10, 20};
    qt.rebuild(xs, ys, ids);

    EXPECT_EQ(qt.point_count(), 2u);
    std::vector<QuadPoint<double>> results;
    qt.query_radius(2.0, 2.0, 1.5, results);
    bool found = false;
    for (const auto& p : results) {
        if (p.idx == 10) found = true;
    }
    EXPECT_TRUE(found);
}

TEST(QuadtreeTest, EmptyQuery) {
    Quadtree<double> qt(0.0, 0.0, 100.0, 100.0);
    std::vector<QuadPoint<double>> results;
    qt.query_radius(50.0, 50.0, 10.0, results);
    EXPECT_TRUE(results.empty());
}

TEST(QuadtreeTest, BoundaryPoints) {
    Quadtree<double> qt(0.0, 0.0, 10.0, 10.0);
    qt.insert(0.0, 0.0, 0);
    qt.insert(9.99, 9.99, 1);
    qt.insert(10.0, 10.0, 2); // Outside bounds

    EXPECT_EQ(qt.point_count(), 2u);
}
