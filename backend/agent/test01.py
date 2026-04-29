from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_deepseek import ChatDeepSeek



load_dotenv()

# model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", streaming=True)
# 实例化模型
model = ChatDeepSeek(
    model="deepseek-v4-flash",  
)

conversation = [
    {
        "role": "system",
        "content": "你是人工智能专家",
    },
    {"role": "user", "content": "介绍一下LangChain框架"},
]
for chunk in model.stream(conversation):
    # print(chunk.text, end="", flush=True)
      # 遍历当前 chunk 中的所有内容块
    for block in chunk.content_blocks:
        if block["type"] == "reasoning":
            # 打印思考内容（可能是分段出现的，所以用 end="" 避免换行）
            print(block["reasoning"], end="", flush=True)
        elif block["type"] == "text":
            # 打印正式回复的文本
            print(block["text"], end="", flush=True)
        # 如果还有 tool_call_chunk 等其他类型，也可以按需处理