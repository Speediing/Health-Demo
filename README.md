# HealthAssist Medication Onboarding Demo

A voice AI assistant that guides patients through medication onboarding, built with [LiveKit Agents](https://docs.livekit.io/agents/) and Next.js.

## Overview

This demo showcases a healthcare voice agent that helps patients:

- Verify their medications
- Learn about their conditions
- Set up medication reminders
- Schedule pharmacist calls

![HealthAssist Demo](https://img.shields.io/badge/LiveKit-Agents-blueviolet)

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js UI    │────▶│  LiveKit Cloud  │◀────│  Python Agent   │
│   (Frontend)    │     │                 │     │   (Backend)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [pnpm](https://pnpm.io/)
- [Python](https://www.python.org/) 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Required API Keys

| Service      | Description             | Get API Key                                                 |
| ------------ | ----------------------- | ----------------------------------------------------------- |
| **LiveKit**  | Real-time communication | [cloud.livekit.io](https://cloud.livekit.io)                |
| **OpenAI**   | LLM for conversation    | [platform.openai.com](https://platform.openai.com/api-keys) |
| **Deepgram** | Speech-to-text          | [console.deepgram.com](https://console.deepgram.com)        |
| **Cartesia** | Text-to-speech          | [play.cartesia.ai](https://play.cartesia.ai)                |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/livekit-examples/health-demo.git
cd health-demo
```

### 2. Set Up the Agent

```bash
cd agent

# Create environment file
cp .env.example .env.local

# Add your API keys to .env.local:
# LIVEKIT_URL=wss://your-project.livekit.cloud
# LIVEKIT_API_KEY=your-api-key
# LIVEKIT_API_SECRET=your-api-secret
# OPENAI_API_KEY=your-openai-key
# DEEPGRAM_API_KEY=your-deepgram-key
# CARTESIA_API_KEY=your-cartesia-key

# Install dependencies
uv sync

# Run the agent
uv run python main.py dev
```

### 3. Set Up the Frontend

```bash
cd frontend

# Create environment file
cp .env.example .env.local

# Add your LiveKit credentials to .env.local:
# LIVEKIT_URL=wss://your-project.livekit.cloud
# LIVEKIT_API_KEY=your-api-key
# LIVEKIT_API_SECRET=your-api-secret

# Install dependencies
pnpm install

# Run the development server
pnpm dev
```

### 4. Open the App

Visit [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
health-demo/
├── agent/                 # Python voice agent
│   ├── main.py           # Agent entry point
│   ├── prompts/          # LLM instruction prompts
│   ├── data/             # Mock patient data
│   └── pyproject.toml    # Python dependencies
├── frontend/             # Next.js web app
│   ├── app/              # App router pages
│   └── package.json      # Node dependencies
├── data/                 # Shared mock data
└── .github/workflows/    # CI/CD pipelines
```

## Deployment

### Agent (LiveKit Cloud)

The agent auto-deploys to LiveKit Cloud on commits to `main`. See [`.github/workflows/deploy-agent.yml`](.github/workflows/deploy-agent.yml).

Manual deploy:

```bash
cd agent
lk agent deploy --project your-project-name
```

### Frontend (Vercel)

The frontend auto-deploys to Vercel on commits to `main`.

## Links

- [GitHub Repository](https://github.com/livekit-examples/health-demo)

## Documentation

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [LiveKit React SDK](https://docs.livekit.io/realtime/client-sdks/react/)

## License

Apache 2.0
