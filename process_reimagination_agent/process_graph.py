from __future__ import annotations

from statistics import mean

from process_reimagination_agent.diagram_models import DiagramEdge, DiagramNode, ProcessGraph


def _coerce_graph(graph: ProcessGraph | dict | None) -> ProcessGraph | None:
    if graph is None:
        return None
    if isinstance(graph, ProcessGraph):
        return graph
    if isinstance(graph, dict):
        try:
            return ProcessGraph.model_validate(graph)
        except Exception:
            return None
    return None


def _normalize_node_type(label: str) -> tuple[str, str]:
    lower = label.lower()
    if "start" in lower:
        return "start_event", "none"
    if "end" in lower:
        return "end_event", "none"
    if "?" in label or "gateway" in lower or "decision" in lower:
        return "gateway", "xor"
    if "subprocess" in lower:
        return "subprocess", "none"
    if len(lower) <= 2:
        return "unknown", "none"
    return "task", "none"


def build_process_graph(
    *,
    graph_id: str,
    node_candidates: list[tuple[str, int, float, str | None]],
    edge_candidates: list[tuple[str, str, str | None, float]],
    warnings: list[str] | None = None,
) -> ProcessGraph:
    warnings_out = list(warnings or [])
    nodes: list[DiagramNode] = []
    for node_idx, (label, page_number, confidence, lane) in enumerate(node_candidates, start=1):
        node_type, gateway_type = _normalize_node_type(label)
        nodes.append(
            DiagramNode(
                node_id=f"N{node_idx}",
                label=label.strip(),
                node_type=node_type,  # type: ignore[arg-type]
                gateway_type=gateway_type,  # type: ignore[arg-type]
                lane=lane,
                page_number=max(1, page_number),
                confidence=max(0.0, min(1.0, confidence)),
            )
        )

    label_to_id = {node.label.lower(): node.node_id for node in nodes}
    edges: list[DiagramEdge] = []
    unresolved_edges = 0
    for edge_idx, (source_label, target_label, condition_label, confidence) in enumerate(edge_candidates, start=1):
        src = label_to_id.get(source_label.strip().lower())
        tgt = label_to_id.get(target_label.strip().lower())
        if not src or not tgt:
            unresolved_edges += 1
            warnings_out.append(f"Unresolved edge candidate: {source_label} -> {target_label}")
            continue
        edges.append(
            DiagramEdge(
                edge_id=f"E{edge_idx}",
                source_id=src,
                target_id=tgt,
                condition_label=condition_label.strip() if condition_label else None,
                confidence=max(0.0, min(1.0, confidence)),
            )
        )

    confidence_values = [n.confidence for n in nodes] + [e.confidence for e in edges]
    extraction_confidence = mean(confidence_values) if confidence_values else 0.0
    if unresolved_edges:
        extraction_confidence = max(0.0, extraction_confidence - min(0.25, unresolved_edges * 0.03))

    return ProcessGraph(
        graph_id=graph_id,
        nodes=nodes,
        edges=edges,
        lanes=[],
        extraction_confidence=round(extraction_confidence, 4),
        unresolved_edges=unresolved_edges,
        warnings=warnings_out,
    )


def graph_signals(graph: ProcessGraph | dict | None) -> dict[str, bool]:
    graph_obj = _coerce_graph(graph)
    if not graph_obj:
        return {
            "order_type_gateway": False,
            "capture_failure_gateway": False,
            "change_handler": False,
            "availability_check": False,
            "manual_loop_risk": False,
        }

    labels = [node.label.lower() for node in graph_obj.nodes]
    gateway_labels = [node.label.lower() for node in graph_obj.nodes if node.node_type == "gateway"]
    has_order_type = any("order type" in label or "consignment" in label for label in gateway_labels + labels)
    has_capture_failure = any("failure" in label or "edi issue" in label or "failed" in label for label in gateway_labels + labels)
    has_change = any("change" in label or "va02" in label or "amend" in label for label in labels)
    has_availability = any("availability" in label or "atp" in label for label in labels)
    has_manual_loop = any("manual" in label or "email" in label or "fax" in label for label in labels) and len(graph_obj.edges) >= 2
    return {
        "order_type_gateway": has_order_type,
        "capture_failure_gateway": has_capture_failure,
        "change_handler": has_change,
        "availability_check": has_availability,
        "manual_loop_risk": has_manual_loop,
    }


def graph_motifs(graph: ProcessGraph | dict | None) -> dict[str, int]:
    graph_obj = _coerce_graph(graph)
    if not graph_obj:
        return {"gateway_count": 0, "manual_touchpoints": 0, "exception_branches": 0, "edge_count": 0}
    gateway_count = len([n for n in graph_obj.nodes if n.node_type == "gateway"])
    manual_touchpoints = len(
        [
            n
            for n in graph_obj.nodes
            if any(token in n.label.lower() for token in ["manual", "email", "fax", "spreadsheet", "whatsapp"])
        ]
    )
    exception_branches = len(
        [n for n in graph_obj.nodes if any(token in n.label.lower() for token in ["failure", "issue", "exception", "block"])]
    )
    return {
        "gateway_count": gateway_count,
        "manual_touchpoints": manual_touchpoints,
        "exception_branches": exception_branches,
        "edge_count": len(graph_obj.edges),
    }
