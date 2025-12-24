import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("medication-onboarding")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).parent
PROMPTS_DIR = BASE_DIR / "prompts"

# Data directory: check local first (Docker), then parent (development)
if (BASE_DIR / "data").exists():
    DATA_DIR = BASE_DIR / "data"
else:
    DATA_DIR = BASE_DIR.parent / "data"


def load_json(filename: str) -> dict | list:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}. Checked: {BASE_DIR / 'data'} and {BASE_DIR.parent / 'data'}"
        )
    with open(path) as f:
        return json.load(f)


def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename) as f:
        return f.read()


@dataclass
class SessionState:
    patient: dict = field(default_factory=dict)
    medications: list = field(default_factory=list)
    availability: dict = field(default_factory=dict)
    education: dict = field(default_factory=dict)
    consented: bool = False
    medications_verified: bool = False
    confidence_score: Optional[int] = None
    concerns: list = field(default_factory=list)
    reminders: list = field(default_factory=list)
    scheduled_calls: list = field(default_factory=list)
    current_workflow: str = "welcome"
    agents: dict = field(default_factory=dict[str, Agent])
    prev_agent: Optional[Agent] = None
    ctx: Optional[JobContext] = None

    def load_data(self):
        self.patient = load_json("patient.json")
        self.medications = load_json("medications.json")
        self.availability = load_json("availability.json")
        self.education = load_json("education.json")

    def to_ui_state(self) -> dict:
        return {
            "patient": self.patient,
            "medications": self.medications,
            "consented": self.consented,
            "medicationsVerified": self.medications_verified,
            "confidenceScore": self.confidence_score,
            "concerns": self.concerns,
            "reminders": self.reminders,
            "scheduledCalls": self.scheduled_calls,
            "currentWorkflow": self.current_workflow,
        }


RunContext_T = RunContext[SessionState]


class BaseAgent(Agent):
    workflow_name: str = "unknown"

    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name}")

        state: SessionState = self.session.userdata
        state.current_workflow = self.workflow_name

        if state.ctx and state.ctx.room:
            await state.ctx.room.local_participant.set_attributes(
                {"state": json.dumps(state.to_ui_state())}
            )

        # Generate a reply when entering a new agent (after transfer)
        if state.prev_agent:
            self.session.generate_reply()

    async def _transfer_to_agent(self, name: str, context: RunContext_T) -> Agent:
        state = context.userdata
        current_agent = context.session.current_agent
        next_agent = state.agents[name]
        state.prev_agent = current_agent
        return next_agent

    async def _update_ui(self) -> None:
        state: SessionState = self.session.userdata
        if state.ctx and state.ctx.room:
            await state.ctx.room.local_participant.set_attributes(
                {"state": json.dumps(state.to_ui_state())}
            )


class WelcomeAgent(BaseAgent):
    workflow_name = "welcome"

    def __init__(self, state: SessionState) -> None:
        patient_name = state.patient.get("name", "there")
        prompt = load_prompt("welcome.txt").format(patient_name=patient_name)
        super().__init__(instructions=prompt)

    @function_tool
    async def record_consent(self, context: RunContext_T, consented: bool) -> str:
        """Record whether the patient consents to proceed with medication onboarding.

        Args:
            consented: True if patient agrees to proceed, False otherwise
        """
        state = context.userdata
        state.consented = consented
        await self._update_ui()
        if consented:
            return "Consent recorded. Continue with medication verification."
        return "Patient declined. Offer to reschedule or end the call politely."

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently when patient wants to reschedule. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)

    @function_tool
    async def transfer_to_verification(self, context: RunContext_T) -> Agent:
        """Call this tool silently after patient consents. Do not say anything before or after calling this tool."""
        state = context.userdata
        state.consented = True
        await self._update_ui()
        return await self._transfer_to_agent("verification", context)


class SchedulingAgent(BaseAgent):
    workflow_name = "scheduling"

    def __init__(self, state: SessionState) -> None:
        slots = state.availability.get("pharmacistSlots", [])
        available_times = "\n".join(
            [
                f"- {s['date']} at {s['time']} with {s['pharmacist']} [slot_id: {s['id']}]"
                for s in slots[:5]
            ]
        )
        prompt = load_prompt("scheduling.txt").format(available_times=available_times)
        super().__init__(instructions=prompt)

    @function_tool
    async def schedule_callback(self, context: RunContext_T, slot_id: str) -> str:
        """Schedule a callback for the medication onboarding review.

        Args:
            slot_id: The ID of the time slot (e.g., slot-001)
        """
        state = context.userdata
        slots = state.availability.get("pharmacistSlots", [])
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return "Sorry, that slot is no longer available. Please choose another."

        state.scheduled_calls.append(
            {
                "type": "callback",
                "date": slot["date"],
                "time": slot["time"],
                "reason": "Medication onboarding review",
            }
        )
        await self._update_ui()
        return f"Callback scheduled for {slot['date']} at {slot['time']}. Confirm with the patient and say goodbye."

    @function_tool
    async def schedule_pharmacist_call(
        self, context: RunContext_T, slot_id: str, reason: str
    ) -> str:
        """Schedule a pharmacist call for medication questions.

        Args:
            slot_id: The ID of the time slot (e.g., slot-001)
            reason: Brief reason for the call
        """
        state = context.userdata
        slots = state.availability.get("pharmacistSlots", [])
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return "Sorry, that slot is no longer available. Please choose another."

        state.scheduled_calls.append(
            {
                "type": "pharmacist",
                "date": slot["date"],
                "time": slot["time"],
                "pharmacist": slot["pharmacist"],
                "reason": reason,
            }
        )
        await self._update_ui()
        return f"Scheduled call with {slot['pharmacist']} on {slot['date']} at {slot['time']}."

    @function_tool
    async def transfer_to_verification(self, context: RunContext_T) -> Agent:
        """Call this tool silently if patient wants to continue with medication review now. Do not say anything."""
        state = context.userdata
        state.consented = True
        await self._update_ui()
        return await self._transfer_to_agent("verification", context)


class MedicationVerificationAgent(BaseAgent):
    workflow_name = "verification"

    def __init__(self, state: SessionState) -> None:
        meds_list = "\n".join(
            [
                f"- {m['name']} {m['dosage']} for {m['conditionName']}"
                for m in state.medications
            ]
        )
        prompt = load_prompt("verification.txt").format(meds_list=meds_list)
        super().__init__(instructions=prompt)

    @function_tool
    async def confirm_medications(self, context: RunContext_T, verified: bool) -> str:
        """Record whether the patient confirms their medications are correct.

        Args:
            verified: True if medications are correct, False if there are issues
        """
        state = context.userdata
        state.medications_verified = verified
        for med in state.medications:
            med["verified"] = verified
        await self._update_ui()
        if verified:
            return "Medications confirmed. Continue with confidence check."
        return "Patient has concerns. Offer to connect with pharmacist."

    @function_tool
    async def transfer_to_confidence(self, context: RunContext_T) -> Agent:
        """Call this tool silently after medications are verified. Do not say anything before or after calling this tool."""
        state = context.userdata
        state.medications_verified = True
        await self._update_ui()
        return await self._transfer_to_agent("confidence", context)

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently for medication concerns. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)


class ConfidenceBarrierAgent(BaseAgent):
    workflow_name = "confidence"

    def __init__(self, state: SessionState) -> None:
        prompt = load_prompt("confidence.txt")
        super().__init__(instructions=prompt)

    @function_tool
    async def record_confidence(
        self, context: RunContext_T, score: int, concerns: list[str]
    ) -> str:
        """Record the patient's confidence score and any concerns.

        Args:
            score: Confidence score from 1-10
            concerns: List of concerns (e.g., ["side effects", "cost"])
        """
        state = context.userdata
        state.confidence_score = score
        state.concerns = concerns
        await self._update_ui()

        if score <= 6:
            return f"Confidence score {score} recorded with concerns: {concerns}. Offer pharmacist call, then continue to education."
        return f"Good confidence score of {score}. Proceed to education."

    @function_tool
    async def transfer_to_education(self, context: RunContext_T) -> Agent:
        """Call this tool silently to continue to education. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("education", context)

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently if patient wants to talk to a pharmacist. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)


class EducationAgent(BaseAgent):
    workflow_name = "education"

    def __init__(self, state: SessionState) -> None:
        conditions = state.patient.get("conditions", [])
        education_content = []
        for cond in conditions:
            if cond in state.education:
                edu = state.education[cond]
                education_content.append(
                    f"{edu['condition'].upper()}:\n"
                    f"- Key info: {edu['medicationInfo']}\n"
                    f"- Warning: {edu['warningSign']}"
                )
        prompt = load_prompt("education.txt").format(
            education_content="\n\n".join(education_content)
        )
        super().__init__(instructions=prompt)

    @function_tool
    async def transfer_to_reminders(self, context: RunContext_T) -> Agent:
        """Call this tool silently after education is complete. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("reminders", context)

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently to schedule a pharmacist call. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)


class ReminderAgent(BaseAgent):
    workflow_name = "reminders"

    def __init__(self, state: SessionState) -> None:
        meds_schedule = "\n".join(
            [
                f"- {m['name']}: {m['frequency']} - {m['instructions']}"
                for m in state.medications
            ]
        )
        prompt = load_prompt("reminders.txt").format(meds_schedule=meds_schedule)
        super().__init__(instructions=prompt)

    @function_tool
    async def set_daily_reminder(
        self, context: RunContext_T, time: str, medication_names: list[str]
    ) -> str:
        """Set up a daily text reminder for medications.

        Args:
            time: Time for the reminder (e.g., "8:00 AM")
            medication_names: List of medication names to remind about
        """
        state = context.userdata
        state.reminders.append(
            {
                "type": "daily_text",
                "time": time,
                "medications": medication_names,
            }
        )
        await self._update_ui()
        return f"Daily reminder set for {time} for: {', '.join(medication_names)}"

    @function_tool
    async def set_calendar_reminder(
        self, context: RunContext_T, time: str, frequency: str
    ) -> str:
        """Add medication reminders to calendar.

        Args:
            time: Time for the reminder
            frequency: How often (daily, weekly)
        """
        state = context.userdata
        state.reminders.append(
            {
                "type": "calendar",
                "time": time,
                "frequency": frequency,
            }
        )
        await self._update_ui()
        return f"Calendar reminder added for {time}, {frequency}"

    @function_tool
    async def setup_auto_refill(self, context: RunContext_T) -> str:
        """Enable auto-refill for the patient's medications."""
        state = context.userdata
        state.reminders.append(
            {
                "type": "auto_refill",
                "enabled": True,
            }
        )
        await self._update_ui()
        return "Auto-refill has been enabled for your medications."

    @function_tool
    async def transfer_to_wrapup(self, context: RunContext_T) -> Agent:
        """Call this tool silently after reminders are set. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("wrapup", context)

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently to schedule help with routine setup. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)


class WrapUpAgent(BaseAgent):
    workflow_name = "wrapup"

    def __init__(self, state: SessionState) -> None:
        patient_name = state.patient.get("name", "").split()[0]
        conditions = ", ".join(
            [
                state.education.get(c, {}).get("condition", c)
                for c in state.patient.get("conditions", [])
            ]
        )
        prompt = load_prompt("wrapup.txt").format(
            patient_name=patient_name, conditions=conditions
        )
        super().__init__(instructions=prompt)

    @function_tool
    async def schedule_followup(self, context: RunContext_T, days: int) -> str:
        """Schedule a follow-up check-in call.

        Args:
            days: Number of days until follow-up (7 or 30)
        """
        state = context.userdata
        followup_type = "7-day check-in" if days <= 7 else "30-day check-in"
        state.scheduled_calls.append(
            {
                "type": "followup",
                "days": days,
                "description": followup_type,
            }
        )
        await self._update_ui()
        return f"Follow-up scheduled for {days} days from now."

    @function_tool
    async def transfer_to_scheduling(self, context: RunContext_T) -> Agent:
        """Call this tool silently to schedule a specific call time. Do not say anything before or after calling this tool."""
        return await self._transfer_to_agent("scheduling", context)

    @function_tool
    async def end_call(self, context: RunContext_T) -> str:
        """End the call gracefully."""
        state = context.userdata
        state.current_workflow = "completed"
        await self._update_ui()
        return "Call completed. Say a warm goodbye."


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    load_dotenv(dotenv_path=".env.local")

    state = SessionState(ctx=ctx)
    state.load_data()

    agent_classes = [
        ("welcome", WelcomeAgent),
        ("scheduling", SchedulingAgent),
        ("verification", MedicationVerificationAgent),
        ("confidence", ConfidenceBarrierAgent),
        ("education", EducationAgent),
        ("reminders", ReminderAgent),
        ("wrapup", WrapUpAgent),
    ]
    state.agents = {name: cls(state) for name, cls in agent_classes}

    session = AgentSession[SessionState](
        userdata=state,
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(
            model="gpt-4.1-mini", parallel_tool_calls=False, temperature=0.4
        ),
        tts=cartesia.TTS(voice="6f84f4b8-58a2-430c-8c79-688dad597532", speed="normal"),
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(),
    )

    await session.start(
        agent=state.agents["welcome"],
        room=ctx.room,
    )

    await session.say(
        f"Hi {state.patient.get('name', '').split()[0]}, this is your OneHealthLink medication assistant. "
        "I'm here to help you understand your new medications and answer any questions. "
        "Is now a good time to chat for a few minutes?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
