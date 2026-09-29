"""Phase 35 - Algorithm Explorer API Sidecar Service (Port 9006).

Serves metadata, hyperparameter configurations, metrics, and live control APIs
for all 36 algorithms spanning CV, Soft Computing, NLP, and Reinforcement Learning.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="NexusSim Algorithm Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Canonical 36-Algorithm Inventory Registry
ALGORITHM_CATALOG: List[Dict[str, Any]] = [
    # Computer Vision (CV 1..12)
    {"id": "CV-1", "name": "Classical HSV Thresholding", "category": "CV", "status": "ACTIVE", "latency_ms": 1.2, "accuracy": "91.4%"},
    {"id": "CV-2", "name": "CNN Traffic Tile Classifier", "category": "CV", "status": "ACTIVE", "latency_ms": 3.8, "accuracy": "94.8%"},
    {"id": "CV-3", "name": "Top-Down Blob Detector", "category": "CV", "status": "ACTIVE", "latency_ms": 12.0, "accuracy": "97.5%"},
    {"id": "CV-4", "name": "DeepSORT Vehicle Tracker", "category": "CV", "status": "ACTIVE", "latency_ms": 16.5, "accuracy": "92.0%"},
    {"id": "CV-5", "name": "U-Net Road Mask Segmentation", "category": "CV", "status": "ACTIVE", "latency_ms": 22.1, "accuracy": "89.2% IoU"},
    {"id": "CV-6", "name": "Mask R-CNN Silhouettes", "category": "CV", "status": "ACTIVE", "latency_ms": 35.0, "accuracy": "88.6%"},
    {"id": "CV-7", "name": "Road Surface Hazard Perception", "category": "CV", "status": "ACTIVE", "latency_ms": 2.1, "accuracy": "95.0%"},
    {"id": "CV-8", "name": "Lucas-Kanade Optical Flow", "category": "CV", "status": "ACTIVE", "latency_ms": 8.4, "accuracy": "96.1%"},
    {"id": "CV-9", "name": "Traffic Anomaly Blockage Detector", "category": "CV", "status": "ACTIVE", "latency_ms": 4.2, "accuracy": "94.5%"},
    {"id": "CV-10", "name": "Lane Boundary Hough Detector", "category": "CV", "status": "ACTIVE", "latency_ms": 5.1, "accuracy": "91.0%"},
    {"id": "CV-11", "name": "Spatial Camera Alert Pipeline", "category": "CV", "status": "ACTIVE", "latency_ms": 2.0, "accuracy": "99.0%"},
    {"id": "CV-12", "name": "Pedestrian Crowd Density Estimator", "category": "CV", "status": "ACTIVE", "latency_ms": 6.3, "accuracy": "93.4%"},

    # Soft Computing (SC 1..12)
    {"id": "SC-1", "name": "Genetic Algorithm Calibration", "category": "SC", "status": "ACTIVE", "latency_ms": 150.0, "metric": "MAPE 18.3%"},
    {"id": "SC-2", "name": "Particle Swarm Optimization", "category": "SC", "status": "ACTIVE", "latency_ms": 95.0, "metric": "MAPE 16.8%"},
    {"id": "SC-3", "name": "Simulated Annealing Calibration", "category": "SC", "status": "ACTIVE", "latency_ms": 110.0, "metric": "MAPE 17.5%"},
    {"id": "SC-4", "name": "CMA-ES Evolution Strategy", "category": "SC", "status": "ACTIVE", "latency_ms": 120.0, "metric": "MAPE 16.2%"},
    {"id": "SC-5", "name": "Ant Colony System (ACS) Routing", "category": "SC", "status": "ACTIVE", "latency_ms": 45.0, "metric": "-6.2% travel time"},
    {"id": "SC-6", "name": "Artificial Bee Colony Split Optimizer", "category": "SC", "status": "ACTIVE", "latency_ms": 38.0, "metric": "+14% green balance"},
    {"id": "SC-7", "name": "ANFIS Neuro-Fuzzy Controller", "category": "SC", "status": "ACTIVE", "latency_ms": 1.5, "metric": "Wait 31.5s"},
    {"id": "SC-8", "name": "Symbolic GP Decision Rule Tree", "category": "SC", "status": "ACTIVE", "latency_ms": 0.05, "metric": "Wait 33.0s"},
    {"id": "SC-9", "name": "Rough Sets Observation Reduct", "category": "SC", "status": "ACTIVE", "latency_ms": 8.0, "metric": "72% feature reduction"},
    {"id": "SC-10", "name": "NSGA-II Pareto Multi-Objective", "category": "SC", "status": "ACTIVE", "latency_ms": 80.0, "metric": "Pareto frontier"},
    {"id": "SC-11", "name": "SC-Guided RL Warm Starting", "category": "SC", "status": "ACTIVE", "latency_ms": 15.0, "metric": "-40% warmup steps"},
    {"id": "SC-12", "name": "Mamdani Fuzzy Signal Policy", "category": "SC", "status": "ACTIVE", "latency_ms": 0.05, "metric": "Wait 32.1s (Gini 0.35)"},

    # Natural Language Processing (NLP 1..12)
    {"id": "NLP-1", "name": "Rule-Based Intent Classifier", "category": "NLP", "status": "ACTIVE", "latency_ms": 0.8, "accuracy": "96.4%"},
    {"id": "NLP-2", "name": "RapidFuzz Street Gazetteer Parser", "category": "NLP", "status": "ACTIVE", "latency_ms": 2.5, "accuracy": "93.1%"},
    {"id": "NLP-3", "name": "Citizen Sentiment Polarity Scorer", "category": "NLP", "status": "ACTIVE", "latency_ms": 1.1, "accuracy": "92.0%"},
    {"id": "NLP-4", "name": "LLM Metric Tool-Calling Layer", "category": "NLP", "status": "ACTIVE", "latency_ms": 140.0, "accuracy": "98.0%"},
    {"id": "NLP-5", "name": "Multinomial Naive Bayes Categorizer", "category": "NLP", "status": "ACTIVE", "latency_ms": 0.9, "accuracy": "91.5%"},
    {"id": "NLP-6", "name": "Interactive Live Q&A Stream", "category": "NLP", "status": "ACTIVE", "latency_ms": 1.2, "accuracy": "95.0%"},
    {"id": "NLP-7", "name": "Traffic Named Entity Recognition", "category": "NLP", "status": "ACTIVE", "latency_ms": 3.2, "accuracy": "94.2%"},
    {"id": "NLP-8", "name": "Structured Event Tuple Extractor", "category": "NLP", "status": "ACTIVE", "latency_ms": 2.8, "accuracy": "95.5%"},
    {"id": "NLP-9", "name": "Anaphora Coreference Resolver", "category": "NLP", "status": "ACTIVE", "latency_ms": 1.8, "accuracy": "89.0%"},
    {"id": "NLP-10", "name": "TextRank Condition Summarizer", "category": "NLP", "status": "ACTIVE", "latency_ms": 4.5, "accuracy": "90.5%"},
    {"id": "NLP-11", "name": "Grounded State QA Engine", "category": "NLP", "status": "ACTIVE", "latency_ms": 2.1, "accuracy": "94.0%"},
    {"id": "NLP-12", "name": "RDF Semantic Knowledge Graph", "category": "NLP", "status": "ACTIVE", "latency_ms": 3.0, "accuracy": "100% relational"},

    # Reinforcement Learning (RL 1..12)
    {"id": "RL-1", "name": "Decentralized MAPPO (Headline)", "category": "RL", "status": "DEPLOYED_C++", "latency_ms": 0.08, "metric": "+26.3% reward (Wait 28.4s)"},
    {"id": "RL-2", "name": "Tabular Q-Learning", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.02, "metric": "Wait 38.2s"},
    {"id": "RL-3", "name": "Tabular SARSA", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.02, "metric": "Wait 39.1s"},
    {"id": "RL-4", "name": "Deep Q-Network (DQN)", "category": "RL", "status": "DEPLOYED_C++", "latency_ms": 0.09, "metric": "Wait 33.4s"},
    {"id": "RL-5", "name": "Double DQN (DDQN)", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.09, "metric": "Wait 31.8s"},
    {"id": "RL-6", "name": "Dueling DQN", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.11, "metric": "Wait 30.5s"},
    {"id": "RL-7", "name": "REINFORCE Policy Gradient", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.06, "metric": "Wait 35.8s"},
    {"id": "RL-8", "name": "Advantage Actor-Critic (A2C)", "category": "RL", "status": "BENCHMARKED", "latency_ms": 0.08, "metric": "Wait 31.2s"},
    {"id": "RL-9", "name": "Single-Agent PPO", "category": "RL", "status": "DEPLOYED_C++", "latency_ms": 0.08, "metric": "Wait 28.4s"},
    {"id": "RL-10", "name": "Soft Actor-Critic (SAC)", "category": "RL", "status": "SHOWCASE", "latency_ms": 0.14, "metric": "Wait 27.5s"},
    {"id": "RL-11", "name": "Twin Delayed DDPG (TD3)", "category": "RL", "status": "SHOWCASE", "latency_ms": 0.13, "metric": "Wait 28.9s"},
    {"id": "RL-12", "name": "Deep Deterministic Policy Gradient (DDPG)", "category": "RL", "status": "SHOWCASE", "latency_ms": 0.12, "metric": "Wait 29.8s"},
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "algo_explorer", "port": 9006, "total_algorithms": len(ALGORITHM_CATALOG)}


@app.get("/algorithms")
def get_all_algorithms(category: str | None = None):
    if category:
        return [a for a in ALGORITHM_CATALOG if a["category"].lower() == category.lower()]
    return ALGORITHM_CATALOG


class AlgoToggleRequest(BaseModel):
    algo_id: str
    active: bool


@app.post("/algorithms/toggle")
def toggle_algorithm(req: AlgoToggleRequest):
    for a in ALGORITHM_CATALOG:
        if a["id"] == req.algo_id:
            a["status"] = "ACTIVE" if req.active else "DISABLED"
            return {"status": "updated", "algo": a}
    return {"status": "error", "message": f"Algorithm {req.algo_id} not found"}


def main():
    print("Starting Algorithm Explorer API Sidecar on port 9006...")
    uvicorn.run(app, host="0.0.0.0", port=9006, log_level="info")


if __name__ == "__main__":
    main()
