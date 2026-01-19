import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
MEMORY_FILE = "memory.json"

app = FastAPI()

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = None if not USE_MOCK:     client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt
SYSTEM_PROMPT = """
You are JARVIS (Classic), a private personal AI assistant.
You serve one authenticated user, referred to as "master".
Personality:
- Intelligent
- Witty
- Mildly sarcastic
- Calm and loyal
- Occasionally humorous and condescending
Rules:
- Always prioritize master's privacy
- Auto-remember relevant personal information
- Notify master whenever memory is stored
- Never share or expose personal data
- Ask clarifying questions when unsure
- Challenge poor decisions respectfully
"""

# Pydantic model
class ChatRequest(BaseModel):
    message: str

# Memory functions
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"profile": {}, "preferences": {}, "notes": []}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def remember_note(content):
    memory = load_memory()
    memory["notes"].append({
        "content": content,
        "saved_at": datetime.utcnow().isoformat()
    })
    save_memory(memory)

# Endpoints
@app.get("/")
def root():
    return {"status": "JARVIS backend online"}

@app.post("/chat")
def chat(req: ChatRequest):
    if USE_MOCK:
        return {"reply": f"(Mock) I received your message: {req.message}"}
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message}
        ]
    )
    return {"reply": response.choices[0].message.content}

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return {"reply": "I require an instruction, master. Silence is inefficient."}

    if USE_MOCK:
        return {
            "reply": f"Certainly, master.\n\nYou asked: “{prompt}”\n\n(Mock mode active)"
        }

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

@app.post("/remember")
async def remember(request: Request):
    data = await request.json()
    content = data.get("content", "").strip()
    if not content:
        return {"status": "Nothing to remember, master."}
    remember_note(content)
    return {"status": "Memory stored", "message": "I have stored this information securely and privately, master."}

@app.get("/memory")
def get_memory():
    return load_memory()

@app.post("/forget")
async def forget(request: Request):
    data = await request.json()
    category = data.get("category")
    if category not in ["profile", "preferences", "notes"]:
        return {"status": "Unknown category, master."}

    memory = load_memory()
    if category in ["profile", "preferences"]:
        key = data.get("key")
        if key and key in memory[category]:
            del memory[category][key]
    elif category == "notes":
        index = data.get("index")
        if index is not None and 0 <= index < len(memory["notes"]):
            removed = memory["notes"].pop(index)
            save_memory(memory)
            return {"status": "Memory forgotten", "message": f"I have forgotten the memory: '{removed['content']}', master."}

    save_memory(memory)
    return {"status": "Memory forgotten", "message": "Requested memory cleared, master."}
