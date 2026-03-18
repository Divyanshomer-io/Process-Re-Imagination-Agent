"""Transform agent state dicts into the exact JSON shapes the UI expects.

The UI components import from mockResults.ts which defines these shapes:
  - mockFrictionData  ->  FrictionItemResponse[]
  - mockPathData      ->  PathItemResponse[]
  - mockStrategyReport -> string
  - mockBlueprintXML  -> string
  - mockUseCases      ->  UseCaseResponse[]
"""

from __future__ import annotations

import json
import re
from typing import Any

from api.schemas import (
    BlueprintResponse,
    FrictionItemResponse,
    PathItemResponse,
    UseCaseResponse,
)


def transform_friction_logs(
    cognitive_friction_logs: list[dict[str, Any]],
    evidence_references: list[dict[str, Any]] | None = None,
    pain_points: list[str] | None = None,
) -> list[FrictionItemResponse]:
    evidence_refs = evidence_references or []
    items: list[FrictionItemResponse] = []

    for log in cognitive_friction_logs:
        friction_id = log.get("friction_id", "")

        related_refs = [
            r.get("source", r.get("path", ""))
            for r in evidence_refs
            if r.get("id", "") == friction_id or friction_id in str(r)
        ]
        evidence_files = related_refs or (
            [log["source_evidence"]] if log.get("source_evidence") else []
        )

        related_pain = []
        if log.get("why_its_friction"):
            related_pain.append(log["why_its_friction"])
        if log.get("open_questions"):
            related_pain.append(log["open_questions"])
        if not related_pain and pain_points:
            related_pain = pain_points[:2]

        items.append(FrictionItemResponse(
            id=friction_id or f"F{len(items)+1:03d}",
            manualAction=log.get("current_manual_action", ""),
            whereInProcess=log.get("where_in_process", "Not specified"),
            region=log.get("region_impacted", "Global"),
            whyItMatters=log.get("why_its_friction", ""),
            evidenceText=log.get("source_evidence", ""),
            openQuestions=log.get("open_questions", ""),
            evidenceCount=len(evidence_files),
            relatedPainPoints=related_pain,
            evidence=evidence_files,
            pathClassification=log.get("proposed_path", "B"),
        ))
    return items


def transform_path_decisions(
    path_decisions: list[dict[str, Any]],
) -> list[PathItemResponse]:
    items: list[PathItemResponse] = []
    for dec in path_decisions:
        notes_parts = []
        if dec.get("clean_core_guardrail"):
            notes_parts.append(dec["clean_core_guardrail"])
        if dec.get("side_car_component"):
            notes_parts.append(dec["side_car_component"])
        if dec.get("regional_overrides"):
            notes_parts.append("Regional: " + ", ".join(dec["regional_overrides"]))

        items.append(PathItemResponse(
            item=dec.get("current_manual_action", ""),
            path=dec.get("path", "B"),
            suitabilityReason=dec.get("rationale", ""),
            notes=" | ".join(notes_parts) if notes_parts else "",
        ))
    return items


def transform_strategy_report(state: dict[str, Any]) -> str:
    report = state.get("strategy_report_markdown") or ""
    if not report:
        report = (state.get("refined_blueprint") or {}).get("strategy_report_markdown", "")
    return report


def transform_blueprint(state: dict[str, Any]) -> BlueprintResponse:
    # #region agent log
    from pathlib import Path as _P
    _log_path = _P(__file__).resolve().parents[3] / "debug-d79ac4.log"
    # #endregion
    xml = state.get("mermaid_xml") or ""
    if not xml:
        xml = (state.get("refined_blueprint") or {}).get("mermaid_xml", "")

    mermaid_code = ""
    visual_match = re.search(r"<MermaidData><!\[CDATA\[(.*?)\]\]></MermaidData>", xml, re.S)
    if visual_match:
        mermaid_code = visual_match.group(1).strip()
    else:
        legacy = re.search(r"<Diagram[^>]*><!\[CDATA\[(.*?)\]\]></Diagram>", xml, re.S)
        if legacy:
            mermaid_code = legacy.group(1).strip()
        elif "<mermaid>" in xml.lower():
            mermaid_match = re.search(r"<mermaid[^>]*>([\s\S]*?)</mermaid>", xml, re.I)
            if mermaid_match:
                raw = mermaid_match.group(1).strip()
                cdata = re.search(r"<!\[CDATA\[([\s\S]*?)\]\]>", raw)
                mermaid_code = (cdata.group(1) if cdata else raw).strip()
        elif "<Diagram" in xml:
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml)
                diagram_el = root.find("Diagram")
                if diagram_el is not None and diagram_el.text:
                    mermaid_code = diagram_el.text.strip()
            except Exception:
                pass

    svg = ""
    render_artifact = state.get("render_artifact", {})
    if render_artifact.get("status") == "created":
        from pathlib import Path as P
        svg_path = P(render_artifact.get("svg_path", ""))
        if svg_path.exists():
            svg = svg_path.read_text(encoding="utf-8")
    # #region agent log
    try:
        with open(_log_path, "a", encoding="utf-8") as _f:
            _f.write(json.dumps({"sessionId":"d79ac4","location":"transformers.py:transform_blueprint","message":"Blueprint transform","data":{"mermaidLen":len(mermaid_code),"mermaidPreview":mermaid_code[:150] if mermaid_code else "","svgLen":len(svg),"xmlLen":len(xml)},"hypothesisId":"H1,H5","timestamp":__import__("time").time()*1000}) + "\n")
    except Exception:
        pass
    # #endregion
    return BlueprintResponse(xml=xml, mermaid=mermaid_code, svg=svg)


def transform_use_cases(state: dict[str, Any]) -> list[UseCaseResponse]:
    raw = state.get("use_case_cards_json") or ""
    if not raw:
        raw = (state.get("refined_blueprint") or {}).get("use_case_cards_json", "")
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []

    cards = parsed.get("use_case_cards", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(cards, list):
        return []

    items: list[UseCaseResponse] = []
    for card in cards:
        ctx = card.get("context", {})
        ctx_str = ctx if isinstance(ctx, str) else (
            f"{ctx.get('region', '')} — {ctx.get('where_in_process', '')}".strip(" —")
        )

        mechanism = card.get("mechanism", "")
        if isinstance(mechanism, list):
            mechanism = ", ".join(mechanism)

        tech = card.get("tech_mapping", card.get("tech", ""))
        if isinstance(tech, dict):
            parts = []
            for k, v in tech.items():
                if v:
                    vals = v if isinstance(v, list) else [v]
                    parts.append(f"{k}: {', '.join(str(x) for x in vals)}")
            tech = " | ".join(parts)

        value = card.get("value", "")
        if isinstance(value, dict):
            value = value.get("statement", str(value))

        items.append(UseCaseResponse(
            id=card.get("use_case_id", card.get("id", f"UC{len(items)+1:03d}")),
            context=ctx_str,
            agentRole=card.get("agent_role_or_owner", card.get("agentRole", "")),
            mechanism=mechanism,
            tech=str(tech),
            value=str(value),
        ))
    return items
