# ☀️ Morning Briefing Bot

> An AI-powered daily assistant that greets you each morning with local weather, top news, and your personalized task list — all in a single conversational interface.

**Live demo:** _[Add your Hugging Face Spaces link here]_

---

## Overview

Morning Briefing Bot is a LangChain-style multi-tool chatbot that routes your requests to the right data source automatically. Ask for your "morning briefing" and it pulls today's weather forecast, current headlines, and your task list — then Claude composes it into a friendly, readable summary.

---

## The Problem

Every morning involves the same friction: opening a weather app, scanning a news site, checking a to-do list — all in separate places. This bot consolidates that into a single conversational interface. You ask once, it fetches everything, and Claude presents it in a clean, readable format. The motivation came from wanting a smarter, personalized alternative to generic news apps that don't know your local context or daily priorities.

---

## How It Works

```
User message
     │
     ▼
┌─────────────┐
│   Router    │  (Claude Haiku classifies intent)
│  (Claude)   │
└──────┬──────┘
       │
  ┌────┴─────────────────────┐
  │                          │                          │
  ▼                          ▼                          ▼
WEATHER                    NEWS                      TASKS
api.weather.gov        worldnewsapi.com          In-memory list
(no key needed)        (free API key)            (chat-managed)
  │                          │                          │
  └────────────┬─────────────┘
               ▼
        Claude Haiku
     (compose response)
               │
               ▼
        Final reply → User
               │
               ▼
        conversation_log.jsonl
```

**Routing rules:**
- "good morning" / "morning briefing" → all 3 tools
- Weather question → NWS API
- News question → World News API (topic extracted)
- Task command → in-memory task manager (add/remove/list/clear)

---

## Tools

| Tool | Source | Key Required |
|------|--------|-------------|
| Weather | [api.weather.gov](https://api.weather.gov) | ❌ None |
| News | [worldnewsapi.com](https://worldnewsapi.com) | ✅ Free signup |
| Tasks | In-memory | ❌ None |
| LLM | Anthropic Claude Haiku | ✅ Paid (~$5 to start) |

---

## Key Findings / What I Learned

The hardest part was reliable JSON routing from the LLM — Claude occasionally wraps responses in markdown code fences even when instructed not to, so stripping those before parsing was a necessary defensive step. Temperature=0 on the routing call helped but didn't fully eliminate it.

The NWS API is surprisingly powerful and completely free, but requires a two-step call (points endpoint → forecast endpoint) that isn't obvious from the docs. The World News API's free tier (50 daily points) is tight for heavy testing but plenty for a real morning briefing use case.

If I were to extend this, I'd add a geocoding step so users can ask for weather in any city by name, and a persistent task store (SQLite or a simple JSON file) so tasks survive app restarts.

---

## Sample Conversations

**1. Full morning briefing**
```
User: Good morning! Give me my full briefing.
Bot:  ☀️ Good morning! Here's your briefing for Wednesday...

      🌤️ WEATHER — Spokane
      Today: Partly cloudy with a high of 62°F...

      📰 NEWS
      1. Fed holds rates steady amid inflation concerns...
      2. ...

      ✅ TASKS (2)
      1. Call dentist at 2pm
      2. Review project proposal
```

**2. Adding tasks**
```
User: Add task: buy groceries after work
Bot:  ✅ Added: buy groceries after work
      You now have 3 tasks.
```

**3. News on a specific topic**
```
User: What's the latest news on AI?
Bot:  Here are the top AI headlines...
      1. OpenAI announces new reasoning model...
```

**4. Weather only**
```
User: What's the weather like today?
Bot:  🌤️ Here's today's forecast for Spokane...
      Today: Mostly sunny, high near 65°F, light winds.
```

---

## How to Run

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/morning-briefing-bot
cd morning-briefing-bot
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set environment variables**
```bash
export ANTHROPIC_API_KEY=your_key_here
export WORLD_NEWS_API_KEY=your_key_here
```

Or in Google Colab, save them as secrets named `ANTHROPIC_API_KEY` and `WORLD_NEWS_API_KEY`.

**4. Launch**
```bash
python app.py
```

Open the local URL shown in the terminal (usually `http://127.0.0.1:7860`).

---

## Deploying to Hugging Face Spaces

1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces) → SDK: Gradio
2. Upload `app.py` and `requirements.txt`
3. Add your API keys under **Settings → Secrets**:
   - `ANTHROPIC_API_KEY`
   - `WORLD_NEWS_API_KEY`
4. The Space will build and deploy automatically

---

## Who Would Care

Anyone who wants a smarter, consolidated morning routine — students juggling deadlines, remote workers starting async days, or anyone tired of context-switching between weather apps, news tabs, and to-do lists. The routing architecture also makes this a practical template for building any multi-tool chatbot where different questions need different data sources.
