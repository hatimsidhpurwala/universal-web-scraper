import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from embedder import embed_query
from vector_store import search_chunks

class AgentState(TypedDict):
    question: str
    chat_history: list
    retrieved_chunks: list
    answer: str
    sources: list

def retrieve_node(state: AgentState) -> AgentState:
    query_vec = embed_query(state["question"])
    chunks = search_chunks(query_vec, top_k=8)
    state["retrieved_chunks"] = chunks
    state["sources"] = list({c["source_url"] for c in chunks})
    return state

def answer_node(state: AgentState) -> AgentState:
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile"
    )
    context = "\n\n".join(
        f"[Source: {c['source_url']} | Relevance: {c['score']}]\n{c['text']}"
        for c in state["retrieved_chunks"]
    )
    messages = [
        SystemMessage(content=(
            "You are a precise assistant that answers questions using ONLY the provided context chunks.\n"
            "Rules:\n"
            "1. Read ALL provided chunks carefully before answering\n"
            "2. Give a complete, detailed, well-structured answer\n"
            "3. If the question asks about services, list ALL services found across ALL chunks\n"
            "4. If multiple chunks mention the same topic, combine the information\n"
            "5. Never say 'according to page X' — just give the answer directly\n"
            "6. If the answer genuinely isn't in the context, say: 'This information was not found in the scraped content'\n"
            "7. Format with bullet points when listing multiple items"
        )),
        *state["chat_history"],
        HumanMessage(content=(
            f"Context chunks:\n{context}\n\n"
            f"Question: {state['question']}\n\n"
            f"Give a complete and accurate answer based strictly on the above context."
        ))
    ]
    response = llm.invoke(messages)
    state["answer"] = response.content
    state["chat_history"] = state["chat_history"] + [
        HumanMessage(content=state["question"]),
        AIMessage(content=response.content)
    ]
    return state

def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()

agent = build_agent()

def ask(question: str, chat_history: list = []) -> dict:
    result = agent.invoke({
        "question": question,
        "chat_history": chat_history,
        "retrieved_chunks": [],
        "answer": "",
        "sources": []
    })
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "chat_history": result["chat_history"]
    }