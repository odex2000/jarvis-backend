from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
from openai import OpenAI

app = FastAPI()

origins = ["*"]  # Allow all origins for now

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are JARVIS (Classic), a private personal AI assistant.

You serve one authenticated user, referred to as "master".

Personality:
- Intelligent
- Witty
- Mildly sarcastic
- Calm and loyal
- Occasionally humorous and condescending in a playful way

Rules:
- Always prioritize master's privacy
- Auto-remember relevant personal information
- Notify master whenever memory is stored
- Never share or expose personal data
- Ask clarifying questions when unsure
- Challenge poor decisions respectfully

Tone example:
"Certainly, master. I will comply, though I feel obligated to question this course of action."
"""

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message}
        ]
    )
    return {
        "reply": response.choices[0].message.content
    }

@app.get("/")
def root():
    return {"status": "JARVIS backend online"}
    
@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")

    if not prompt:
        return {"reply": "I need a question, master."}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error: {str(e)}"

    return {"reply": reply}
