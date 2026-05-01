import gradio as gr
import requests
import json
import os
import re
from datetime import datetime
from anthropic import Anthropic

# ── API clients ────────────────────────────────────────────────────────────────
client = Anthropic()

# ── In-memory task list ────────────────────────────────────────────────────────
tasks: list[str] = []

# ── Conversation log ───────────────────────────────────────────────────────────
LOG_FILE = "conversation_log.jsonl"

def log_interaction(user_msg: str, bot_msg: str, tools_used: list[str]):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "bot": bot_msg,
        "tools_used": tools_used,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Tool 1: Weather (NWS — no key needed) ─────────────────────────────────────
def get_weather(city: str = "Spokane") -> str:
    """Fetch current forecast from the National Weather Service."""
    # Spokane coordinates (default); extendable via geocoding
    coords = {
        "spokane": (47.6588, -117.4260),
        "seattle": (47.6062, -122.3321),
        "portland": (45.5051, -122.6750),
        "new york": (40.7128, -74.0060),
        "chicago": (41.8781, -87.6298),
    }
    lat, lon = coords.get(city.lower(), (47.6588, -117.4260))

    try:
        # Step 1: get grid info
        meta = requests.get(
            f"https://api.weather.gov/points/{lat},{lon}",
            headers={"User-Agent": "MorningBriefingBot/1.0"},
            timeout=10,
        ).json()
        forecast_url = meta["properties"]["forecast"]

        # Step 2: get forecast
        forecast = requests.get(
            forecast_url,
            headers={"User-Agent": "MorningBriefingBot/1.0"},
            timeout=10,
        ).json()

        periods = forecast["properties"]["periods"][:2]  # today + tonight
        result = []
        for p in periods:
            result.append(
                f"**{p['name']}**: {p['detailedForecast']}"
            )
        return "\n\n".join(result)

    except Exception as e:
        return f"Weather unavailable right now ({e}). Check weather.gov manually."


# ── Tool 2: News (World News API) ─────────────────────────────────────────────
def get_news(topic: str = "top headlines") -> str:
    """Fetch top news headlines from World News API."""
    api_key = os.environ.get("WORLD_NEWS_API_KEY", "")
    if not api_key:
        return "World News API key not set. Add WORLD_NEWS_API_KEY to your environment."

    try:
        params = {
            "api-key": api_key,
            "text": topic,
            "language": "en",
            "number": 5,
            "sort": "publish-time",
            "sort-direction": "DESC",
        }
        resp = requests.get(
            "https://api.worldnewsapi.com/search-news",
            params=params,
            timeout=10,
        ).json()

        articles = resp.get("news", [])
        if not articles:
            return "No news articles found for that topic."

        lines = []
        for i, a in enumerate(articles, 1):
            title = a.get("title", "No title")
            source = a.get("source_country", "unknown source").upper()
            url = a.get("url", "")
            lines.append(f"{i}. **{title}** ({source})\n   {url}")

        return "\n\n".join(lines)

    except Exception as e:
        return f"News unavailable right now ({e})."


# ── Tool 3: Task manager ───────────────────────────────────────────────────────
def manage_tasks(action: str, task: str = "") -> str:
    """Add, remove, list, or clear tasks."""
    global tasks
    action = action.lower().strip()

    if action == "list":
        if not tasks:
            return "Your task list is empty. Add tasks by saying 'add task: <your task>'."
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(tasks))
        return f"**Your tasks for today:**\n{numbered}"

    elif action == "add":
        if not task:
            return "Please specify a task to add."
        tasks.append(task.strip())
        return f"✅ Added: *{task.strip()}*\nYou now have {len(tasks)} task(s)."

    elif action == "remove":
        # Try to match by number or text
        try:
            idx = int(task) - 1
            removed = tasks.pop(idx)
            return f"🗑️ Removed task {idx+1}: *{removed}*"
        except (ValueError, IndexError):
            # Try text match
            for i, t in enumerate(tasks):
                if task.lower() in t.lower():
                    removed = tasks.pop(i)
                    return f"🗑️ Removed: *{removed}*"
            return f"Couldn't find task matching '{task}'."

    elif action == "clear":
        tasks = []
        return "🧹 All tasks cleared."

    return "Unknown task action. Try: list, add, remove, or clear."


# ── Classifier + orchestrator ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly morning briefing assistant. You help users start their day with weather, news, and task management.

You have access to three tools:
1. WEATHER — fetch local weather forecast
2. NEWS — fetch top news headlines on any topic  
3. TASKS — manage a to-do list (add/remove/list/clear)

When the user asks for a "morning briefing", "good morning", "wake me up", or "daily briefing":
→ Call all three tools (weather + news + tasks) and compose a warm, readable morning summary.

When routing to a single tool, extract any relevant parameters:
- For weather: extract city name if mentioned (default: Spokane)
- For news: extract topic if mentioned (default: top headlines)
- For tasks: extract action (add/remove/list/clear) and task text

Always respond in a friendly, concise tone. Format your responses with clear sections.
Never make up news or weather — only use what the tools return.

Respond with a JSON routing decision in this format:
{
  "tools": ["weather", "news", "tasks"],  // which tools to call
  "weather_city": "Spokane",
  "news_topic": "top headlines",
  "task_action": "list",
  "task_text": ""
}
Then on a new line write: RESPONSE_FOLLOWS
Then write your final response to the user using the tool results."""


def classify_and_respond(message: str, tool_results: dict) -> str:
    """Ask Claude to generate the final response given tool results."""
    tool_summary = "\n\n".join(
        f"[{k.upper()} RESULTS]\n{v}" for k, v in tool_results.items()
    )
    prompt = f"""User message: {message}

Tool results:
{tool_summary}

Write a warm, well-formatted morning briefing response using the tool results above.
Use markdown formatting. Be friendly and concise."""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def route_message(message: str) -> tuple[dict, list[str]]:
    """Use Claude to decide which tools to call."""
    routing_prompt = f"""Analyze this user message and return a JSON routing decision.

User message: "{message}"

Return ONLY valid JSON with these fields:
{{
  "tools": [],       // list of tools needed: "weather", "news", "tasks"
  "weather_city": "Spokane",
  "news_topic": "top headlines",
  "task_action": "list",
  "task_text": ""
}}

Rules:
- "good morning", "morning briefing", "wake up", "daily briefing" → all three tools
- weather questions → ["weather"]
- news questions → ["news"], extract topic
- task questions (add/remove/show/list/clear tasks) → ["tasks"], extract action and text
- greetings or unclear → ["tasks"] with action "list"

Return ONLY the JSON object, no other text."""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": routing_prompt}],
    )
    raw = resp.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw), []
    except json.JSONDecodeError:
        # Fallback: show tasks
        return {"tools": ["tasks"], "task_action": "list", "task_text": "",
                "weather_city": "Spokane", "news_topic": "top headlines"}, []


# ── Main chat function ─────────────────────────────────────────────────────────
def chat(message: str, history: list) -> str:
    if not message.strip():
        return "Good morning! Ask for your **morning briefing**, check the **weather**, get **news**, or manage your **tasks**."

    # Route
    routing, _ = route_message(message)
    tools_called = routing.get("tools", ["tasks"])
    tool_results = {}

    if "weather" in tools_called:
        city = routing.get("weather_city", "Spokane")
        tool_results["weather"] = get_weather(city)

    if "news" in tools_called:
        topic = routing.get("news_topic", "top headlines")
        tool_results["news"] = get_news(topic)

    if "tasks" in tools_called:
        action = routing.get("task_action", "list")
        text = routing.get("task_text", "")
        tool_results["tasks"] = manage_tasks(action, text)

    # Generate response
    response = classify_and_respond(message, tool_results)

    # Log it
    log_interaction(message, response, tools_called)

    return response


# ── Gradio UI ──────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="☀️ Morning Briefing Bot",
    theme=gr.themes.Soft(primary_hue="amber", neutral_hue="slate"),
    css="""
    .gradio-container { max-width: 800px !important; margin: auto; }
    .chat-message { font-size: 15px; line-height: 1.6; }
    footer { display: none !important; }
    #title-row { text-align: center; padding: 1rem 0 0.5rem; }
    #subtitle { color: #888; font-size: 14px; text-align: center; margin-bottom: 1rem; }
    """
) as demo:

    gr.HTML("""
    <div id="title-row">
        <h1>☀️ Morning Briefing Bot</h1>
    </div>
    <p id="subtitle">Your AI-powered daily assistant — weather · news · tasks</p>
    """)

    chatbot = gr.Chatbot(
    label="",
    height=480,
    show_label=False,
    elem_classes=["chat-message"],
    placeholder="Ask for your morning briefing to get started!",
    type="messages",   # ← add this line
)

    with gr.Row():
        msg_box = gr.Textbox(
            placeholder='Try: "Good morning!" or "Add task: call dentist" or "What\'s the weather?"',
            show_label=False,
            scale=5,
            container=False,
        )
        send_btn = gr.Button("Send ➤", variant="primary", scale=1)

    with gr.Row():
        gr.Examples(
            examples=[
                "Good morning! Give me my full briefing.",
                "What's the weather in Spokane today?",
                "Add task: review project proposal",
                "Add task: call dentist at 2pm",
                "Show my tasks",
                "What's the latest news on AI?",
                "Remove task 1",
                "Clear all my tasks",
            ],
            inputs=msg_box,
            label="Quick examples",
        )

    def respond(message, history):
    if not message.strip():
        return history, ""
    reply = chat(message, history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return history, ""

    send_btn.click(respond, [msg_box, chatbot], [chatbot, msg_box])
    msg_box.submit(respond, [msg_box, chatbot], [chatbot, msg_box])

if __name__ == "__main__":
    demo.launch(debug=True)
