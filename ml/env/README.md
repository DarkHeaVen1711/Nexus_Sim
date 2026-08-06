# ml/env — Environment Contract (Phase 7)

Gym-compatible training environment wrapping the offline Python
micro-simulator (`traffic_sim.py`). One RL agent controls each signalised
intersection; observations, actions, and rewards follow TR-ML-02/03/04.

## Observation space (TR-ML-02, Phase 7.1)

Each agent observes a flat, normalised vector of dimension **11**, with all
entries in `[0, 1]`:

| Index | Feature                  | Source                                  |
|-------|--------------------------|-----------------------------------------|
| 0     | queue, North approach    | queue length / `MAX_QUEUE` (50)         |
| 1     | queue, South approach    | queue length / `MAX_QUEUE` (50)         |
| 2     | queue, East approach     | queue length / `MAX_QUEUE` (50)         |
| 3     | queue, West approach     | queue length / `MAX_QUEUE` (50)         |
| 4     | phase index              | 0.0 / 1.0 (which approach pair is green)|
| 5     | time in phase            | seconds in phase / `decision_interval`  |
| 6     | time of day              | hour of day / 24.0 (0..1)               |
| 7     | neighbour pressure, North| in-degree pressure / `MAX_QUEUE`        |
| 8     | neighbour pressure, South| in-degree pressure / `MAX_QUEUE`        |
| 9     | neighbour pressure, East | in-degree pressure / `MAX_QUEUE`        |
| 10    | neighbour pressure, West | in-degree pressure / `MAX_QUEUE`        |

Gymnasium space: `spaces.Box(low=0.0, high=1.0, shape=(11,), dtype=np.float32)`.
Implementation: `observation.py` (`build_observation`, `OBSERVATION_DIM = 11`).

## Action space (TR-ML-03)

`spaces.Discrete(2)` per agent, applied at a GREEN phase boundary:

- `0` = EXTEND — keep the current phase green for another `decision_interval`
- `1` = SWITCH — go YELLOW → RED → switch to the other phase

## Reward (TR-ML-04, Phase 7.2)

`combined_reward(pressure_terms, zone_waits, alpha, beta, weights)` returns per
agent a weighted sum of:

- pressure term: negative mean queue length across approaches (efficiency),
- equity term: Gini-weighted reward that favours balanced zone waiting times.

`alpha` / `beta` control the efficiency–equity trade-off; baseline zone weights
come from `baseline_zone_weights(graph["baseline_zone_wait"])`.

## Env interface (Phase 7.3)

`NexusSimEnv` implements the standard Gymnasium interface:

- `reset()` → `(obs, info)`; `obs` is a dict `{intersection_id: np.ndarray(11)}`
- `step(actions)` → `(obs, rewards, terminated, truncated, info)`; rewards and
  actions are dicts keyed by intersection id
- `info` includes `mean_pressure`, `equity`, `gini`, `zone_wait`, `completed`

Toy demand and the micro-simulator live in `toy_graph.py` / `traffic_sim.py`.
