---
title: Morning Briefing Bot
emoji: ☀️
colorFrom: yellow
colorTo: yellow
sdk: gradio
sdk_version: 5.29.0
app_file: app.py
pinned: false
---

# ☀️ Morning Briefing Bot

> An AI-powered daily assistant — weather · news · tasks

## Overview

Morning Briefing Bot routes your requests to the right data source automatically. Ask for your "morning briefing" and it pulls today's weather forecast, current headlines, and your task list — then Claude composes a friendly summary.

## Tools

| Tool | Source | Key Required |
|------|--------|-------------|
| Weather | api.weather.gov | ❌ None |
| News | worldnewsapi.com | ✅ Free signup |
| Tasks | In-memory | ❌ None |
| LLM | Anthropic Claude Haiku | ✅ |

## How to Run Locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key
export WORLD_NEWS_API_KEY=your_key
python app.py
```