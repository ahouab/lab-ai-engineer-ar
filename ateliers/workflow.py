import json
import os
import sys
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from rag import Question, request_json


API = os.getenv("RAG_URL", "http://127.0.0.1:8001")


class Etat(TypedDict, total=False):
    question: str
    proposition: dict
    sortie: str


def valider(etat: Etat) -> Etat:
    return {"question": Question(question=etat["question"]).question}


def generer(etat: Etat) -> Etat:
    reponse = request_json(f"{API}/ask", "POST", {"question": etat["question"]}, timeout=510)
    return {"proposition": reponse}


def verifier(etat: Etat) -> Command[Literal["afficher", "classer"]]:
    proposition = etat["proposition"]
    if proposition["verdict"] != "ok":
        return Command(goto="classer")
    accepter = interrupt({
        "الإجابة": proposition["answer"],
        "المصادر": [item["source"] for item in proposition["sources"]],
    })
    return Command(goto="afficher" if accepter is True else "classer")


def afficher(etat: Etat) -> Etat:
    return {"sortie": etat["proposition"]["answer"]}


def classer(_etat: Etat) -> Etat:
    return {"sortie": "لم تُعتمد أي إجابة."}


def main():
    graph = StateGraph(Etat)
    graph.add_node("valider", valider)
    graph.add_node("generer", generer)
    graph.add_node("verifier", verifier)
    graph.add_node("afficher", afficher)
    graph.add_node("classer", classer)
    graph.add_edge(START, "valider")
    graph.add_edge("valider", "generer")
    graph.add_edge("generer", "verifier")
    graph.add_edge("afficher", END)
    graph.add_edge("classer", END)
    workflow = graph.compile(checkpointer=InMemorySaver())

    question = " ".join(sys.argv[1:]) or "متى يبدأ النسخ الاحتياطي الكامل لمختبر أستر؟"
    config = {"configurable": {"thread_id": uuid4().hex}, "recursion_limit": 8}
    resultat = workflow.invoke({"question": question}, config)
    if resultat.get("__interrupt__"):
        print(json.dumps(resultat["__interrupt__"][0].value, ensure_ascii=False, indent=2))
        approuve = input("هل تعتمد الإجابة؟ [نعم/لا] ").strip() == "نعم"
        resultat = workflow.invoke(Command(resume=approuve), config)
    print(resultat["sortie"])


if __name__ == "__main__":
    main()
