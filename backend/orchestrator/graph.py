"""
LangGraph-based conversational agent with MongoDB checkpointer for persistent memory.

This module creates a stateful graph that:
1. Routes user queries to the appropriate RAG level (0, 1, or 2)
2. Executes the query using the selected tool
3. Persists conversation state to MongoDB for memory across sessions
"""

import logging
from typing import Annotated, Any, Dict, Optional

from common.config import settings
from common.schemas import QueryResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from orchestrator.agent import decide_tool, run_query, llm
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# -----------------------------
# State Definition
# -----------------------------
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    selected_level: Optional[int]
    rag_response: Optional[QueryResponse]
    rephrased_question: Optional[str]


# -----------------------------
# Graph Nodes
# -----------------------------
def contextualize_node(state: ChatState) -> Dict[str, Any]:
    """
    Contextualize node that rephrases the latest user question based on chat history.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    # Get the last user message
    last_message = messages[-1]
    if hasattr(last_message, "content"):
        question = last_message.content
    else:
        question = str(last_message)

    # If no history (just the current message), no need to rephrase
    if len(messages) <= 1:
        logger.info("[CONTEXTUALIZE] No history, keeping original question.")
        return {"rephrased_question": question}

    # Check if we have a valid LLM
    if not llm:
        logger.warning("[CONTEXTUALIZE] LLM not available, skipping rephrasing.")
        return {"rephrased_question": question}

    # Prepare history for context
    history_msgs = messages[:-1]  # Exclude the current message
    history_text = "\n".join(
        [
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in history_msgs[-6:]  # Last 3 turns
        ]
    )

    prompt = (
        "Given the following chat history and the latest user question which might reference context in the chat history, "
        "formulate a standalone question which can be understood without the chat history. "
        "Do NOT answer the question, just reformulate it if needed and otherwise return it as is.\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"Latest Question: {question}\n\n"
        "Standalone Question:"
    )

    try:
        logger.info("[CONTEXTUALIZE] Rephrasing question with history...")
        response = llm.invoke(prompt)
        rephrased = response.content.strip()
        logger.info(f"[CONTEXTUALIZE] Rephrased: '{question}' -> '{rephrased}'")
        return {"rephrased_question": rephrased}
    except Exception as e:
        logger.error(f"[CONTEXTUALIZE] Failed to rephrase: {e}")
        return {"rephrased_question": question}


def router_node(state: ChatState) -> Dict[str, Any]:
    """
    Router node that decides which RAG level to query based on the user's message.
    Uses the decide_tool from agent.py.
    """
    # Use rephrased question if available, otherwise fall back to last message
    question = state.get("rephrased_question")
    if not question:
        messages = state.get("messages", [])
        if not messages:
            logger.warning("[ROUTER] No messages in state")
            return {"selected_level": 1}
        last_message = messages[-1]
        question = (
            last_message.content
            if hasattr(last_message, "content")
            else str(last_message)
        )

    logger.info(f"[ROUTER] Routing question: {question[:100]}...")

    try:
        level = decide_tool(question)
        logger.info(f"[ROUTER] Selected Level {level}")
        return {"selected_level": level}
    except Exception as e:
        logger.error(f"[ROUTER] Failed to decide tool: {e}")
        return {"selected_level": 1}


def query_node(state: ChatState) -> Dict[str, Any]:
    """
    Query node that executes the query on the selected RAG level.
    """
    question = state.get("rephrased_question")
    selected_level = state.get("selected_level", 1)

    if not question:
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            question = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )
        else:
            error_msg = "No question provided"
            logger.error(f"[QUERY] {error_msg}")
            return {
                "rag_response": {"answer": error_msg, "citations": [], "prompt": None, "used_top_k": 0},
                "messages": [AIMessage(content=error_msg)],
            }

    logger.info(f"[QUERY] Executing query on Level {selected_level}")

    try:
        response = run_query(question, level=selected_level)
        if isinstance(response, dict):
            answer = response.get("answer", str(response))
            citations = response.get("citations", [])
            prompt = response.get("prompt", None)
            used_top_k = response.get("used_top_k", 0)

        else:
            answer = str(response)
            citations = []
            prompt = None
            used_top_k = 0

        logger.info(f"[QUERY] Got response with {len(answer)} chars")

        return {
            "rag_response": {"answer": answer, "citations": citations, "prompt": prompt, "used_top_k": used_top_k},
            "messages": [AIMessage(content=answer)],
        }
    except Exception as e:
        error_msg = f"Query failed: {str(e)}"
        logger.error(f"[QUERY] {error_msg}")
        return {
            "rag_response": {"answer": error_msg, "citations": [], "prompt": None, "used_top_k": 0},
            "messages": [AIMessage(content=error_msg)],
        }


# -----------------------------
# Graph Builder
# -----------------------------
def build_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph with router and query nodes.
    """
    builder = StateGraph(ChatState)

    # Add nodes
    builder.add_node("contextualize", contextualize_node)
    builder.add_node("router", router_node)
    builder.add_node("query", query_node)

    # Add edges
    builder.add_edge(START, "contextualize")
    builder.add_edge("contextualize", "router")
    builder.add_edge("router", "query")
    builder.add_edge("query", END)

    return builder


# -----------------------------
# Compiled Graph with Checkpointer
# -----------------------------
class ChatbotGraph:
    """
    Wrapper class for the compiled graph with MongoDB checkpointer.
    """

    def __init__(self):
        self.builder = build_graph()
        self.checkpointer = None
        self.checkpointer_cm = None
        self.graph = None

    def initialize(self):
        """Initialize the checkpointer and compile the graph."""
        if self.checkpointer is None:
            self.checkpointer_cm = MongoDBSaver.from_conn_string(
                settings.MONGO_URI, db_name=settings.DB_NAME
            )
            self.checkpointer = self.checkpointer_cm.__enter__()
            self.graph = self.builder.compile(checkpointer=self.checkpointer)
            logger.info("[GRAPH] Initialized ChatbotGraph with MongoDB checkpointer")

    def close(self):
        """Close the checkpointer connection."""
        if self.checkpointer_cm is not None:
            self.checkpointer_cm.__exit__(None, None, None)
            self.checkpointer = None
            self.graph = None
            logger.info("[GRAPH] Closed MongoDB checkpointer connection")

    def invoke(self, message: str, thread_id: str, user_id: str) -> Dict[str, Any]:
        """
        Invoke the graph with a user message.

        Args:
            message: The user's message/question
            thread_id: Unique thread ID for conversation continuity
            user_id: The authenticated user's ID

        Returns:
            Dict with answer, citations, and metadata
        """
        if self.graph is None:
            self.initialize()

        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

        input_state = {"messages": [HumanMessage(content=message)]}

        logger.info(f"[GRAPH] Invoking graph for thread={thread_id}, user={user_id}")

        try:
            result = self.graph.invoke(input_state, config)

            rag_response = result.get("rag_response", {})
            return {
                "answer": rag_response.get("answer", ""),
                "citations": rag_response.get("citations", []),
                "prompt": rag_response.get("prompt", None),
                "used_top_k": rag_response.get("used_top_k", 0),
                "thread_id": thread_id,
            }
        except Exception as e:
            logger.error(f"[GRAPH] Invocation failed: {e}")
            raise


# Global instance
chatbot_graph = ChatbotGraph()
