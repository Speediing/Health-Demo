# OneHealthLink Medication Onboarding Agent

A multi-agent voice assistant that guides patients through medication onboarding.

## Architecture

The agent uses a multi-agent system with handoffs between specialized agents:

| Agent | Purpose |
|-------|---------|
| **WelcomeAgent** | Greets patient, gets consent, offers rescheduling |
| **SchedulingAgent** | Handles pharmacist call scheduling |
| **MedicationVerificationAgent** | Verifies medications on file |
| **ConfidenceBarrierAgent** | Checks confidence level and concerns |
| **EducationAgent** | Educates about conditions and medications |
| **ReminderAgent** | Sets up medication reminders |
| **WrapUpAgent** | Closes the session and schedules follow-ups |

## Setup

1. Create `.env.local` from the example:
```bash
cp .env.example .env.local
```

2. Fill in your API keys:
```
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
CARTESIA_API_KEY=your-cartesia-key
```

3. Install dependencies:
```bash
uv sync
```

4. Run the agent:
```bash
uv run python main.py dev
```

## Docker Build

Build from the **project root** (not from inside `agent/`):

```bash
# From onehealth-demo/
docker build -f agent/Dockerfile -t onehealth-agent .
```

Run with environment variables:
```bash
docker run --env-file agent/.env.local onehealth-agent
```

## Real-time UI Updates

The agent updates the frontend in real-time using LiveKit participant attributes. The `SessionState` is serialized to JSON and set as the `state` attribute on the agent's local participant.

The frontend listens for `ParticipantAttributesChanged` events and parses the state to update the UI.

## Data Files

Mock data is stored in the `../data/` folder:
- `patient.json` - Patient information
- `medications.json` - Medications on file
- `availability.json` - Pharmacist scheduling slots
- `education.json` - Educational content for each condition

