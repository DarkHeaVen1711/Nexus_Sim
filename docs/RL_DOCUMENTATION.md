# Reinforcement Learning (RL) — NexusSim Documentation

---

## Subject Overview

Reinforcement Learning is the core adaptive intelligence of NexusSim, providing learned signal-control policies that replace the fixed-cycle Webster's formula baseline. The RL subsystem trains decentralized multi-agent proximal policy optimization (MAPPO) agents—one per signalized intersection—that observe local traffic conditions and decide moment-to-moment whether to extend or switch signal phases. The system is expanded to a 12-algorithm inventory spanning tabular value, deep value, policy-gradient, actor-critic, and continuous-control families, all sharing a common training and evaluation harness.

**Key references:** `docs/TEAM_IMPLEMENTATION_PLAN.md` (Phases 7–9, 19–24), `docs/PRD.md` G2/G13, `docs/TRD.md` §4.3 (TR-ML-01 through TR-ML-19).

---

## Role in Project

The RL subsystem serves three critical roles in NexusSim:

1. **Primary adaptive signal controller:** Trained RL policies replace the non-adaptive Webster's fixed-cycle timing, producing a citywide average wait-time reduction target of ≥15% and an equity (Gini) improvement target of ≥10% (PRD §7).
2. **Academic breadth and depth:** The 12-algorithm inventory (FR-16) covers the major RL families required by the four-subject coursework, with nine signal-control algorithms benchmarked against a common baseline and three continuous-control algorithms demonstrated on a standard Gym environment.
3. **Integration anchor:** RL policies are the most latency-sensitive subsystem—they must run in the C++ hot path via ONNX inference with p95 ≤ 8 ms per tick (NFR-4)—and they demonstrate real-time responsiveness to NLP incident reports (Phase 17 → Phase 18 integration).

**TRD traceability:** TR-ML-01 through TR-ML-19 (§4.3), TR-ENG-09/12 (§4.1).

---

## Objectives

| ID | Objective | Phase(s) | Status | Acceptance Criteria |
|----|-----------|----------|--------|---------------------|
| O-RL-1 | Build a Gym-compatible multi-agent environment wrapping simulation state snapshots | 7 | IN PROGRESS | `NexusSimEnv` with `reset()`, `step()`, observation/action spaces; no live C++ call during training (TR-ML-01) |
| O-RL-2 | Design per-agent observation space: 4 queue lengths + 4 neighbor pressures + phase + time-in-phase + time-of-day (11-dim) | 7.1 | DONE | Flat vector in [0,1], shape (11,), unit tests in `ml/tests/test_observation.py` (TR-ML-02) |
| O-RL-3 | Implement reward function: `α × pressure_i + β × equity_global` with tunable tradeoff curve | 7.2 | DONE | `combined_reward()` returns per-agent rewards + components; Gini computed; unit tests in `ml/tests/test_reward.py` (TR-ML-04) |
| O-RL-4 | Build MAPPO trainer with shared-weight 3-layer MLP policy/value networks | 7.5 | DONE | `ppo_update()` and `collect_episode()` function; MLflow logging; checkpoint save/resume (TR-ML-05, TR-ML-06) |
| O-RL-5 | Train on toy 4-intersection graph; verify rising reward curve above Webster baseline | 7.8 | PENDING | MLflow reward curve rises within 500 episodes (Phase 7 checkpoint) |
| O-RL-6 | Export trained policy to ONNX and integrate C++ inference via `InferenceEngine` | 8 | PLANNED | ONNX parity with PyTorch on 10 inputs; p95 ≤ 8 ms (TR-ML-07, TR-ENG-12) |
| O-RL-7 | Deploy on full Chicago graph; generalize to Paris and Ahmedabad via transfer learning | 9 | PLANNED | MARL vs. Webster table across 3 cities (Phase 9 checkpoint) |
| O-RL-8 | Implement 12-algorithm shared harness (`BaseTrainer`, `benchmark.py`, `configs.yaml`) | 19 | PLANNED | `benchmark.py` prints comparison table + MLflow (TR-ML-11) |
| O-RL-9 | Train 5 value-based algorithms: Q-Learning, SARSA, DQN, DDQN, Dueling DQN | 20 | PLANNED | 5 eval reports vs. Webster (TR-ML-14, TR-ML-15) |
| O-RL-10 | Train 3 policy-based algorithms: REINFORCE, A2C, PPO | 21 | PLANNED | 8 signal-control algorithms in comparison table (TR-ML-16) |
| O-RL-11 | Showcase SAC/TD3/DDPG on Pendulum-v1 via Stable-Baselines3 | 22 | PLANNED | Return curves logged to MLflow (TR-ML-17) |
| O-RL-12 | Deploy MAPPO/PPO/DQN to C++ engine via ONNX; `--signal-policy rl --algo` dispatch | 23 | PLANNED | p95 ≤ 8 ms; dashboard PolicyComparisonPanel shows all three (TR-ML-18) |
| O-RL-13 | Document 12-algorithm inventory with ablation study in `docs/results.md` | 24 | PLANNED | Table + ablation (TR-ML-19) |

---

## Current Implementation

### Implemented Components (Phases 7.1–7.7)

**Observation space** (`ml/env/observation.py`):
```python
OBSERVATION_DIM = 11

def build_observation(
    queues: Sequence[float],       # 4 per-approach queue lengths
    phase: float,                  # current phase index (0.0 / 1.0)
    time_in_phase: float,          # seconds in phase, normalized
    time_of_day: float,            # hour-of-day, normalized 0..1
    neighbor_pressure: Sequence[float],  # 4 neighbor pressures
    max_queue: float,              # normalization denominator
) -> np.ndarray:
    return np.array(
        [q / max_queue for q in queues]
        + [float(phase), float(time_in_phase), float(time_of_day)]
        + [p / max_queue for p in neighbor_pressure],
        dtype=np.float32,
    )
```

**Reward function** (`ml/env/reward.py`):
```python
def combined_reward(pressure_terms, zone_waits, alpha, beta, zone_weights=None):
    equity = equity_term(zone_waits, zone_weights)
    rewards = [alpha * pressure + beta * equity for pressure in pressure_terms]
    return {
        "rewards": rewards,
        "mean_pressure": sum(pressure_terms) / len(pressure_terms),
        "equity": equity,
        "gini": gini_coefficient(zone_waits),
    }
```

**Signal controller state machine** (`ml/env/controller.py`):
- `IntersectionController`: GREEN/YELLOW/RED state machine with `decision_interval` (5.0s default), `yellow_time` (3.0s), `red_clearance` (2.0s).
- Decision at GREEN-phase boundary only: `is_decision_ready()` returns true when timer elapses.
- Action space: `ACTION_EXTEND = 0`, `ACTION_SWITCH = 1`.

**Toy graph** (`ml/env/toy_graph.py`):
- 4-intersection 2×2 grid with 4 approaches each (N, S, E, W).
- Hardcoded deterministic demand with AM/PM peaks (`time_of_day_factor`).
- Base rates: 0.30 veh/s on one heavy peripheral approach per intersection; alternating phases prevent trivial "always extend" solutions.
- Baseline zone waits: `[12.0, 15.0, 14.0, 18.0]` for equity weight computation.

**Traffic simulator** (`ml/env/traffic_sim.py`):
- Pure Python micro-simulator over the toy grid; no live C++ call.
- Per-approach Poisson arrivals, saturation-flow discharge through green, link travel times.
- `neighbor_pressures()` computes queue on each neighbor's approach feeding back toward the intersection.

**Gym environment** (`ml/env/nexus_sim_env.py`):
```python
class NexusSimEnv(gym.Env):
    observation_space = spaces.Box(low=0.0, high=1.0, shape=(11,), dtype=np.float32)
    action_space = spaces.Discrete(2)
    num_agents = 4  # one per intersection
```

**Policy/Value networks** (`ml/models/mappo_net.py`):
```python
class PolicyNetwork(nn.Module):  # 3-layer MLP, obs_dim → 64 → 64 → n_actions(2)
    def sample_action(self, obs) -> (actions, log_probs):
        probs = Categorical(logits=self.forward(obs))
        return probs.sample(), probs.log_prob(probs.sample())

class ValueNetwork(nn.Module):   # 3-layer MLP, obs_dim → 64 → 64 → 1
```

**PPO trainer** (`ml/train/ppo.py`):
- `compute_gae()`: Generalized Advantage Estimation (γ=0.99, λ=0.95).
- `ppo_update()`: Clipped surrogate objective, entropy bonus (0.01), value loss (MSE, coef 0.5), 4 epochs, batch size 256.

**Rollout collection** (`ml/train/rollout.py`):
- `collect_episode()`: Steps one episode, returns per-agent buffers (obs, act, logp, rew, val, done) concatenated into tensors.
- `FixedCycleBaseline()`: Holds each phase `switch_every` decision intervals (default 4), then switches. `evaluate_fixed_baseline()` returns mean episode reward/pressure/equity/gini.

**Training driver** (`ml/train/train.py`):
- CLI: `--city toy --episodes 1000 --alpha 1.0 --beta 1.0 --lr 5e-4 --gamma 0.95 --lam 0.95 --clip-eps 0.2 --entropy-coef 0.003 --hidden 64 --episodes-per-update 4 --reward-scale 0.0` (auto-scales from baseline).
- MLflow logging per episode: `episode_reward`, `mean_pressure`, `equity`, `gini`.
- Checkpoint save/resume: `ml/checkpoints/<city>/<episode>.pt`.
- Baseline evaluation: `--baseline-episodes 10` runs `FixedCycleBaseline` and prints comparison.

**Tests:**
- `test_observation.py`: dimension, unit range, normalization, dtype, error on bad input.
- `test_reward.py`: pressure, equity, Gini, combined reward components.
- `test_env.py`: observation/action spaces, reset/step, truncation, determinism, controller cycling.
- `test_ppo.py`: GAE shapes/values, PPO update runs, policy sampling, collect_episode buffers, baseline switching.
- `test_toy_graph.py`: graph structure, phase coverage, symmetry, time-of-day peaks.

**Requirements** (`ml/requirements.txt`):
```
numpy==1.26.4
torch==2.4.1
gymnasium==1.0.0
mlflow==2.16.2
pytest>=7.0
```

---

## Dependencies/Interfaces

### Upstream (what RL depends on)

| Dependency | Source | Interface | Status |
|------------|--------|-----------|--------|
| Simulation state snapshots | C++ engine via WebSocket (port 9001) | JSON: `{tick, agents, metrics:{avg_speed,active_agents,completed_agents,avg_wait_time,gini_coefficient}, zone_metrics}` | PLANNED (Phase 7.3 wraps this) |
| `graph.json` | Pipeline (`pipeline/src/export.py`) | Nodes with `zone_id`, edges with `length_m`/`lanes` | DONE (Phase 1) |
| `od_matrix.json` | Pipeline (`pipeline/src/od_matrix.py` or `od_proxy.py`) | Zone-pair hourly demand rates | DONE (Phase 6) |
| Signal controller | C++ `SignalController.h` | Phase state machine with GREEN/YELLOW/RED | DONE (Phase 5) |
| Quadtree | C++ `Quadtree.h` | Per-approach queue length queries | DONE (Phase 3) |

### Downstream (what depends on RL)

| Consumer | Interface | Status |
|----------|-----------|--------|
| ONNX policy file (`policy.onnx`) | PyTorch → ONNX export; consumed by `InferenceEngine.h` in C++ | PLANNED (Phase 8) |
| Dashboard `PolicyComparisonPanel.tsx` | Reads `mode` and `signals[]` from WebSocket broadcast; sends `policy_switch` control message | PLANNED (Phase 12.6) |
| NLP incident reports | Incidents mutate road conditions → RL observations change → policy reacts automatically | PLANNED (Phase 17 → 18 integration) |
| Eval reports (`ml/results/<algo>/eval_report.json`) | Reward, pressure, equity, Gini, avg wait, % change vs. Webster | PLANNED (Phase 19.4) |

### Internal module boundaries

| Module | Path | Exposes |
|--------|------|---------|
| `ml/env/` | `NexusSimEnv`, `observation`, `reward`, `controller`, `traffic_sim`, `toy_graph` | Gym env + reward + obs builder |
| `ml/models/` | `mappo_net.py` | `PolicyNetwork`, `ValueNetwork` |
| `ml/train/` | `ppo.py`, `rollout.py`, `train.py` | GAE, PPO update, episode collection, baseline eval |
| `ml/export/` | `export_onnx.py` (PLANNED) | PyTorch → ONNX |
| `ml/eval/` | `report.py` (PLANNED) | Per-algorithm eval report |
| `ml/algo/` | `configs.yaml`, `benchmark.py` (PLANNED) | Shared harness |

---

## Future Extension Points

1. **Full Chicago graph training (Phase 9.1):** Replace `build_toy_graph()` with `graph.json` loader; expect 2000–5000 episodes overnight.
2. **Multi-city transfer learning (Phase 9.3–9.5):** Fine-tune Chicago-trained policy on Paris/Ahmedabad graphs; document sensitivity to `chaos` coefficient.
3. **ONNX deployment (Phase 8):** `export_onnx.py` validates parity; `InferenceEngine.h` loads `policy.onnx`, batches observations, runs on background thread via ring buffer.
4. **12-algorithm harness (Phase 19):** `BaseTrainer` interface; `ml/env/single_agent.py` wraps multi-agent env for single-agent algorithms (DQN, PPO, Q-Learning).
5. **C++ `SignalPolicy` interface (Phase 12):** `SignalPolicy` with `tick()`, `is_green()`, `current_phase_index()`, `policy_name()`; `RLPolicy` implementation keyed by algorithm name.
6. **ONNX algorithm dispatch (Phase 23):** `InferenceEngine --algo dqn` runs argmax over Q outputs; `RLPolicy` slots into Phase 12 interface.
7. **Reward shaping with CV data (Phase 14 → 9):** `cv_congestion.json` feeds GA as additional fitness term; could also shape RL reward in future iterations.

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 7–9 | MARL environment, ONNX export, multi-city training |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 19–24 | Shared RL framework, 12 algorithms, C++ deployment, results |
| `docs/PRD.md` | G2, G13, §7 | MARL goals, success metrics |
| `docs/TRD.md` | §4.3 | TR-ML-01 through TR-ML-19, full requirement traceability |
| `docs/TECH_STACK.md` | §Subsystem 3 | PyTorch, Gymnasium, MAPPO, ONNX Runtime, MLflow |
| `ml/env/` | All files | Gym environment, observation, reward, controller, toy graph |
| `ml/models/mappo_net.py` | Full file | PolicyNetwork, ValueNetwork definitions |
| `ml/train/` | All files | PPO update, rollout collection, training driver |
| `ml/tests/` | All files | Unit tests for env, reward, observation, PPO, toy graph |

---

*This document is self-contained and independently updatable. Changes to other subject documentation files do not require changes here, and vice versa. Last updated: August 2026.*
