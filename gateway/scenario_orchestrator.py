"""
Scenario Orchestrator — Multi-Engine Lifecycle & Time-Machine Branching.

Manages dynamic engine port allocation (:9100-:9900), child process lifecycle,
and tick-level state branching for what-if scenarios (Blueprint 2 / Phase 7.4).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scenario_orchestrator")


@dataclass
class EngineInstance:
    simulation_id: str
    parent_id: Optional[str] = None
    forked_at_tick: Optional[int] = None
    city: str = "chicago"
    port: int = 9001
    status: str = "running"
    created_at: float = field(default_factory=time.time)
    mutations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScenarioOrchestrator:
    """Manages ephemeral engine pools and scenario forks."""

    def __init__(self, base_port: int = 9100, max_instances: int = 32):
        self.base_port = base_port
        self.max_instances = max_instances
        self.instances: Dict[str, EngineInstance] = {}
        self.allocated_ports: set[int] = set()

    def allocate_port(self) -> int:
        for offset in range(self.max_instances):
            p = self.base_port + offset
            if p not in self.allocated_ports:
                self.allocated_ports.add(p)
                return p
        raise RuntimeError("No available engine ports in ephemeral pool")

    def release_port(self, port: int) -> None:
        self.allocated_ports.discard(port)

    def register_instance(
        self,
        simulation_id: str,
        city: str = "chicago",
        port: int = 9001,
        parent_id: Optional[str] = None,
        forked_at_tick: Optional[int] = None,
        mutations: Optional[List[Dict[str, Any]]] = None,
    ) -> EngineInstance:
        inst = EngineInstance(
            simulation_id=simulation_id,
            parent_id=parent_id,
            forked_at_tick=forked_at_tick,
            city=city,
            port=port,
            status="running",
            mutations=mutations or [],
        )
        self.instances[simulation_id] = inst
        return inst

    def fork_scenario(
        self,
        parent_id: str,
        target_tick: int,
        mutations: Optional[List[Dict[str, Any]]] = None,
    ) -> EngineInstance:
        """Forks a child simulation from parent at target_tick with mutations."""
        parent = self.instances.get(parent_id)
        city = parent.city if parent else "chicago"
        child_id = f"sim-{uuid.uuid4().hex[:8]}"
        child_port = self.allocate_port()

        child = self.register_instance(
            simulation_id=child_id,
            city=city,
            port=child_port,
            parent_id=parent_id,
            forked_at_tick=target_tick,
            mutations=mutations or [],
        )
        logger.info(
            f"Forked scenario {child_id} from {parent_id} at tick {target_tick} on port {child_port}"
        )
        return child

    def terminate_instance(self, simulation_id: str) -> bool:
        inst = self.instances.pop(simulation_id, None)
        if not inst:
            return False
        self.release_port(inst.port)
        inst.status = "terminated"
        return True

    def get_instance(self, simulation_id: str) -> Optional[EngineInstance]:
        return self.instances.get(simulation_id)

    def list_instances(self) -> List[Dict[str, Any]]:
        return [
            {
                "simulation_id": inst.simulation_id,
                "parent_id": inst.parent_id,
                "forked_at_tick": inst.forked_at_tick,
                "city": inst.city,
                "port": inst.port,
                "status": inst.status,
                "mutations_count": len(inst.mutations),
                "created_at": inst.created_at,
            }
            for inst in self.instances.values()
        ]


orchestrator = ScenarioOrchestrator()
