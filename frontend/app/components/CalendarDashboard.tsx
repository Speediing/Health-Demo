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
  MapPin,
  CalendarDays,
  TrendingUp,
} from "lucide-react";

interface CalendarDashboardProps {
  state: SessionState | null;
}

function DashboardHeader({ state }: { state: SessionState }) {
  const totalEvents = state.calendarEvents?.length || 0;
  const movedCount = state.movedMeetings?.length || 0;
  const flightCount = state.bookedFlights?.length || 0;

  return (
    <div className="dashboard-header">
      <div className="dashboard-title">
        <CalendarDays size={20} />
        <h2>Your Week at a Glance</h2>
      </div>
      <div className="dashboard-stats">
        <div className="stat-pill">
          <Calendar size={13} />
          <span>{totalEvents} events</span>
        </div>
        {flightCount > 0 && (
          <div className="stat-pill booked">
            <Plane size={13} />
            <span>{flightCount} flight{flightCount !== 1 ? "s" : ""}</span>
          </div>
        )}
        {movedCount > 0 && (
          <div className="stat-pill moved">
            <MoveRight size={13} />
            <span>{movedCount} moved</span>
          </div>
        )}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: CalendarEvent }) {
  const isMoved = event.moved;
  const isTravel = event.type === "travel";

  return (
    <div className={`event-card ${isMoved ? "moved" : ""} ${isTravel ? "travel" : ""}`}>
      <div className="event-card-left">
        <div className={`event-time-block ${isTravel ? "travel" : ""}`}>
          <span className="event-time-start">{event.start_time}</span>
          <span className="event-time-sep">-</span>
          <span className="event-time-end">{event.end_time}</span>
        </div>
      </div>
      <div className="event-card-right">
        <div className="event-title">
          {isTravel && <Plane size={13} className="travel-icon" />}
          {event.title}
        </div>
        {!isTravel && event.attendees.length > 0 && (
          <div className="event-attendees">
            <Users size={11} />
            <span>{event.attendees.join(", ")}</span>
          </div>
        )}
        {isTravel && (
          <div className="event-travel-badge">
            <Plane size={11} />
            <span>Travel</span>
          </div>
        )}
        {isMoved && (
          <div className="event-moved-badge">
            <MoveRight size={11} />
            <span>Rescheduled</span>
          </div>
        )}
      </div>
    </div>
  );
}

function formatDateLabel(dateKey: string): { dayName: string; dateStr: string } {
  const parts = dateKey.split(", ");
  return { dayName: parts[0], dateStr: parts[1] || "" };
}

function CalendarSection({ events }: { events: CalendarEvent[] }) {
  if (!events || events.length === 0) return null;

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
        <h3>Calendar</h3>
      </div>
      <div className="calendar-days">
        {sortedDates.map((dateKey) => {
          const { dayName, dateStr } = formatDateLabel(dateKey);
          const hasMovedEvent = eventsByDate[dateKey].some((e) => e.moved);

          return (
            <div
              key={dateKey}
              className={`calendar-day ${hasMovedEvent ? "has-changes" : ""}`}
            >
              <div className="day-header">
                <span className="day-name">{dayName}</span>
                <span className="day-date">{dateStr}</span>
                {hasMovedEvent && (
                  <span className="day-change-indicator">
                    <TrendingUp size={11} />
                    Updated
                  </span>
                )}
              </div>
              <div className="day-events">
                {eventsByDate[dateKey].map((evt) => (
                  <EventCard key={evt.id} event={evt} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FlightsSection({ flights }: { flights: BookedFlight[] }) {
  if (!flights || flights.length === 0) return null;

  return (
    <div className="flights-section">
      <div className="section-header">
        <Plane size={18} />
        <h3>Booked Flights</h3>
        <span className="flight-count">{flights.length}</span>
      </div>
      <div className="flights-list">
        {flights.map((flight) => {
          const [origin, destination] = flight.route.split(" to ");
          return (
            <div key={flight.id} className="flight-card">
              <div className="flight-card-top">
                <div className="flight-airline">{flight.airline}</div>
                <div className="flight-price">{flight.price}</div>
              </div>
              <div className="flight-route">
                <div className="flight-endpoint">
                  <MapPin size={14} />
                  <span>{origin}</span>
                </div>
                <div className="flight-arrow">
                  <div className="flight-arrow-line" />
                  <Plane size={14} />
                  <div className="flight-arrow-line" />
                </div>
                <div className="flight-endpoint">
                  <MapPin size={14} />
                  <span>{destination}</span>
                </div>
              </div>
              <div className="flight-details">
                <div className="flight-detail-item">
                  <Clock size={12} />
                  <span>
                    {flight.departure_time} - {flight.arrival_time}
                  </span>
                </div>
                <div className="flight-detail-item">
                  <Calendar size={12} />
                  <span>{flight.departure_date}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MovedMeetingsSection({ meetings }: { meetings: MovedMeeting[] }) {
  if (!meetings || meetings.length === 0) return null;

  return (
    <div className="moved-section">
      <div className="section-header">
        <MoveRight size={18} />
        <h3>Rescheduled Meetings</h3>
        <span className="moved-count">{meetings.length}</span>
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
    return (
      <div className="dashboard-empty">
        <Calendar size={40} />
        <p>Connecting to your calendar...</p>
      </div>
    );
  }

  return (
    <div className="calendar-dashboard">
      <DashboardHeader state={state} />
      <FlightsSection flights={state.bookedFlights || []} />
      <MovedMeetingsSection meetings={state.movedMeetings || []} />
      <CalendarSection events={state.calendarEvents || []} />
    </div>
  );
}
