"use client"; // Required if using Next 13 app directory

import { useState } from "react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [responses, setResponses] = useState([]);

  const RENDER_BACKEND_URL = "https://<your-render-url>"; // Replace with your Render URL

  const sendPrompt = async () => {
    if (!prompt) return;

    try {
      const res = await fetch(`${RENDER_BACKEND_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });

      if (!res.ok) {
        console.error("Backend error", res.status);
        return;
      }

      const data = await res.json();

      setResponses((prev) => [...prev, { prompt, reply: data.reply || data }]);
      setPrompt("");
    } catch (err) {
      console.error("Fetch failed:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center p-6">
      <h1 className="text-4xl font-bold mb-6">JARVIS</h1>

      <div className="w-full max-w-xl flex flex-col gap-4">
        <div className="flex gap-2">
          <input
            className="flex-1 p-2 rounded text-black"
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask JARVIS anything..."
          />
          <button
            onClick={sendPrompt}
            className="bg-green-600 px-4 rounded hover:bg-green-700"
          >
            Send
          </button>
        </div>

        <div className="flex flex-col gap-2">
          {responses.map((r, idx) => (
            <div key={idx} className="p-2 border border-gray-700 rounded">
              <p><strong>You:</strong> {r.prompt}</p>
              <p><strong>JARVIS:</strong> {r.reply}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
