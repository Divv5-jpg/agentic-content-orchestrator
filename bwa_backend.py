from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
import operator
from pathlib import Path
from typing import TypedDict,Literal,Optional,List,Annotated
from pydantic import BaseModel,Field
from langgraph.graph import StateGraph,START,END
from langgraph.types import Send
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage,HumanMessage
from langchain_community.tools.tavily_search import TavilySearchResults
class Task(BaseModel):
    id: str = ""
    title:str
    goal:str=Field(...,description="one sentence describing what the reader should be able to understand after this section")
    bullets:List[str]=Field(...,min_length=3,max_length=6,description='3-6 non overlapping subpoints to cover in this sections')
    target_words:int=Field(...,description='target word count for this section (120-550)')
    tags:List[str]=Field(default_factory=list)
    requires_research:bool=False
    requires_citation:bool=False
    requires_code:bool=False

class Plan(BaseModel):
    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal[
        "explainer",
        "tutorial",
        "news_roundup",
        "comparison",
        "system_design"
    ] = "explainer"
    constraints: List[str]
    tasks: List[Task]

class evidenceItem(BaseModel):
    title:str
    url:str
    published_at:Optional[str]=None
    snippet:Optional[str]=None
    source:Optional[str]=None

class routerdecision(BaseModel):
    need_research:bool
    mode:Literal["closed_book","open_book","hybrid"]
    queries:List[str]=Field(default_factory=list)

class evidencepack(BaseModel):
    evidence:List[evidenceItem]=Field(default_factory=list)
class State(TypedDict):
    topic:str
    mode:str
    needs_research:bool
    queries:list[str]
    evidence:list[evidenceItem]
    plan:Optional[Plan]
    sections: Annotated[list[tuple[int, str]], operator.add]
    final:str
llm= ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)
# -----------------------------
# 3) Router (decide upfront)
# -----------------------------
ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false):
  Evergreen topics where correctness does not depend on recent facts (concepts, fundamentals).
- hybrid (needs_research=true):
  Mostly evergreen but needs up-to-date examples/tools/models to be useful.
- open_book (needs_research=true):
  Mostly volatile: weekly roundups, "this week", "latest", rankings, pricing, policy/regulation.

If needs_research=true:
- Output 3–10 high-signal queries.
- Queries should be scoped and specific (avoid generic queries like just "AI" or "LLM").
- If user asked for "last week/this week/latest", reflect that constraint IN THE QUERIES.
"""

def router_node(state: State) -> dict:
    
    topic = state["topic"]
    decider = llm.with_structured_output(routerdecision)
    decision = decider.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=f"Topic: {topic}"),
        ]
    )

    return {
        "needs_research": decision.need_research,
        "mode": decision.mode,
        "queries": decision.queries,
    }

def route_next(state: State) -> str:
    return "research" if state["needs_research"] else "orchestrator"
# -----------------------------
# 4) Research (Tavily)
# -----------------------------

def _tavily_search(query: str, max_results: int = 2) -> List[dict]:

    tool = TavilySearchResults(max_results=max_results)
    results = tool.invoke({"query": query})

    normalized: List[dict] = []

    for r in results or []:
        normalized.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "snippet": (r.get("content") or r.get("snippet") or "")[:500],
                "published_at": r.get("published_date") or r.get("published_at"),
                "source": r.get("source"),
            }
        )

    return normalized



def research_node(state: State) -> dict:

    queries = (state.get("queries", []) or [])[:3]
    max_results = 2

    raw_results: List[dict] = []

    for q in queries:
        raw_results.extend(
            _tavily_search(q, max_results=max_results)
        )

    if not raw_results:
        return {"evidence": []}

    dedup = {}

    for r in raw_results:

        url = (r.get("url") or "").strip()

        if not url:
            continue

        dedup[url] = evidenceItem(
            title=(r.get("title") or "")[:300],
            url=url,
            published_at=r.get("published_at"),
            snippet=(r.get("snippet") or "")[:500],
            source=r.get("source"),
        )

    return {
        "evidence": list(dedup.values())
    }
ORCH_SYSTEM = """
You create a structured Plan for a technical blog.

Return valid JSON only. Do not explain your reasoning.

Create exactly 5 tasks.

Each task must contain:

- title
- goal
- 3 bullets
- target_words
- tags
- requires_research
- requires_citation
- requires_code
Do NOT generate the id field. It will be assigned by Python.

The JSON root object MUST contain these fields:
- blog_title
- audience
- tone
- blog_kind
- constraints
- tasks

IMPORTANT:
- "blog_kind" MUST be exactly one of:
  "explainer", "tutorial", "news_roundup", "comparison", "system_design".
- "constraints" MUST ALWAYS be a JSON array of strings.
- If there are no constraints, return [].
- Never omit "constraints".
- Never use "hybrid", "open_book", or "closed_book" as blog_kind.

Output ONLY the Plan object.
"""
def orchestrator_node(state: State) -> dict:
    planner = llm.with_structured_output(
    Plan,
    method="json_mode"
)
    evidence = state.get("evidence", [])
    mode = state.get("mode", "closed_book")

    # Keep only a small amount of evidence
    evidence_data = [
        e.model_dump()
        for e in evidence[:6]
    ]

    plan = planner.invoke(
        [
            SystemMessage(content=ORCH_SYSTEM),
            HumanMessage(
                content=(
                    f"Topic: {state['topic']}\n"
                    f"Mode: {mode}\n\n"
                    f"Evidence:\n"
                    f"{evidence_data}"
                )
            ),
        ]
    )
    for i, task in enumerate(plan.tasks, start=1):
       task.id = f"T{i}"

    return {"plan": plan}
# -----------------------------
# 6) Fanout
# -----------------------------
def fanout(state: State):
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
            },
        )
        for task in state["plan"].tasks
    ]

# -----------------------------
# 7) Worker (write one section)
# -----------------------------

import time

WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Rules:
- Follow the Goal and cover ALL Bullets in order.
- Keep the section concise and close to Target words.
- Output ONLY the section content in Markdown.
- Start with a '## <Section Title>' heading.
- Avoid fluff and marketing language.

Grounding:
- If mode == open_book, only make specific factual claims supported by Evidence.
- When making such claims, cite the provided URL using Markdown.
- Only use URLs from Evidence.
- If evidence does not support a claim, do not invent it.

Code:
- If requires_code == true, include a minimal relevant code example.

Style:
- Use short paragraphs and bullets where useful.
- Be precise and implementation-oriented.
"""

worker_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    max_tokens=1000
)


def worker_node(payload: dict) -> dict:

    # Small delay between worker requests
    time.sleep(5)

    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])

    evidence = [
        evidenceItem(**e)
        for e in payload.get("evidence", [])
    ]

    topic = payload["topic"]
    mode = payload.get("mode", "closed_book")

    bullets_text = "\n- " + "\n- ".join(task.bullets)

    evidence_text = ""

    if evidence:
        evidence_text = "\n".join(
            f"- {e.title} | {e.url}"
            for e in evidence[:2]
        )

    section_md = worker_llm.invoke(
        [
            SystemMessage(content=WORKER_SYSTEM),

            HumanMessage(
                content=(
                    f"Blog: {plan.blog_title}\n"
                    f"Audience: {plan.audience}\n"
                    f"Tone: {plan.tone}\n"
                    f"Blog kind: {plan.blog_kind}\n"
                    f"Topic: {topic}\n"
                    f"Mode: {mode}\n\n"

                    f"Section: {task.title}\n"
                    f"Goal: {task.goal}\n"
                    f"Target words: {task.target_words}\n"

                    f"requires_citation: {task.requires_citation}\n"
                    f"requires_code: {task.requires_code}\n\n"

                    f"Bullets:{bullets_text}\n\n"

                    f"Evidence:\n{evidence_text}"
                )
            ),
        ]
    ).content.strip()

    return {
        "sections": [(task.id, section_md)]
    }


# -----------------------------
# 8) Reducer (merge + save)
# -----------------------------
def reducer_node(state: State) -> dict:

    plan = state["plan"]

    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    final_md = f"# {plan.blog_title}\n\n{body}\n"

    filename = f"{plan.blog_title}.md"
    Path(filename).write_text(final_md, encoding="utf-8")

    return {"final": final_md}
# -----------------------------
# 9) Build graph
# -----------------------------
g = StateGraph(State)
g.add_node("router", router_node)
g.add_node("research", research_node)
g.add_node("orchestrator", orchestrator_node)
g.add_node("worker", worker_node)
g.add_node("reducer", reducer_node)

g.add_edge(START, "router")
g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
g.add_edge("research", "orchestrator")

g.add_conditional_edges("orchestrator", fanout, ["worker"])
g.add_edge("worker", "reducer")
g.add_edge("reducer", END)

app = g.compile()
app
# -----------------------------
# 10) Runner
# -----------------------------
def run(topic: str):
    out = app.invoke(
        {
            "topic": topic,
            "mode": "",
            "needs_research": False,
            "queries": [],
            "evidence": [],
            "plan": None,
            "sections": [],
            "final": "",
        }
    )

    return out

