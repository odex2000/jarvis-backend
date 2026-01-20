import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# ---------------------------
# Config
# ---------------------------
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEMORY_FILE = "memory.json"

# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI()

# CORS (allow frontend connections)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = None
if not USE_MOCK:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in environment!")
    client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# System prompt
# ---------------------------
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

# ---------------------------
# Pydantic model
# ---------------------------
class ChatRequest(BaseModel):
    message: str

# ---------------------------
# Memory functions
# ---------------------------
def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"profile": {}, "preferences": {}, "notes": []}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"profile": {}, "preferences": {}, "notes": []}

def save_memory(memory: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def remember_note(content: str, category: str = "notes", score: int = 5):
    memory = load_memory()
    # Ensure category exists
    if category not in memory:
        memory[category] = []

    if category in ["profile", "preferences"]:
        key = content.split(":")[0]  # simple key from "key: value"
        value = content.split(":", 1)[-1].strip()
        memory[category][key] = {"value": value, "score": score, "times_used": 0}
    else:  # notes
        memory[category].append({
            "content": content,
            "score": score,
            "times_used": 0,
            "saved_at": datetime.utcnow().isoformat()
        })

    save_memory(memory)

# ---------------------------
# Endpoints
# ---------------------------
@app.get("/")
def root():
    return {"status": "JARVIS backend online"}

# Chat endpoint
@app.post("/chat")
def chat(req: ChatRequest):
    memory = load_memory()
    if USE_MOCK:
        return {"reply": f"(Mock) I received your message: {req.message}"}

    # Include memory in prompt sorted by relevance
    notes_sorted = sorted(memory.get("notes", []), key=lambda x: x["score"], reverse=True)
    memory_context = "\n".join([f"- {n['content']}" for n in notes_sorted])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Relevant memories:\n{memory_context}"},
        {"role": "user", "content": req.message}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error: {str(e)}"

    # Update memory usage scoring (simple increment)
    for note in notes_sorted:
        if note['content'] in req.message:
            note['times_used'] += 1
            note['score'] += 1
    save_memory(memory)

    return {"reply": reply}

# Ask endpoint (short prompt)
@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return {"reply": "I require an instruction, master. Silence is inefficient."}

    if USE_MOCK:
        return {"reply": f"Certainly, master.\n\nYou asked: “{prompt}”\n\n(Mock mode active)"}

    memory = load_memory()
    notes_sorted = sorted(memory.get("notes", []), key=lambda x: x["score"], reverse=True)
    memory_context = "\n".join([f"- {n['content']}" for n in notes_sorted])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Relevant memories:\n{memory_context}"},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error: {str(e)}"

    # Update memory usage scoring
    for note in notes_sorted:
        if note['content'] in prompt:
            note['times_used'] += 1
            note['score'] += 1
    save_memory(memory)

    return {"reply": reply}

# Remember endpoint
@app.post("/remember")
async def remember(request: Request):
    try:
        data = await request.json()
        content = data.get("content", "").strip()
        category = data.get("category", "notes")
        score = int(data.get("score", 5))

        if not content:
            return {"status": "Nothing to remember, master."}

        remember_note(content, category, score)
        return {
            "status": "Memory stored",
            "message": "I have stored this information securely and privately, master."
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

# Get memory
@app.get("/memory")
def get_memory():
    return load_memory()

# Forget endpoint
@app.post("/forget")
async def forget(request: Request):
    try:
        data = await request.json()
        category = data.get("category")
        memory = load_memory()

        if category not in ["profile", "preferences", "notes"]:
            return {"status": "Unknown category, master."}

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
    except Exception as e:
        return {"status": "Error", "message": str(e)}
