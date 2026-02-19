import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobRequest,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("calendar-assistant")
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
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path) as f:
        return json.load(f)


def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename) as f:
        return f.read()


# --- Hardcoded data ---

CALENDAR_EVENTS = [
    {
        "id": "evt-001",
        "title": "Sprint Planning",
        "date": "2026-02-23",
        "day": "Monday",
        "start_time": "9:00 AM",
        "end_time": "10:00 AM",
        "attendees": ["Jordan Lee", "Priya Patel"],
    },
    {
        "id": "evt-002",
        "title": "1:1 with Manager",
        "date": "2026-02-23",
        "day": "Monday",
        "start_time": "2:00 PM",
        "end_time": "2:30 PM",
        "attendees": ["Alex Chen"],
    },
    {
        "id": "evt-003",
        "title": "Design Review",
        "date": "2026-02-24",
        "day": "Tuesday",
        "start_time": "10:00 AM",
        "end_time": "11:00 AM",
        "attendees": ["Sam Rivera", "Jordan Lee"],
    },
    {
        "id": "evt-004",
        "title": "Team Standup",
        "date": "2026-02-24",
        "day": "Tuesday",
        "start_time": "9:00 AM",
        "end_time": "9:15 AM",
        "attendees": ["Full Team"],
    },
    {
        "id": "evt-005",
        "title": "Client Presentation",
        "date": "2026-02-25",
        "day": "Wednesday",
        "start_time": "11:00 AM",
        "end_time": "12:00 PM",
        "attendees": ["Priya Patel", "External Client"],
    },
    {
        "id": "evt-006",
        "title": "Lunch with VP of Engineering",
        "date": "2026-02-25",
        "day": "Wednesday",
        "start_time": "12:30 PM",
        "end_time": "1:30 PM",
        "attendees": ["Taylor Kim"],
    },
    {
        "id": "evt-007",
        "title": "Team Standup",
        "date": "2026-02-26",
        "day": "Thursday",
        "start_time": "9:00 AM",
        "end_time": "9:15 AM",
        "attendees": ["Full Team"],
    },
    {
        "id": "evt-008",
        "title": "Architecture Deep Dive",
        "date": "2026-02-26",
        "day": "Thursday",
        "start_time": "2:00 PM",
        "end_time": "3:30 PM",
        "attendees": ["Jordan Lee", "Sam Rivera", "Alex Chen"],
    },
    {
        "id": "evt-009",
        "title": "Friday Wrap-up",
        "date": "2026-02-27",
        "day": "Friday",
        "start_time": "4:00 PM",
        "end_time": "4:30 PM",
        "attendees": ["Full Team"],
    },
]

FLIGHT_OPTIONS = [
    {
        "id": "flight-001",
        "airline": "WestJet",
        "route": "Calgary (YYC) to Vancouver (YVR)",
        "departure_date": "2026-02-23",
        "departure_time": "7:00 AM",
        "arrival_time": "8:15 AM",
        "price": "$289",
    },
    {
        "id": "flight-002",
        "airline": "Air Canada",
        "route": "Calgary (YYC) to Vancouver (YVR)",
        "departure_date": "2026-02-23",
        "departure_time": "12:30 PM",
        "arrival_time": "1:45 PM",
        "price": "$345",
    },
    {
        "id": "flight-003",
        "airline": "WestJet",
        "route": "Calgary (YYC) to Vancouver (YVR)",
        "departure_date": "2026-02-24",
        "departure_time": "6:00 AM",
        "arrival_time": "7:15 AM",
        "price": "$259",
    },
    {
        "id": "flight-004",
        "airline": "Air Canada",
        "route": "Vancouver (YVR) to Calgary (YYC)",
        "departure_date": "2026-02-27",
        "departure_time": "5:00 PM",
        "arrival_time": "7:30 PM",
        "price": "$310",
    },
    {
        "id": "flight-005",
        "airline": "WestJet",
        "route": "Vancouver (YVR) to Calgary (YYC)",
        "departure_date": "2026-02-27",
        "departure_time": "8:00 PM",
        "arrival_time": "10:30 PM",
        "price": "$275",
    },
]


@dataclass
class SessionState:
    calendar_events: list = field(default_factory=list)
    booked_flights: list = field(default_factory=list)
    moved_meetings: list = field(default_factory=list)
    ctx: Optional[JobContext] = None

    def load_data(self):
        self.calendar_events = [evt.copy() for evt in CALENDAR_EVENTS]

    def to_ui_state(self) -> dict:
        """Serialize state to a dict with camelCase keys matching the frontend SessionState interface."""
        moved_ids = {m["event_id"] for m in self.moved_meetings}
        calendar_events = []
        for evt in self.calendar_events:
            ce = {
                "id": evt["id"],
                "title": evt["title"],
                "date": evt["date"],
                "day": evt["day"],
                "start_time": evt["start_time"],
                "end_time": evt["end_time"],
                "attendees": evt["attendees"],
                "moved": evt["id"] in moved_ids,
                "type": evt.get("type", "meeting"),
            }
            # Include original times if the event was moved
            if evt["id"] in moved_ids:
                moved_info = next(m for m in self.moved_meetings if m["event_id"] == evt["id"])
                ce["original_date"] = moved_info.get("original_date", "")
                ce["original_start_time"] = moved_info.get("original_start_time", "")
                ce["original_end_time"] = moved_info.get("original_end_time", "")
            calendar_events.append(ce)

        booked_flights = [
            {
                "id": f["id"],
                "airline": f["airline"],
                "route": f["route"],
                "departure_date": f["departure_date"],
                "departure_time": f["departure_time"],
                "arrival_time": f["arrival_time"],
                "price": f["price"],
            }
            for f in self.booked_flights
        ]

        moved_meetings = [
            {
                "event_id": m["event_id"],
                "title": m["title"],
                "old": m["old"],
                "new": m["new"],
                "attendees": m["attendees"],
            }
            for m in self.moved_meetings
        ]

        return {
            "calendarEvents": calendar_events,
            "bookedFlights": booked_flights,
            "movedMeetings": moved_meetings,
        }


RunContext_T = RunContext[SessionState]


class CalendarAssistant(Agent):
    def __init__(self, state: SessionState) -> None:
        events_text = "\n".join(
            f"- [id: {evt['id']}] {evt['title']} on {evt['day']} {evt['date']} from {evt['start_time']} to {evt['end_time']} "
            f"(attendees: {', '.join(evt['attendees'])})"
            for evt in state.calendar_events
        )
        prompt = load_prompt("calendar_assistant.txt").format(calendar_events=events_text)
        super().__init__(instructions=prompt, llm="openai/gpt-4o-mini")

    async def _update_ui(self, context: RunContext_T) -> None:
        """Push current state to the frontend via participant attributes."""
        state = context.userdata
        if state.ctx and state.ctx.room and state.ctx.room.local_participant:
            ui_state = state.to_ui_state()
            await state.ctx.room.local_participant.set_attributes(
                {"state": json.dumps(ui_state)}
            )

    @function_tool
    async def get_calendar_events(
        self, context: RunContext_T, start_date: str, end_date: str
    ) -> str:
        """Look up the user's calendar events for a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        state = context.userdata
        events = [
            evt for evt in state.calendar_events
            if start_date <= evt["date"] <= end_date
        ]
        if not events:
            return f"No events found between {start_date} and {end_date}."

        result = f"Calendar events from {start_date} to {end_date}:\n"
        for evt in events:
            result += (
                f"- {evt['title']} on {evt['day']} {evt['date']} "
                f"from {evt['start_time']} to {evt['end_time']} "
                f"(attendees: {', '.join(evt['attendees'])})\n"
            )
        await self._update_ui(context)
        return result

    @function_tool
    async def search_flights(
        self, context: RunContext_T, origin: str, destination: str
    ) -> str:
        """Search for available flights between two cities.

        Args:
            origin: Origin city name (e.g., "Calgary")
            destination: Destination city name (e.g., "Vancouver")
        """
        origin_lower = origin.lower()
        dest_lower = destination.lower()

        matching = [
            f for f in FLIGHT_OPTIONS
            if origin_lower in f["route"].lower() and dest_lower in f["route"].lower()
            and f["route"].lower().index(origin_lower) < f["route"].lower().index(dest_lower)
        ]

        if not matching:
            return f"No flights found from {origin} to {destination}."

        result = f"Available flights from {origin} to {destination}:\n"
        for f in matching:
            result += (
                f"- {f['airline']} on {f['departure_date']}: "
                f"departs {f['departure_time']}, arrives {f['arrival_time']} "
                f"({f['price']}) [flight_id: {f['id']}]\n"
            )
        return result

    @function_tool
    async def book_flight(self, context: RunContext_T, flight_id: str) -> str:
        """Book a specific flight for the user.

        Args:
            flight_id: The ID of the flight to book (e.g., "flight-001")
        """
        state = context.userdata
        flight = next((f for f in FLIGHT_OPTIONS if f["id"] == flight_id), None)
        if not flight:
            return "Sorry, that flight is no longer available."

        state.booked_flights.append(flight)

        # Add travel block to the calendar
        try:
            day_name = datetime.strptime(flight["departure_date"], "%Y-%m-%d").strftime("%A")
        except ValueError:
            day_name = ""

        travel_event = {
            "id": f"travel-{flight['id']}",
            "title": f"✈ {flight['airline']} — {flight['route']}",
            "date": flight["departure_date"],
            "day": day_name,
            "start_time": flight["departure_time"],
            "end_time": flight["arrival_time"],
            "attendees": [],
            "type": "travel",
        }
        state.calendar_events.append(travel_event)
        # Sort events by date then start_time so the travel block appears in order
        state.calendar_events.sort(key=lambda e: (e["date"], e["start_time"]))

        logger.info(f"Booked flight: {flight['airline']} {flight['route']} on {flight['departure_date']}")
        await self._update_ui(context)
        return (
            f"Flight booked! {flight['airline']} from {flight['route']} "
            f"on {flight['departure_date']}, departing at {flight['departure_time']} "
            f"and arriving at {flight['arrival_time']}. Price: {flight['price']}. "
            f"I've also added the travel time to your calendar."
        )

    @function_tool
    async def move_meeting(
        self, context: RunContext_T, event_id: str, new_date: str, new_start_time: str, new_end_time: str
    ) -> str:
        """Move a calendar meeting to a new date and time. This will notify all attendees.

        Args:
            event_id: The ID of the calendar event to move (e.g., "evt-001")
            new_date: The new date in YYYY-MM-DD format
            new_start_time: The new start time (e.g., "3:00 PM")
            new_end_time: The new end time (e.g., "4:00 PM")
        """
        state = context.userdata
        event = next((e for e in state.calendar_events if e["id"] == event_id), None)
        if not event:
            return "Sorry, I couldn't find that calendar event."

        old_info = f"{event['title']} on {event['date']} from {event['start_time']} to {event['end_time']}"
        original_date = event["date"]
        original_start = event["start_time"]
        original_end = event["end_time"]

        event["date"] = new_date
        event["start_time"] = new_start_time
        event["end_time"] = new_end_time

        state.moved_meetings.append({
            "event_id": event_id,
            "title": event["title"],
            "old": old_info,
            "new": f"{new_date} from {new_start_time} to {new_end_time}",
            "attendees": event["attendees"],
            "original_date": original_date,
            "original_start_time": original_start,
            "original_end_time": original_end,
        })

        attendees_str = ", ".join(event["attendees"])
        logger.info(f"Moved meeting: {event['title']} to {new_date} {new_start_time}-{new_end_time}")
        await self._update_ui(context)
        return (
            f"Done! Moved '{event['title']}' to {new_date} from {new_start_time} to {new_end_time}. "
            f"Calendar invites have been updated and {attendees_str} have been notified."
        )


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    load_dotenv(dotenv_path=".env.local")

    state = SessionState(ctx=ctx)
    state.load_data()

    agent = CalendarAssistant(state)

    session = AgentSession[SessionState](
        userdata=state,
        stt="deepgram/nova-3",
        tts="elevenlabs/eleven_turbo_v2_5:Xb7hH8MSUJpSbSDYk0k2",
        turn_detection=MultilingualModel(),
        vad=silero.VAD.load(),
    )

    await session.start(
        agent=agent,
        room=ctx.room,
    )

    # Push initial calendar state to the frontend
    ui_state = state.to_ui_state()
    await ctx.room.local_participant.set_attributes(
        {"state": json.dumps(ui_state)}
    )

    await session.say(
        "Hi there! I'm your calendar assistant. How can I help you today?",
        allow_interruptions=True,
    )


async def request_fnc(req: JobRequest) -> None:
    await req.accept()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, request_fnc=request_fnc))
