# HealthAssist Medication Onboarding Demo

This is a LiveKit demo for HealthAssist that demonstrates an agent helping patients with medication onboarding.

## Project Requirements

- Keep all mock data (medication calendar, availability) in the `data/` folder so it can be shared by the agent and frontend
- The app doesn't need to be stateful - it's just a demo. UI updates can be done via LiveKit RPC OR by updating the data folder, whichever is cleaner and easier to read
- Reminders/user-set actions should show up in the UI in real-time

## Overall Coding Guidelines

- Keep code short and concise
- Refactor where possible to reuse components
- Refer to https://github.com/livekit/agents/tree/main/examples for best practices
- Use AgentTasks whenever it makes sense
- Use multiple agents and handoffs
- Make sure the UI has a text mode so we don't have to use voice to chat with the agent
- Don't use emojis. Keep the code self-explanatory so it's easy to understand while reading

# Agent

The agent guides the user through multiple workflows. At any point, the user should be able to switch to a different flow.

The messages are guidelines. You don't have to follow them exactly. You can use session.generate_reply and a system prompt. For the very first message of the agent I would use say so we don't need an LLM call to block latency.

## Objective

Digitally onboard a member who has newly filled one or more STARS-related medications (D08 Diabetes, D09 Hypertension, D10 Cholesterol).

**Conditions**: Hypertension (HTN), Diabetes (DM), Cholesterol (CHOL)

**Goals**: Improve first-fill adherence, educate with empathy, escalate intelligently

## Workflows

### 1. Welcome and Consent

**Bot greeting:**
"My job is to help you understand what your new medication does, how to take it safely, and what to expect."

**Goals:**

- Get their consent to proceed with the medication and offer to transfer to a different agent if needed
- Schedule a call for later if now's not a good time
  - Transfer to the scheduling agent which hits the calendar availability endpoint and loads all the data
- Move on to medication verification if they consent and don't want to reschedule

### 2. Medication Verification

**Bot greeting:**
"I see you recently filled:
• Lisinopril (for blood pressure)
• Metformin (for blood sugar)
• Atorvastatin (for cholesterol)
Are these correct?"

Pull the medication from a mock API which gets data from the `/data` folder.

**Goals:**

- User confirms "Yes, that's right" → transfer to confidence and barrier steps
- User says "Not sure / something looks wrong or I take others too" → offer pharmacist call → offer live chat or call. Move to calendar scheduling agent (same as Welcome and Consent flow)

**Escalation script:**
"No problem — sometimes records differ. Would you like to connect with a pharmacist to double-check and verify that the medications on our file are correct?"

### 3. Confidence & Barriers Check

**Bot questions:**
"How confident are you about starting your new medication?" (Scale 1–10)

"Do you have any concerns?"
• Possible side effects
• Cost/refill issues
• Unsure why I need it
• None right now

**Goals:**

- Confidence ≤6 → offer live chat or schedule pharmacist call, go through the same scheduling flow
- Confidence >6 → transfer to education module

### 4. Education Module

| Condition    | Chatbot Script                                                                                                                           | Optional Actions                             | KB Needed                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| Hypertension | "This medicine relaxes your blood vessels so your heart doesn't work as hard. Keep taking it even if your blood pressure feels normal."  | Talk to a pharmacist about side effects      | HTN education module, lifestyle tips, teach-back questions   |
| Diabetes     | "Metformin helps your body use sugar better and protects your kidneys and heart. Take with food to reduce stomach upset."                | Ask how metformin works                      | DM education module, hypoglycemia prevention, meal timing    |
| Cholesterol  | "Statins protect your heart by lowering 'bad' cholesterol. You won't feel different day-to-day, but they prevent future heart problems." | Schedule pharmacist call to review your meds | CHOL education module, myth/fact sheet, side effect handling |

**Goals:**

- Make sure the user gets their questions answered about their condition
- Give them a brief summary of what they need to know about their conditions

### 5. Build Routine & Reminders

**Bot question:**
"Would you like help remembering your meds?"

**Options:**

- Set daily text reminder
- Set up auto-refill
- Add to calendar
- Talk to someone about routine setup → move to calendar scheduling flow

**Goals:**

- Make sure user is set up for success and offer them help to take their meds

### 6. Wrap-Up & Reinforcement

**Bot closing:**
"You're off to a great start, [Name]! Taking your [blood pressure/diabetes/cholesterol] medication every day keeps your heart, kidneys, and eyes healthy. Would you like a quick follow-up in a week to check in?"

**Options:**

- Yes, check in next week
- Schedule call instead
- No thanks

**Implementation:**

- If yes: create follow-up reminder in system (Day 7 / Day 30)
- If call: launch scheduling widget

**KB Needed:**

- Reinforcement narratives ("How meds work together")

# Frontend

The main goal of the frontend is to:

1. **Show real-time conversation with the agent**

   - Ability to toggle text and voice mode
   - Use https://github.com/livekit-examples/agent-starter-react as an example of how chat bubbles and transcripts work

2. **Show user data and update in real-time**
   - User name email
   - Wether or not they consented to the flow
   - A list of medications
   - List of conditions
   - Live update of any reminders/schedules
   - At the end of the call: summary and feedback/concerns

# Configuration

Create a `.env` file in both frontend and agent folders where LiveKit API keys will be added (using `.env.local` format).

This app will be deployed on:

- LiveKit Cloud hosted agents
- Frontend in Next.js
