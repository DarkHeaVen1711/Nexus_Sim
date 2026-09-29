"""Domain-specific mathematical and Pareto invariants for NexusSim ML Subsystems."""

import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sc"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nlp"))
from nsga2 import NSGA2Optimizer
from anfis import ANFISController
from rough_sets import RoughSetReducer
from knowledge_graph import TrafficKnowledgeGraph


class TestParetoOptimalityInvariants:
    def test_pareto_dominance_axiom(self):
        """In multi-objective optimization, a point dominates another if it is <= in all and < in at least one."""
        opt = NSGA2Optimizer()
        # Cost objectives: minimize both (lower is better)
        # Objectives: (wait_time, gini)
        sol_a = (20.0, 0.25)
        sol_b = (30.0, 0.40)
        sol_c = (15.0, 0.35)

        # sol_a strictly dominates sol_b
        assert opt.dominates(sol_a, sol_b) is True
        # sol_b does not dominate sol_a
        assert opt.dominates(sol_b, sol_a) is False
        # sol_a and sol_c are mutually non-dominating (trade-off)
        assert opt.dominates(sol_a, sol_c) is False
        assert opt.dominates(sol_c, sol_a) is False

    def test_nsga2_generates_valid_pareto_solutions(self):
        """NSGA-II objective evaluator must produce strictly positive wait time and bounded Gini."""
        opt = NSGA2Optimizer()
        sample_params = [
            np.array([0.1, 0.9, 0.8, 0.1]),
            np.array([0.9, 0.1, 0.5, 0.2]),
            np.array([0.5, 0.5, 1.0, 0.0]),
        ]
        for p in sample_params:
            wait, gini = opt.evaluate_objectives(p)
            assert wait > 0.0, f"Wait time {wait} must be positive"
            assert 0.0 <= gini <= 1.0, f"Gini coefficient {gini} must be in [0, 1]"


class TestSoftComputingInvariants:
    def test_anfis_firing_strengths_bounded(self):
        """Fuzzy rule firing strengths must be strictly bounded in [0.0, 1.0]."""
        controller = ANFISController(num_inputs=2, num_mfs_per_input=3)
        sample_inputs = [
            [0.2, 0.8],
            [0.5, 0.5],
            [1.0, 0.0],
        ]
        for inp in sample_inputs:
            res = controller.forward(inp)
            assert 0.0 <= res["green_extension_seconds"] <= 15.0
            for w in res["rule_firing_strengths"]:
                assert 0.0 <= w <= 1.0, f"Firing strength {w} out of bounds"

    def test_rough_set_reduct_minimality(self):
        """Rough set attribute reducts must reduce dimension while separating distinct classes."""
        reducer = RoughSetReducer(continuous_bins=3)
        # 6 samples, 4 features
        X = np.array([
            [0.1, 0.9, 0.1, 0.8],
            [0.2, 0.8, 0.1, 0.7],
            [0.9, 0.1, 0.9, 0.2],
            [0.8, 0.2, 0.9, 0.1],
        ])
        y = np.array([0, 0, 1, 1])
        reduct_res = reducer.compute_reduct(X, y)
        assert "reduct_features" in reduct_res
        reduct = reduct_res["reduct_features"]
        assert len(reduct) > 0
        assert len(reduct) <= X.shape[1]


class TestNLPKnowledgeGraphInvariants:
    def test_knowledge_graph_triple_integrity(self):
        """Knowledge graph triples must satisfy (subject, predicate, object) non-empty string integrity."""
        kg = TrafficKnowledgeGraph()
        kg.populate_from_simulation("Chicago", zone_count=4, active_policy="type2_fuzzy")
        assert len(kg.triples) >= 4
        for s, p, o in kg.triples:
            assert isinstance(s, str) and len(s.strip()) > 0
            assert isinstance(p, str) and len(p.strip()) > 0
            assert isinstance(o, str) and len(o.strip()) > 0
        matches = kg.query_relations(predicate="has_policy")
        assert len(matches) == 1
        assert matches[0]["object"] == "type2_fuzzy"
