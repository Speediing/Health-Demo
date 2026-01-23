import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import boto3
from google.cloud.dialogflowcx_v3 import SessionsClient, types as dialogflow_types
from google.oauth2 import service_account
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
    room_io,
)
from livekit.agents.beta.workflows import WarmTransferTask
from livekit.agents.llm import ToolError
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("medication-onboarding")
logger.setLevel(logging.INFO)

# SIP Configuration for warm transfer to supervisor
SIP_TRUNK_ID = "ST_4Ct2FA2tqtEG"
DEFAULT_SUPERVISOR_PHONE = "+14039193117"  # Default fallback
SIP_NUMBER = "+18253054156"

# Amazon Lex Configuration for call center hours bot
LEX_BOT_ID = "VHSTLQZDML"
LEX_BOT_ALIAS_ID = "TSTALIASID"
LEX_LOCALE_ID = "en_US"
LEX_REGION = "us-east-1"

# Google Dialogflow Configuration for location finder bot
DIALOGFLOW_PROJECT_ID = os.environ.get("DIALOGFLOW_PROJECT_ID", "")
DIALOGFLOW_LOCATION = os.environ.get("DIALOGFLOW_LOCATION", "us-central1")
DIALOGFLOW_AGENT_ID = os.environ.get("DIALOGFLOW_AGENT_ID", "")

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
    lex_client: Any = None
    lex_bot_active: bool = False
    dialogflow_client: Any = None
    dialogflow_bot_active: bool = False
    current_llm: str = "openai"
    supervisor_phone: str = DEFAULT_SUPERVISOR_PHONE

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
            "lexBotActive": self.lex_bot_active,
            "dialogflowBotActive": self.dialogflow_bot_active,
            "currentLlm": self.current_llm,
        }


RunContext_T = RunContext[SessionState]


SUPERVISOR_SUMMARY_INSTRUCTIONS = """
Introduce the conversation from your perspective as the AI medication onboarding assistant:

WHO you're talking to (patient name if mentioned)
WHY they called (medication onboarding for new prescriptions)
WHERE in the workflow you are (welcome, verification, education, etc.)
WHY a human supervisor is being requested
Brief summary of any concerns or issues raised by the patient
"""


class BaseAgent(Agent):
    workflow_name: str = "unknown"
    llm_provider: str = "openai"  # Override in subclasses

    async def on_enter(self) -> None:
        agent_name = self.__class__.__name__
        logger.info(f"Entering {agent_name} with LLM: {self.llm_provider}")

        state: SessionState = self.session.userdata
        state.current_workflow = self.workflow_name
        state.current_llm = self.llm_provider
        # Clear bot indicators when entering a new agent
        state.lex_bot_active = False
        state.dialogflow_bot_active = False

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

    @function_tool
    async def transfer_to_supervisor(self, context: RunContext_T) -> None:
        """Called when the patient asks to speak to a human supervisor or pharmacist directly.
        This will put the patient on hold while the supervisor is connected.

        Ensure that the patient has confirmed that they want to be transferred before calling this tool.
        Examples on when this tool should be called:
        ----
        - Patient: Can I speak to a real person?
        - Assistant: Of course, let me connect you.
        ----
        - Patient: I'd like to talk to a pharmacist directly.
        - Assistant: Absolutely, I'll transfer you now.
        ----
        - Patient: I'm not comfortable discussing this with an AI.
        - Assistant: I understand completely. Let me get a human on the line.
        ----
        """
        state = context.userdata
        supervisor_phone = state.supervisor_phone
        logger.info(f"Initiating warm transfer to supervisor at {supervisor_phone}")
        await self.session.say(
            "Please hold while I connect you to a supervisor.",
            allow_interruptions=False,
        )
        try:
            result = await WarmTransferTask(
                target_phone_number=supervisor_phone,
                sip_trunk_id=SIP_TRUNK_ID,
                sip_number=SIP_NUMBER,
                chat_ctx=self.chat_ctx,
                extra_instructions=SUPERVISOR_SUMMARY_INSTRUCTIONS,
            )
        except ToolError as e:
            logger.error(f"Failed to transfer to supervisor with tool error: {e}")
            raise e
        except Exception as e:
            logger.exception("Failed to transfer to supervisor")
            raise ToolError(f"Failed to transfer to supervisor: {e}") from e

        logger.info(
            "Transfer to supervisor successful",
            extra={"supervisor_identity": result.human_agent_identity},
        )
        await self.session.say(
            "You are now connected with a supervisor. I'll be hanging up now. Take care!",
            allow_interruptions=False,
        )
        self.session.shutdown()

    @function_tool
    async def get_call_center_hours(self, context: RunContext_T, user_query: str) -> str:
        """Get call center hours information using the Lex bot.
        Call this tool when the patient asks about call center hours, support hours,
        when they can call back, or when agents are available.

        Args:
            user_query: The patient's question about call center hours
        """
        state = context.userdata
        if not state.lex_client:
            return "I'm sorry, I don't have access to call center hours information right now."

        try:
            # Set Lex bot active state and update UI
            state.lex_bot_active = True
            await self._update_ui()

            session_id = f"session-{id(state)}"
            response = state.lex_client.recognize_text(
                botId=LEX_BOT_ID,
                botAliasId=LEX_BOT_ALIAS_ID,
                localeId=LEX_LOCALE_ID,
                sessionId=session_id,
                text=user_query,
            )

            messages = response.get("messages", [])
            result = " ".join(msg.get("content", "") for msg in messages) if messages else "I couldn't find specific information about call center hours."

            # Keep lex_bot_active = True while the response is spoken
            # It will be cleared on next agent enter or next interaction
            return result

        except Exception as e:
            logger.error(f"Error querying Lex bot: {e}")
            # Clear Lex bot active state on error
            state.lex_bot_active = False
            await self._update_ui()
            return "I'm having trouble accessing call center hours right now. Please try again later."

    @function_tool
    async def get_closest_location(self, context: RunContext_T, user_query: str) -> str:
        """Get the closest pharmacy or healthcare location using the Dialogflow bot.
        Call this tool when the patient asks about finding the nearest location,
        closest pharmacy, where to pick up medications, or nearby healthcare facilities.

        Args:
            user_query: The patient's question about finding a location
        """
        state = context.userdata
        if not state.dialogflow_client:
            return "I'm sorry, I don't have access to location information right now."

        try:
            # Set Dialogflow bot active state and update UI
            state.dialogflow_bot_active = True
            await self._update_ui()

            # Build the session path
            session_id = str(uuid.uuid4())
            session_path = f"projects/{DIALOGFLOW_PROJECT_ID}/locations/{DIALOGFLOW_LOCATION}/agents/{DIALOGFLOW_AGENT_ID}/sessions/{session_id}"

            # Create the text input
            text_input = dialogflow_types.TextInput(text=user_query)
            query_input = dialogflow_types.QueryInput(
                text=text_input,
                language_code="en"
            )

            # Make the detect intent request
            request = dialogflow_types.DetectIntentRequest(
                session=session_path,
                query_input=query_input
            )
            response = state.dialogflow_client.detect_intent(request=request)

            # Extract the response messages
            query_result = response.query_result
            response_messages = query_result.response_messages
            result = " ".join(
                msg.text.text[0] for msg in response_messages
                if msg.text and msg.text.text
            ) if response_messages else "I couldn't find specific location information."

            # Keep dialogflow_bot_active = True while the response is spoken
            # It will be cleared on next agent enter or next interaction
            return result

        except Exception as e:
            logger.error(f"Error querying Dialogflow bot: {e}")
            # Clear Dialogflow bot active state on error
            state.dialogflow_bot_active = False
            await self._update_ui()
            return "I'm having trouble accessing location information right now. Please try again later."


class WelcomeAgent(BaseAgent):
    workflow_name = "welcome"
    llm_provider = "openai"

    def __init__(self, state: SessionState) -> None:
        patient_name = state.patient.get("name", "there")
        prompt = load_prompt("welcome.txt").format(patient_name=patient_name)
        super().__init__(instructions=prompt, llm="openai/gpt-4o-mini")

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
    llm_provider = "gemini"

    def __init__(self, state: SessionState) -> None:
        slots = state.availability.get("pharmacistSlots", [])
        available_times = "\n".join(
            [
                f"- {s['date']} at {s['time']} with {s['pharmacist']} [slot_id: {s['id']}]"
                for s in slots[:5]
            ]
        )
        prompt = load_prompt("scheduling.txt").format(available_times=available_times)
        super().__init__(instructions=prompt, llm="google/gemini-2.0-flash")

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
    llm_provider = "gemini"

    def __init__(self, state: SessionState) -> None:
        meds_list = "\n".join(
            [
                f"- {m['name']} {m['dosage']} for {m['conditionName']}"
                for m in state.medications
            ]
        )
        prompt = load_prompt("verification.txt").format(meds_list=meds_list)
        super().__init__(instructions=prompt, llm="google/gemini-2.0-flash")

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
    llm_provider = "openai"

    def __init__(self, state: SessionState) -> None:
        prompt = load_prompt("confidence.txt")
        super().__init__(instructions=prompt, llm="openai/gpt-4o-mini")

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
    llm_provider = "gemini"

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
        super().__init__(instructions=prompt, llm="google/gemini-2.0-flash")

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
    llm_provider = "openai"

    def __init__(self, state: SessionState) -> None:
        meds_schedule = "\n".join(
            [
                f"- {m['name']}: {m['frequency']} - {m['instructions']}"
                for m in state.medications
            ]
        )
        prompt = load_prompt("reminders.txt").format(meds_schedule=meds_schedule)
        super().__init__(instructions=prompt, llm="openai/gpt-4o-mini")

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
    llm_provider = "gemini"

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
        super().__init__(instructions=prompt, llm="google/gemini-2.0-flash")

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


def get_supervisor_phone_from_participants(room) -> str:
    """Extract supervisor phone from participant metadata if available."""
    for participant in room.remote_participants.values():
        if participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                if "supervisorPhone" in metadata and metadata["supervisorPhone"]:
                    logger.info(f"Found supervisor phone in participant metadata: {metadata['supervisorPhone']}")
                    return metadata["supervisorPhone"]
            except (json.JSONDecodeError, TypeError):
                pass
    return DEFAULT_SUPERVISOR_PHONE


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    load_dotenv(dotenv_path=".env.local")

    # Get supervisor phone from participant metadata (set by frontend)
    supervisor_phone = get_supervisor_phone_from_participants(ctx.room)

    state = SessionState(ctx=ctx, supervisor_phone=supervisor_phone)
    state.load_data()

    # Listen for participant attribute changes to update supervisor phone
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        if participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                if "supervisorPhone" in metadata and metadata["supervisorPhone"]:
                    state.supervisor_phone = metadata["supervisorPhone"]
                    logger.info(f"Updated supervisor phone from new participant: {state.supervisor_phone}")
            except (json.JSONDecodeError, TypeError):
                pass

    # Initialize Amazon Lex client for call center hours queries
    state.lex_client = boto3.client(
        "lexv2-runtime",
        region_name=LEX_REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    # Initialize Google Dialogflow client for location queries
    if DIALOGFLOW_PROJECT_ID and DIALOGFLOW_AGENT_ID:
        try:
            client_options = {"api_endpoint": f"{DIALOGFLOW_LOCATION}-dialogflow.googleapis.com"}

            # Load credentials from environment variable
            google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            if google_creds_json:
                creds_info = json.loads(google_creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_info)
                state.dialogflow_client = SessionsClient(credentials=credentials, client_options=client_options)
                logger.info("Dialogflow client initialized with service account credentials")
            else:
                # Fall back to default credentials (for local development)
                state.dialogflow_client = SessionsClient(client_options=client_options)
                logger.info("Dialogflow client initialized with default credentials")
        except Exception as e:
            logger.error(f"Failed to initialize Dialogflow client: {e}")
            state.dialogflow_client = None
    else:
        logger.warning("Dialogflow not configured - missing PROJECT_ID or AGENT_ID")

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
        stt="deepgram/nova-3",
        tts="cartesia/sonic-3",
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(),
    )

    await session.start(
        agent=state.agents["welcome"],
        room=ctx.room,
        room_options=room_io.RoomOptions(
            delete_room_on_close=False,  # Keep the room open for supervisor transfer
        ),
    )

    await session.say(
        f"Hi {state.patient.get('name', '').split()[0]}, this is your HealthAssist medication assistant. "
        "I'm here to help you understand your new medications and answer any questions. "
        "Is now a good time to chat for a few minutes?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
