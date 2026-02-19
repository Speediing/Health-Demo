"use client";

import { SessionState, CalendarEvent, BookedFlight, MovedMeeting } from "../types";
import {
  Calendar,
  Plane,
  ArrowRight,
  Clock,
  Users,
  Check,
  MoveRight,
} from "lucide-react";

interface CalendarDashboardProps {
  state: SessionState | null;
}

function EventCard({ event }: { event: CalendarEvent }) {
  const isMoved = event.moved;

  return (
    <div className={`event-card ${isMoved ? "moved" : ""}`}>
      <div className="event-time">
        <Clock size={12} />
        <span>{event.start_time} - {event.end_time}</span>
      </div>
      <div className="event-title">{event.title}</div>
      <div className="event-attendees">
        <Users size={12} />
        <span>{event.attendees.join(", ")}</span>
      </div>
      {isMoved && (
        <div className="event-moved-badge">
          <MoveRight size={12} />
          <span>Rescheduled</span>
        </div>
      )}
    </div>
  );
}

function CalendarSection({ events }: { events: CalendarEvent[] }) {
  const eventsByDate = events.reduce((acc, evt) => {
    const key = `${evt.day}, ${evt.date}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(evt);
    return acc;
  }, {} as Record<string, CalendarEvent[]>);

  const sortedDates = Object.keys(eventsByDate).sort((a, b) => {
    const dateA = a.split(", ")[1];
    const dateB = b.split(", ")[1];
    return dateA.localeCompare(dateB);
  });

  return (
    <div className="calendar-section">
      <div className="section-header">
        <Calendar size={18} />
        <h3>This Week</h3>
      </div>
      <div className="calendar-days">
        {sortedDates.map((dateKey) => (
          <div key={dateKey} className="calendar-day">
            <div className="day-header">{dateKey}</div>
            <div className="day-events">
              {eventsByDate[dateKey].map((evt) => (
                <EventCard key={evt.id} event={evt} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FlightsSection({ flights }: { flights: BookedFlight[] }) {
  if (flights.length === 0) return null;

  return (
    <div className="flights-section">
      <div className="section-header">
        <Plane size={18} />
        <h3>Booked Flights</h3>
        <span className="flight-count">{flights.length}</span>
      </div>
      <div className="flights-list">
        {flights.map((flight) => (
          <div key={flight.id} className="flight-card">
            <div className="flight-airline">{flight.airline}</div>
            <div className="flight-route">
              <span>{flight.route.split(" to ")[0]}</span>
              <ArrowRight size={14} />
              <span>{flight.route.split(" to ")[1]}</span>
            </div>
            <div className="flight-details">
              <div className="flight-time">
                <Clock size={12} />
                <span>{flight.departure_time} - {flight.arrival_time}</span>
              </div>
              <div className="flight-date">{flight.departure_date}</div>
              <div className="flight-price">{flight.price}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MovedMeetingsSection({ meetings }: { meetings: MovedMeeting[] }) {
  if (meetings.length === 0) return null;

  return (
    <div className="moved-section">
      <div className="section-header">
        <MoveRight size={18} />
        <h3>Rescheduled Meetings</h3>
      </div>
      <div className="moved-list">
        {meetings.map((meeting) => (
          <div key={meeting.event_id} className="moved-card">
            <div className="moved-title">
              <Check size={14} />
              <span>{meeting.title}</span>
            </div>
            <div className="moved-change">
              <div className="moved-old">{meeting.old}</div>
              <ArrowRight size={12} />
              <div className="moved-new">{meeting.new}</div>
            </div>
            <div className="moved-attendees">
              <Users size={12} />
              <span>{meeting.attendees.join(", ")} notified</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CalendarDashboard({ state }: CalendarDashboardProps) {
  if (!state) {
    return null;
  }

  return (
    <div className="calendar-dashboard">
      <CalendarSection events={state.calendarEvents || []} />
      <FlightsSection flights={state.bookedFlights || []} />
      <MovedMeetingsSection meetings={state.movedMeetings || []} />
    </div>
  );
}
