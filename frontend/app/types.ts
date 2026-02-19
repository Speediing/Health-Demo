export interface CalendarEvent {
  id: string;
  title: string;
  date: string;
  day: string;
  start_time: string;
  end_time: string;
  attendees: string[];
  moved?: boolean;
  original_date?: string;
  original_start_time?: string;
  original_end_time?: string;
  type?: "meeting" | "travel";
}

export interface BookedFlight {
  id: string;
  airline: string;
  route: string;
  departure_date: string;
  departure_time: string;
  arrival_time: string;
  price: string;
}

export interface MovedMeeting {
  event_id: string;
  title: string;
  old: string;
  new: string;
  attendees: string[];
}

export interface SessionState {
  calendarEvents: CalendarEvent[];
  bookedFlights: BookedFlight[];
  movedMeetings: MovedMeeting[];
}
