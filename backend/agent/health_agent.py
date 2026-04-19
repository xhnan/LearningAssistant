from collections.abc import AsyncGenerator

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", streaming=True)
        _agent = create_agent(
            model=model,
            tools=[],
            system_prompt="You are a helpful learning assistant.",
        )
    return _agent


async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    agent = _get_agent()
    langchain_messages = [(m["role"], m["content"]) for m in messages]
    async for chunk, _ in agent.astream(
        {"messages": langchain_messages},
        stream_mode="messages",
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
