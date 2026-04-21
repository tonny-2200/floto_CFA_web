import os
import json
import re
from typing import TypedDict, List, Dict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from prompts import (
    MAPPER_PROMPT_TEMPLATE,
    AUDITOR_TEXT_PROMPT_TEMPLATE,
    REPORTER_PROMPT_TEMPLATE,
)

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")


class AuditError(Exception):
    """Raised when AI audit processing fails."""

def _coerce_score(value, default: int = 0) -> int:
    """Convert score-like values (e.g., '78%') into int 0..100."""
    if isinstance(value, (int, float)):
        if value != value:  # NaN guard
            return default
        return max(0, min(100, int(round(value))))
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            try:
                parsed = float(match.group(0))
                return max(0, min(100, int(round(parsed))))
            except Exception:
                return default
    return default

def _normalize_final_report(report: Dict) -> Dict:
    """Harden LLM JSON into stable API schema."""
    if not isinstance(report, dict):
        return {
            "overall_score": 0,
            "funnel_data": [],
            "top_recommendations": ["Error parsing AI response"],
        }

    raw_funnel = report.get("funnel_data", [])
    normalized_funnel = []
    if isinstance(raw_funnel, list):
        for item in raw_funnel:
            if not isinstance(item, dict):
                continue
            normalized_funnel.append(
                {
                    "stage": str(item.get("stage", "Unknown Stage")),
                    "value": _coerce_score(item.get("value", 0), default=0),
                    "status": str(item.get("status", "danger")),
                }
            )

    raw_recs = report.get("top_recommendations", [])
    if isinstance(raw_recs, list):
        top_recommendations = [str(rec) for rec in raw_recs[:3]]
    else:
        top_recommendations = []
    if not top_recommendations:
        top_recommendations = ["No recommendations generated."]

    return {
        "overall_score": _coerce_score(report.get("overall_score", 0), default=0),
        "funnel_data": normalized_funnel,
        "top_recommendations": top_recommendations,
    }


def _content_to_text(content) -> str:
    """Normalize LLM message content into plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                # LangChain/OpenAI content blocks commonly use {"type": "text", "text": "..."}
                text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(content)

def _safe_json_parse(content):
    """Parse model output JSON with common markdown fence cleanup."""
    text = _content_to_text(content)
    clean = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)

def _normalize_funnel_map(data) -> Dict[str, List[str]]:
    """Normalize mapper output to required lowercase stage keys."""
    stage_keys = ["awareness", "exploration", "consideration", "conversion"]
    if not isinstance(data, dict):
        return {k: [] for k in stage_keys}

    normalized = {}
    for key in stage_keys:
        value = data.get(key, [])
        if isinstance(value, list):
            normalized[key] = [str(v) for v in value if str(v).strip()]
        elif isinstance(value, str) and value.strip():
            normalized[key] = [value.strip()]
        else:
            normalized[key] = []
    return normalized

def _normalize_friction_points(data) -> List[Dict]:
    """Normalize auditor output into list of structured friction points."""
    if not isinstance(data, list):
        return []

    points = []
    for item in data:
        if not isinstance(item, dict):
            continue
        points.append(
            {
                "stage": str(item.get("stage", "Exploration")),
                "severity": str(item.get("severity", "medium")).lower(),
                "issue": str(item.get("issue", "")),
                "evidence": str(item.get("evidence", "")),
                "impact": str(item.get("impact", "")),
            }
        )
    return points


def _status_from_score(score: int) -> str:
    """Map numeric score to UI status bands."""
    if score >= 70:
        return "good"
    if score >= 40:
        return "warning"
    return "danger"


def _compute_stage_score(
    stage_key: str,
    stage_label: str,
    funnel_stages: Dict[str, List[str]],
    friction_points: List[Dict],
) -> int:
    """
    Deterministic stage score to reduce overly critical model swings.
    Uses baseline + evidence coverage - friction penalties.
    """
    severity_penalty = {"low": 8, "medium": 18, "high": 30}
    mapped_items = funnel_stages.get(stage_key, [])
    stage_friction = [
        p for p in friction_points
        if str(p.get("stage", "")).strip().lower() == stage_label.lower()
    ]

    # Baseline: neutral score. Good pages should not start in danger.
    score = 68

    # Reward observable evidence in this stage.
    if len(mapped_items) >= 3:
        score += 8
    elif len(mapped_items) >= 1:
        score += 4
    else:
        score -= 10

    # Penalize friction based on severity.
    for point in stage_friction:
        severity = str(point.get("severity", "medium")).lower()
        score -= severity_penalty.get(severity, 18)

    return max(0, min(100, int(round(score))))


def _calibrate_report_scores(
    final_report: Dict,
    funnel_stages: Dict[str, List[str]],
    friction_points: List[Dict],
) -> Dict:
    """
    Blend LLM scores with deterministic stage signals so one bad LLM sample
    does not classify healthy landing pages as critical.
    """
    canonical_stages = [
        ("awareness", "Awareness"),
        ("exploration", "Exploration"),
        ("consideration", "Consideration"),
        ("conversion", "Conversion"),
    ]

    stage_lookup = {}
    for item in final_report.get("funnel_data", []):
        if isinstance(item, dict):
            key = str(item.get("stage", "")).strip().lower()
            stage_lookup[key] = item

    calibrated_funnel = []
    for stage_key, stage_label in canonical_stages:
        llm_item = stage_lookup.get(stage_label.lower(), {})
        llm_score = _coerce_score(llm_item.get("value", 68), default=68)
        deterministic_score = _compute_stage_score(
            stage_key=stage_key,
            stage_label=stage_label,
            funnel_stages=funnel_stages,
            friction_points=friction_points,
        )

        # Weighted blend favors model, but anchors with deterministic logic.
        blended = int(round((0.6 * llm_score) + (0.4 * deterministic_score)))
        blended = max(0, min(100, blended))
        calibrated_funnel.append(
            {
                "stage": stage_label,
                "value": blended,
                "status": _status_from_score(blended),
            }
        )

    overall = int(round(sum(item["value"] for item in calibrated_funnel) / len(calibrated_funnel)))

    return {
        "overall_score": overall,
        "funnel_data": calibrated_funnel,
        "top_recommendations": final_report.get("top_recommendations", ["No recommendations generated."])[:3],
    }


# 1. Define the State
class GraphState(TypedDict):
    markdown: str
    screenshot: str  # Base64
    structured_elements: Dict
    funnel_stages: Dict
    friction_points: List[Dict]
    final_report: Dict

# 2. Initialize Model

llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_ENDPOINT"),          
    api_key=os.getenv("AZURE_API_KEY"),
    api_version="2024-12-01-preview",
    azure_deployment="gpt-5-mini",                      
)

llm_2 = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # or gemini-1.5-pro
    google_api_key=api_key,
    temperature=0.5,
)

# --- NODES ---

def mapper_node(state: GraphState):
    """Maps markdown content to Awareness, Exploration, Consideration, Conversion."""
    prompt = MAPPER_PROMPT_TEMPLATE.format(
        markdown=state["markdown"],
        structured_elements=json.dumps(state.get("structured_elements", {}), ensure_ascii=False),
    )
    response = llm.invoke([SystemMessage(content="You are a conversion strategist."), HumanMessage(content=prompt)])
    try:
        parsed = _safe_json_parse(response.content)
        state['funnel_stages'] = _normalize_funnel_map(parsed)
    except Exception as e:
        print(f"Mapper JSON Parsing Error: {e}")
        state['funnel_stages'] = _normalize_funnel_map({})
    return state

def auditor_node(state: GraphState):
    """Identifies friction points using both Text and Vision."""
    text_prompt = AUDITOR_TEXT_PROMPT_TEMPLATE.format(
        funnel_stages=json.dumps(state.get("funnel_stages", {}), ensure_ascii=False)
    )
    # We send the screenshot as a base64 message for Vision analysis
    message = HumanMessage(
        content=[
            {"type": "text", "text": text_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{state['screenshot']}"}}
        ]
    )
    
    response = llm.invoke([message])
    try:
        parsed = _safe_json_parse(response.content)
        state['friction_points'] = _normalize_friction_points(parsed)
    except Exception as e:
        print(f"Auditor JSON Parsing Error: {e}")
        state['friction_points'] = []
    return state

def reporter_node(state: GraphState):
    """Synthesizes everything into a final structured dashboard JSON."""
    prompt = REPORTER_PROMPT_TEMPLATE.format(
        funnel_stages=json.dumps(state.get("funnel_stages", {}), ensure_ascii=False),
        friction_points=json.dumps(state.get("friction_points", []), ensure_ascii=False),
        structured_elements=json.dumps(state.get("structured_elements", {}), ensure_ascii=False),
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])

    try:
        parsed = _safe_json_parse(response.content)
        normalized = _normalize_final_report(parsed)
        state['final_report'] = _calibrate_report_scores(
            final_report=normalized,
            funnel_stages=state.get("funnel_stages", {}),
            friction_points=state.get("friction_points", []),
        )
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        # Fallback: Create a basic report structure so the app doesn't crash
        state['final_report'] = {
            "overall_score": 0,
            "funnel_data": [],
            "top_recommendations": ["Error parsing AI response"]
        }
        
    return state

# --- GRAPH CONSTRUCTION ---

workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("map_funnel", mapper_node)
workflow.add_node("audit_friction", auditor_node)
workflow.add_node("generate_report", reporter_node)

# Define Edges
workflow.set_entry_point("map_funnel")
workflow.add_edge("map_funnel", "audit_friction")
workflow.add_edge("audit_friction", "generate_report")
workflow.add_edge("generate_report", END)

# Compile
app = workflow.compile()

# --- EXECUTION ---
async def run_audit(crawl_data: Dict):
    initial_state = {
        "markdown": crawl_data['markdown'],
        "screenshot": crawl_data['screenshot'],
        "structured_elements": crawl_data['structured_elements'],
        "funnel_stages": {},
        "friction_points": [],
        "final_report": {}
    }
    
    result = await app.ainvoke(initial_state)
    return result['final_report']