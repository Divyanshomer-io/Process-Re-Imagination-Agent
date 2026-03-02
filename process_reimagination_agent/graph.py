from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from process_reimagination_agent.config import Settings, get_settings
from process_reimagination_agent.nodes import (
    Blueprint_Node,
    Human_Escalation_Node,
    Input_Refiner_Node,
    Quality_Control_Node,
    friction_points_node,
    path_classifier_node,
    quality_route,
)
from process_reimagination_agent.state import AgentState


def build_graph(
    checkpointer: BaseCheckpointSaver,
    settings: Settings | None = None,
    *,
    interrupt_before_blueprint: bool = True,
) -> CompiledStateGraph:
    """Build and compile the non-linear LangGraph workflow."""
    runtime_settings = settings or get_settings()

    graph = StateGraph(AgentState)
    graph.add_node("friction_points_node", lambda state: friction_points_node(state, runtime_settings))
    graph.add_node("Input_Refiner_Node", lambda state: Input_Refiner_Node(state, runtime_settings))
    graph.add_node("path_classifier_node", lambda state: path_classifier_node(state, runtime_settings))
    graph.add_node("Quality_Control_Node", lambda state: Quality_Control_Node(state, runtime_settings))
    graph.add_node("Blueprint_Node", lambda state: Blueprint_Node(state, runtime_settings))
    graph.add_node("Human_Escalation_Node", lambda state: Human_Escalation_Node(state, runtime_settings))

    graph.add_edge(START, "friction_points_node")
    graph.add_edge("friction_points_node", "path_classifier_node")
    graph.add_edge("path_classifier_node", "Quality_Control_Node")

    # Mandatory quality-control loop:
    # confidence > 95% => Blueprint
    # confidence <= 95% => Input Refiner -> Architect
    # loop cap exceeded => Human Escalation
    graph.add_conditional_edges(
        "Quality_Control_Node",
        quality_route,
        {
            "blueprint": "Blueprint_Node",
            "refine": "Input_Refiner_Node",
            "escalate": "Human_Escalation_Node",
        },
    )
    graph.add_edge("Input_Refiner_Node", "path_classifier_node")
    graph.add_edge("Blueprint_Node", END)
    graph.add_edge("Human_Escalation_Node", END)

    compile_kwargs: dict[str, Any] = {"checkpointer": checkpointer}
    if interrupt_before_blueprint:
        compile_kwargs["interrupt_before"] = ["Blueprint_Node"]
    return graph.compile(**compile_kwargs)
