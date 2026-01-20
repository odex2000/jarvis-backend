import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# =========================
# Config
# =========================
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
MEMORY_FILE = "memory.json"

app = FastAPI()

# Allow all origins (for frontend)
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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# =========================
# Pydantic Model
# =========================
class ChatRequest(BaseModel):
    message: str

# =========================
# Memory Functions
# =========================
def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {"profile": {}, "preferences": {}, "notes": []}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def remember_note(content: str, category="notes"):
    memory = load_memory()
    memory["notes"].append({
        "content": content,
        "saved_at": datetime.utcnow().isoformat(),
        "score": 0,
        "times_used": 0,
        "category": category
    })
    save_memory(memory)

# =========================
# Endpoints
# =========================
@app.get("/")
def root():
    return {"status": "JARVIS backend online"}

# ----- Chat endpoint -----
@app.post("/chat")
def chat(req: ChatRequest):
    memory = load_memory()

    # Sort notes by relevance score (descending)
    memory["notes"].sort(key=lambda x: x.get("score", 0), reverse=True)

    if USE_MOCK:
        # Increment mock memory scores for demo
        for note in memory["notes"]:
            note["times_used"] += 1
            note["score"] += 1
        save_memory(memory)

        return {
            "reply": f"(Mock) I received your message: {req.message}\nMemory notes count: {len(memory['notes'])}"
        }

    # REAL OpenAI call
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.message}
            ]
        )
        # Update memory scores after use
        for note in memory["notes"]:
            note["times_used"] += 1
            note["score"] += 1
        save_memory(memory)

        return {"reply": response.choices[0].message.content}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

# ----- Ask endpoint -----
@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return {"reply": "I require an instruction, master. Silence is inefficient."}

    memory = load_memory()
    # Sort by relevance
    memory["notes"].sort(key=lambda x: x.get("score", 0), reverse=True)

    if USE_MOCK:
        # Increment memory score in mock mode
        for note in memory["notes"]:
            note["times_used"] += 1
            note["score"] += 1
        save_memory(memory)

        return {
            "reply": f"Certainly, master.\n\nYou asked: “{prompt}”\n\n(Mock mode active)"
        }

    # REAL OpenAI call
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        # Update memory scores
        for note in memory["notes"]:
            note["times_used"] += 1
            note["score"] += 1
        save_memory(memory)

        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Error: {str(e)}"

    return {"reply": reply}

# ----- Remember endpoint -----
@app.post("/remember")
async def remember(request: Request):
    try:
        data = await request.json()
        content = data.get("content", "").strip()
        category = data.get("category", "notes")
        score = int(data.get("score", 5))  # default score 5

        if not content:
            return {"status": "Nothing to remember, master."}

        memory = load_memory()

        # Ensure category exists
        if category not in memory:
            memory[category] = []

        # Handle profile/preferences differently
        if category in ["profile", "preferences"]:
            key = data.get("key")
            if key:
                memory[category][key] = {"value": content, "score": score}
        else:  # notes
            memory[category].append({
                "content": content,
                "score": score,
                "saved_at": datetime.utcnow().isoformat()
            })

        save_memory(memory)

        return {
            "status": "Memory stored",
            "message": "I have stored this information securely and privately, master."
        }

    except Exception as e:
        return {"status": "Error", "message": str(e)}

# ----- Get memory -----
@app.get("/memory")
def get_memory():
    memory = load_memory()
    # Sort notes by score for dashboard display
    memory["notes"].sort(key=lambda x: x.get("score", 0), reverse=True)
    return memory

# ----- Forget endpoint -----
@app.post("/forget")
async def forget(request: Request):
    data = await request.json()
    category = data.get("category")
    memory = load_memory()

    if category not in ["profile", "preferences", "notes"]:
        return {"status": "Unknown category, master."}

    if category in ["profile", "preferences"]:
        key = data.get("key")
        if key and key in memory[category]:
            del memory[category][key]
        save_memory(memory)
        return {"status": "Memory forgotten", "message": "Requested memory cleared, master."}

    if category == "notes":
        index = data.get("index")
        if index is not None and 0 <= index < len(memory["notes"]):
            removed = memory["notes"].pop(index)
            save_memory(memory)
            return {"status": "Memory forgotten", "message": f"I have forgotten the memory: '{removed['content']}', master."}

    save_memory(memory)
    return {"status": "Memory forgotten", "message": "Requested memory cleared, master."}
