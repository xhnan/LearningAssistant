from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv


load_dotenv()
async def get_title(message: str) -> str:
    model = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", streaming=True)
    conversation = [
    {"role": "system", "content": "用简短的一句话概括用的户输入的内容，生成一个标题。最好不要超过20个字。"},
    {"role": "user", "content": message}]
    result = await model.ainvoke(conversation)
    return result.content