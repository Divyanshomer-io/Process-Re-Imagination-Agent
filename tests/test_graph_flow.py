import pytest
import re

langgraph = pytest.importorskip("langgraph")
from langgraph.checkpoint.memory import MemorySaver

from process_reimagination_agent.config import Settings
from process_reimagination_agent.graph import build_graph
from process_reimagination_agent.models import InputManifest
from process_reimagination_agent.nodes import Quality_Control_Node
from process_reimagination_agent.state import create_initial_state


def test_quality_control_routes_to_refiner_on_low_confidence() -> None:
    state = {"confidence_score": 0.90, "refinement_iterations": 0, "phase_status": {}, "quality_feedback": [], "errors": []}
    updated = Quality_Control_Node(state, Settings(confidence_threshold=0.95, max_refinement_loops=3))
    assert updated["quality_gate_result"] == "refine"


def test_quality_control_routes_to_blueprint_on_high_confidence() -> None:
    state = {"confidence_score": 0.97, "refinement_iterations": 0, "phase_status": {}, "quality_feedback": [], "errors": []}
    updated = Quality_Control_Node(state, Settings(confidence_threshold=0.95, max_refinement_loops=3))
    assert updated["quality_gate_result"] == "blueprint"


def test_quality_control_escalates_when_loop_cap_reached() -> None:
    state = {"confidence_score": 0.90, "refinement_iterations": 3, "phase_status": {}, "quality_feedback": [], "errors": []}
    updated = Quality_Control_Node(state, Settings(confidence_threshold=0.95, max_refinement_loops=3))
    assert updated["quality_gate_result"] == "escalate"
    assert updated["errors"]


def test_graph_interrupt_then_resume_generates_blueprint() -> None:
    settings = Settings(min_report_words=2000, confidence_threshold=0.95, max_refinement_loops=3)
    manifest = InputManifest(
        process_name="Order Intake",
        context_region="ANZ",
        pain_points=["Manual email/PDF order entry", "Frequent order modifications"],
        files=["sample_inputs/order_intake_notes.txt"],
    )
    state = create_initial_state(manifest)
    state["force_confidence_override"] = 0.97

    graph = build_graph(checkpointer=MemorySaver(), settings=settings, interrupt_before_blueprint=True)
    config = {"configurable": {"thread_id": "test-thread-1"}}
    graph.invoke(state, config=config)
    snapshot = graph.get_state(config)
    assert "Blueprint_Node" in tuple(snapshot.next or ())

    approved_state = dict(snapshot.values or {})
    approved_state["manual_approval"] = True
    completion_graph = build_graph(checkpointer=MemorySaver(), settings=settings, interrupt_before_blueprint=False)
    final_state = completion_graph.invoke(approved_state, config={"configurable": {"thread_id": "test-thread-2"}})
    assert final_state["phase_status"]["phase_3_blueprint_generation"] == "completed"
    assert "strategy_report_markdown" in final_state["refined_blueprint"]
    assert "mermaid_xml" in final_state["refined_blueprint"]
    report = final_state["strategy_report_markdown"]
    assert report.count("## Appendix: Control and Operability Baseline") == 1
    assert report.count("## Executive Simplified Summary") == 1
    summary_body = report.split("## Executive Simplified Summary", 1)[1].strip()
    assert "\n## " not in summary_body
    assert len(re.findall(r"[^.!?]+[.!?]", summary_body)) == 3
    assert "never embedded in the ERP kernel" in report
    mermaid_xml = final_state["mermaid_xml"]
    assert "subgraph External_Intake" in mermaid_xml
    assert "subgraph Agentic_SideCar" in mermaid_xml
    assert "subgraph Clean_Core_ERP" in mermaid_xml
