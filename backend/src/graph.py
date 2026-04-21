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
    AUDITOR_TEXT_PROMPT,
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
    prompt = MAPPER_PROMPT_TEMPLATE.format(markdown=state["markdown"])
    response = llm.invoke([SystemMessage(content="You are a conversion strategist."), HumanMessage(content=prompt)])
    # In a real app, use structured output parser. For now, simple JSON loading.
    state['funnel_stages'] = response.content 
    return state

def auditor_node(state: GraphState):
    """Identifies friction points using both Text and Vision."""
    # We send the screenshot as a base64 message for Vision analysis
    message = HumanMessage(
        content=[
            {"type": "text", "text": AUDITOR_TEXT_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{state['screenshot']}"}}
        ]
    )
    
    response = llm.invoke([message])
    state['friction_points'] = response.content
    return state

def reporter_node(state: GraphState):
    """Synthesizes everything into a final structured dashboard JSON."""
    prompt = f"""
    Create a final Conversion Audit Report based on these findings:
    Funnel Mapping: {state['funnel_stages']}
    Friction Points: {state['friction_points']}
    
    Return ONLY a valid JSON object. Do not include markdown formatting.
    Required keys: 
    - overall_score (int 0-100)
    - funnel_data (list of objects with 'stage', 'value', 'status')
    - top_recommendations (list of 3 strings)
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content

    # Safety Check: If content is somehow not a string, convert it
    if not isinstance(content, str):
        content = str(content)

    try:
        # 1. Strip out markdown code blocks if the LLM included them
        clean_json = content.replace("```json", "").replace("```", "").strip()
        
        # 2. Parse the string into a Python dict
        parsed = json.loads(clean_json)
        state['final_report'] = _normalize_final_report(parsed)
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