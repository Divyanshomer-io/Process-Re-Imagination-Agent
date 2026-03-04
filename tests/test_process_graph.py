from process_reimagination_agent.process_graph import build_process_graph, graph_motifs, graph_signals


def test_build_process_graph_and_signals() -> None:
    graph = build_process_graph(
        graph_id="g1",
        node_candidates=[
            ("Start", 1, 0.9, None),
            ("What is the Order Type ?", 1, 0.8, "Customer Solutions"),
            ("Enter Standard Order Details into the ERP", 1, 0.8, "Customer Solutions"),
            ("Order capturing Failure?", 1, 0.7, "Customer Solutions"),
            ("End", 1, 0.9, None),
        ],
        edge_candidates=[
            ("Start", "What is the Order Type ?", None, 0.7),
            ("What is the Order Type ?", "Enter Standard Order Details into the ERP", "Yes", 0.7),
            ("Enter Standard Order Details into the ERP", "End", None, 0.7),
        ],
    )
    assert graph.nodes
    assert graph.edges
    signals = graph_signals(graph)
    assert signals["order_type_gateway"]
    assert signals["capture_failure_gateway"]
    motifs = graph_motifs(graph)
    assert motifs["gateway_count"] >= 1
