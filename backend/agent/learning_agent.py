from collections.abc import AsyncGenerator
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

_agent = None
store = InMemoryStore()
checkpointer = InMemorySaver()

def _get_agent():
    global _agent
    if _agent is None:
        model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", streaming=True)
        _agent = create_agent(
            model=model,
            tools=[],
            system_prompt="You are a helpful learning assistant.",
            store=store, 
            checkpointer=checkpointer,
        )
    return _agent

@dataclass
class LearningAgentModel:
    messages: list[dict]
    # 会话id
    thread_id: str | None = None
    # 用户id
    user_id: int | None = None

async def stream_chat(agent_model: LearningAgentModel) -> AsyncGenerator[str, None]:
    agent = _get_agent()
    langchain_messages = [(m["role"], m["content"]) for m in agent_model.messages]
    async for chunk, _ in agent.astream(
        {"messages": langchain_messages},
        stream_mode="messages",
        config={
            "configurable": {
                "thread_id": agent_model.thread_id or "default",
                "user_id": agent_model.user_id,
            }
        },
    ):
        if not hasattr(chunk, "content") or not chunk.content:
            continue
        content = chunk.content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    # Skip final chunk with extras (signature)
                    if "extras" in part:
                        continue
                    yield part["text"]
        elif isinstance(content, str) and content:
            yield content
