from collections.abc import AsyncGenerator

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


async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    agent = _get_agent()
    langchain_messages = [(m["role"], m["content"]) for m in messages]
    async for chunk, _ in agent.astream(
        {"messages": langchain_messages},
        stream_mode="messages",
        config={"configurable": {"thread_id": "1"}}
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
