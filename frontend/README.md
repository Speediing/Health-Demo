# HealthAssist Frontend

A Next.js frontend for the medication onboarding voice agent demo.

## Features

- **Real-time conversation display** with chat bubbles showing transcriptions
- **Voice/Text mode toggle** - speak or type to interact with the agent
- **Live patient dashboard** showing:
  - Patient information
  - Session progress through workflow steps
  - Medications list with verification status
  - Reminders and scheduled calls (updated in real-time)
  - Consent and confidence tracking

## Setup

1. Create `.env.local` with your LiveKit credentials:
```bash
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
```

2. Install dependencies:
```bash
pnpm install
```

3. Run the development server:
```bash
pnpm dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Architecture

The frontend uses:
- **LiveKit Components React** for room connection and audio handling
- **LiveKit transcription hooks** for displaying real-time speech-to-text
- **Participant attributes** for receiving state updates from the agent

### Key Components

| Component | Purpose |
|-----------|---------|
| `RoomConnection` | Manages LiveKit room lifecycle and state |
| `ChatPanel` | Displays conversation with voice/text toggle |
| `PatientDashboard` | Shows patient info, progress, medications, reminders |
| `WorkflowProgress` | Visual step indicator for the onboarding flow |
| `MedicationsList` | Displays medications with verification status |
| `RemindersList` | Shows reminders and scheduled calls |

## Real-time Updates

The agent sets a `state` attribute on its participant containing the serialized `SessionState`. The frontend listens for `ParticipantAttributesChanged` events and updates the UI accordingly.

This enables instant UI updates when:
- Patient consents to the flow
- Medications are verified
- Confidence score is recorded
- Reminders are set
- Calls are scheduled
- Workflow step changes
