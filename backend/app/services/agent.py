from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.services.chat import ChatService
from app.services.memory import MemoryService
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(request_id)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ------------------------------
# Data Models
# ------------------------------
class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    embedding: List[float]

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentState(TypedDict):
    messages: List[Message]
    current_input: str
    needs_memory: bool
    search_queries: List[str]
    memory_hits: List[str]
    error_count: int
    last_error: Optional[str]

# ------------------------------
# Agent Implementation
# ------------------------------
class Agent:
    def __init__(
        self,
        chat_service: ChatService,
        memory_store: MemoryService,
        user_id: str,
        history: List,
        exclude_ids: List[str]
    ):
        self.chat_service = chat_service
        self.memory_store = memory_store
        self.user_id = user_id
        self.history = history
        self.exclude_ids = exclude_ids
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(AgentState)
        builder.add_node("router", self._router)
        builder.add_node("query_generator", self._query_generator)
        builder.add_node("fetch_memory", self._fetch_memory)
        builder.add_node("respond", self._respond)
        # builder.add_edge("router","respond")
        builder.add_conditional_edges(
            "router",
            lambda s: "query_generator" if s["needs_memory"] else "respond",
            {"query_generator": "query_generator", "respond": "respond"}
        )
        builder.add_edge("query_generator", "fetch_memory")
        builder.add_edge("fetch_memory", "respond")

        builder.set_entry_point("router")
        return builder.compile()

    async def _router(self, state: AgentState) -> AgentState:
        try:
            prompt = f"""
                You are an assistant that decides whether the user's current question requires retrieving older long-term memories to be answered effectively.

                The user’s current question is:
                "{state['current_input']}"

                Here is the recent conversation history:
                {self.history}

                Your task:
                Analyze the question and the conversation history. Determine whether the question can be answered **using only the current context and this history**, or if **older stored memories** might be needed to answer it accurately.

                ### Mark that memory is needed if:
                - The question refers to something that is NOT clearly available in the history (e.g., "that idea I mentioned a while ago")
                - The user is asking for a reminder, summary, or clarification of something they likely said previously
                - Key details required to answer are **missing from the current history**

                ### Mark that memory is NOT needed if:
                - The question is general or self-contained
                - The relevant details are clearly visible in the provided history
                - The assistant has enough information to answer directly

                Make a careful judgment based on both the current question and history. Use the `check_memory_necessity` function to return the result. DO NOT include any other text or explanations in your response.
                """
            result = await self.chat_service.call_function(
                name="check_memory_necessity",
                prompt=prompt,
                type="check_memory_necessity"
            )
            try:
                state["needs_memory"] = result.args["needs_memory"]
            except KeyError:
                state["needs_memory"] = False
            return state
        except Exception as e:
            return self._handle_error(state, e)

    async def _query_generator(self, state: AgentState) -> AgentState:
        try:
            # create a prompt to use the history along with the user input to check if there is a need for checking for memories
            prompt = f"""
                    You are an assistant that helps generate search queries to retrieve relevant memories for answering a user's question.

                    Here’s the conversation history between the user and the assistant:
                    {self.history}

                    The current user question is:
                    "{state['current_input']}"

                    Your task is to:
                    1. Understand the context from both the question and the conversation history.
                    2. Identify the key concepts, entities, or past references relevant to the question.
                    3. Generate 2–3 short, specific search queries (each under 10 words) that can help retrieve relevant memories from a memory store.

                    Requirements:
                    - Do NOT repeat the entire question as a query.
                    - Do NOT include general phrases like "find relevant information".
                    - DO include named entities, specific topics, technical keywords, and time references when present.
                    - Queries should be scoped and targeted. If no useful memory is likely, use the question itself as a fallback query.

                    You MUST use the function `generate_search_queries` to return your results Do NOT include any other text or explanations in your response."""
                
            result = await self.chat_service.call_function(
                name="generate_search_queries",
                prompt=prompt,
                type="generate_search_queries"
            )
            try:
                state["search_queries"] = result.args["queries"]
            except KeyError:
                state["search_queries"] = [state["current_input"]]
            return state
        except Exception as e:
            # Fallback: use raw input
            state["search_queries"] = [state["current_input"]]
            return self._handle_error(state, e)

    async def _fetch_memory(self, state: AgentState) -> AgentState:
        try:
            for q in state.get("search_queries", []):
                results = await self.memory_store.search_memories(self.user_id,q, exclude_ids=self.exclude_ids)
                for mem in results:
                    self.exclude_ids.append(mem["_id"])
                    state["memory_hits"].append(mem["fields"]["chunk_text"])
            return state
        except Exception as e:
            return self._handle_error(state, e)

    async def _respond(self, state: AgentState) -> AgentState:
        try:
            prompt = f"""
                You are a helpful, conversational AI assistant.

                The user has asked the following question:
                "{state['current_input']}"

                Here is the recent conversation history:
                {self.history}

                {f"""The following relevant past memories were retrieved and may help answer the question:\n""" + ''.join(f"- {mem}\n" for mem in state["memory_hits"]) if state["needs_memory"] else ""}

                Your task:
                Based on the user's current question, the recent history, and (if available) the retrieved memories, generate a helpful, accurate, and context-aware response.

                - Prioritize the most relevant and recent information
                - If memories are used, integrate them smoothly (don’t just repeat them verbatim)
                - Be concise but informative
                - If the question is ambiguous or unclear, ask for clarification politely

                Now respond to the user.
                """
            
            await self.memory_store.store_memory(
                user_id=self.user_id,
                role="user",
                content=state["current_input"]
            )
            print("I got here")
            response = await self.chat_service.generate(
                prompt=prompt,
                history=self.history
            )
            await self.memory_store.store_memory(
                user_id=self.user_id,
                role="model",
                content=response
            )
            state["messages"].append(
                Message(role="model", content=response)
            )
            return state
        except Exception as e:
            return self._handle_error(state, e)

    def _handle_error(self, state: AgentState, error: Exception) -> AgentState:
        state["error_count"] += 1
        state["last_error"] = str(error)
        logger.error(f"Error: {error}", extra={"request_id": "-"})
        state["messages"].append(
            Message(role="assistant", content="Sorry, something went wrong.")
        )
        return state

# ------------------------------
# Run Utility
# ------------------------------
async def run_agent(
    user_input: str,
    chat_service: ChatService,
    memory_store: MemoryService,
    user_id: str
) -> Dict[str, Any]:
    state: AgentState = {
        "messages": [],
        "current_input": user_input,
        "needs_memory": False,
        "search_queries": [],
        "memory_hits": [],
        "error_count": 0,
        "last_error": None,
    }
    print("GETTING HISTORY")
    history, exclude_ids = await memory_store.get_history(user_id)
    agent = Agent(chat_service, memory_store, user_id, history, exclude_ids)
    final = await agent.graph.ainvoke(state)
    reply = final["messages"][-1].content if final["messages"] else ""
    return {
        "reply": reply,
        "search_queries": final.get("search_queries", []),
        "memory_hits": [m for m in final.get("memory_hits", [])],
        "error_count": final["error_count"],
        "last_error": final["last_error"],
    }
