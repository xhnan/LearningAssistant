from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "LearningAssistant API is running"}
