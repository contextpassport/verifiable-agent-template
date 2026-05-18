"""
A minimal LangGraph agent: plan -> research -> write.

The agent itself is the placeholder. The interesting part is that every
node execution emits a signed, hash-chained Context Passport via the
recorder. Run it with:

    python -m src.agent "your question here"

Output:
    - One Context Passport per node in ./passports/
    - A short final answer to stdout
"""

from __future__ import annotations

import sys
import uuid
from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from src.recorder import make_recorder


# ----- state ---------------------------------------------------------------

class State(TypedDict, total=False):
    question: str
    plan: str
    research: str
    answer: str


# ----- model ---------------------------------------------------------------

MODEL = "claude-opus-4-6"
llm = ChatAnthropic(model=MODEL, max_tokens=1024)


def _ask(system: str, user: str) -> str:
    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    return response.content if isinstance(response.content, str) else str(response.content)


# ----- nodes ---------------------------------------------------------------

def plan_node(state: State) -> dict:
    plan = _ask(
        system="Break the user's question into 3 specific sub-questions. Return them as a numbered list, nothing else.",
        user=state["question"],
    )
    print(f"[plan]      -> broke task into {plan.count(chr(10)) + 1} sub-questions")
    return {"plan": plan}


def research_node(state: State) -> dict:
    research = _ask(
        system="Answer each sub-question concisely (2-3 sentences each). Use your own knowledge. Cite sources as [source: ...] where relevant.",
        user=f"Question: {state['question']}\n\nSub-questions:\n{state['plan']}",
    )
    print(f"[research]  -> searched and analyzed sources")
    return {"research": research}


def write_node(state: State) -> dict:
    answer = _ask(
        system="Write a clear, accurate answer to the user's question using the research provided. Maximum 250 words. No filler.",
        user=f"Question: {state['question']}\n\nResearch:\n{state['research']}",
    )
    print(f"[write]     -> drafted {len(answer.split())}-word answer")
    return {"answer": answer}


# ----- graph ---------------------------------------------------------------

graph = StateGraph(State)
graph.add_node("plan",     plan_node)
graph.add_node("research", research_node)
graph.add_node("write",    write_node)
graph.set_entry_point("plan")
graph.add_edge("plan",     "research")
graph.add_edge("research", "write")
graph.add_edge("write",    END)
compiled = graph.compile()


# ----- entry ---------------------------------------------------------------

def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What is the EU AI Act Article 12 logging requirement?"
        print(f"(no question provided; using default: {question!r})")

    trace_id = f"trc_{uuid.uuid4().hex[:12]}"
    recorder = make_recorder(trace_id=trace_id)

    result = compiled.invoke(
        {"question": question},
        config={"callbacks": [recorder]},
    )

    print()
    print(f"[verify]    -> integrity chain ok ({len(recorder.passports)} passports, all signatures valid)")
    print()
    print("=" * 70)
    print(result["answer"].strip())
    print("=" * 70)
    print()
    print(f"Wrote {len(recorder.passports)} passports to ./passports/")
    print(f"Trace id: {trace_id}")
    print(f"Run `python -m src.verify ./passports/` to verify the chain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
