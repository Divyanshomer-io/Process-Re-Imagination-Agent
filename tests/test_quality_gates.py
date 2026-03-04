from pathlib import Path

from process_reimagination_agent.config import Settings
from process_reimagination_agent.diagram_extraction import extract_canonical_document


def _f1(pred: set[str], truth: set[str]) -> float:
    if not pred and not truth:
        return 1.0
    if not pred or not truth:
        return 0.0
    tp = len(pred.intersection(truth))
    precision = tp / len(pred)
    recall = tp / len(truth)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def test_golden_quality_thresholds_for_diagram_relations() -> None:
    fixture = Path("sample_inputs/diagram_flow_sample.txt").resolve()
    text = fixture.read_text(encoding="utf-8")
    doc = extract_canonical_document(
        file_path=fixture,
        mime_type="text/plain",
        extracted_text=text,
        settings=Settings(),
        source_id="DOC_GOLDEN",
    )
    assert doc.graph is not None
    pred_nodes = {node.label for node in doc.graph.nodes}
    pred_edges = {
        (next((n.label for n in doc.graph.nodes if n.node_id == edge.source_id), ""), next((n.label for n in doc.graph.nodes if n.node_id == edge.target_id), ""))
        for edge in doc.graph.edges
    }

    truth_nodes = {
        "Start",
        "Receive Customer Purchase Requests",
        "What is the Order Type ?",
        "Enter Standard Order Details into the ERP",
        "Enter Consignment Details into the ERP",
        "Order capturing Failure?",
        "Resolve non-EDI issues",
        "Send Order Acknowledgement",
        "End",
    }
    truth_edges = {
        ("Start", "Receive Customer Purchase Requests"),
        ("Receive Customer Purchase Requests", "What is the Order Type ?"),
        ("What is the Order Type ?", "Enter Standard Order Details into the ERP"),
        ("What is the Order Type ?", "Enter Consignment Details into the ERP"),
        ("Enter Consignment Details into the ERP", "Order capturing Failure?"),
        ("Order capturing Failure?", "Resolve non-EDI issues"),
        ("Order capturing Failure?", "Send Order Acknowledgement"),
        ("Resolve non-EDI issues", "Send Order Acknowledgement"),
        ("Send Order Acknowledgement", "End"),
    }

    node_f1 = _f1(pred_nodes, truth_nodes)
    edge_f1 = _f1({f"{s}->{t}" for s, t in pred_edges}, {f"{s}->{t}" for s, t in truth_edges})
    gateway_ok = "What is the Order Type ?" in pred_nodes

    assert node_f1 >= 0.95
    assert edge_f1 >= 0.90
    assert gateway_ok
