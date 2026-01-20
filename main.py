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
