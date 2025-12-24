"use client";

import { Reminder, ScheduledCall } from "../types";
import { Bell, Calendar, RefreshCw, Phone, Clock } from "lucide-react";

interface RemindersListProps {
  reminders: Reminder[];
  scheduledCalls: ScheduledCall[];
}

export function RemindersList({ reminders, scheduledCalls }: RemindersListProps) {
  const hasItems = reminders.length > 0 || scheduledCalls.length > 0;

  if (!hasItems) {
    return (
      <div className="reminders-list empty">
        <div className="section-header">
          <Bell size={18} />
          <h3>Reminders & Calls</h3>
        </div>
        <p className="empty-message">No reminders set yet</p>
      </div>
    );
  }

  return (
    <div className="reminders-list">
      <div className="section-header">
        <Bell size={18} />
        <h3>Reminders & Calls</h3>
      </div>
      <div className="reminders-grid">
        {reminders.map((reminder, index) => (
          <div key={`reminder-${index}`} className="reminder-card">
            {reminder.type === "daily_text" && (
              <>
                <Clock size={16} className="reminder-icon" />
                <div className="reminder-content">
                  <span className="reminder-title">Daily Text Reminder</span>
                  <span className="reminder-detail">{reminder.time}</span>
                  {reminder.medications && (
                    <span className="reminder-meds">
                      {reminder.medications.join(", ")}
                    </span>
                  )}
                </div>
              </>
            )}
            {reminder.type === "calendar" && (
              <>
                <Calendar size={16} className="reminder-icon" />
                <div className="reminder-content">
                  <span className="reminder-title">Calendar Reminder</span>
                  <span className="reminder-detail">
                    {reminder.time} - {reminder.frequency}
                  </span>
                </div>
              </>
            )}
            {reminder.type === "auto_refill" && (
              <>
                <RefreshCw size={16} className="reminder-icon" />
                <div className="reminder-content">
                  <span className="reminder-title">Auto-Refill</span>
                  <span className="reminder-detail">Enabled</span>
                </div>
              </>
            )}
          </div>
        ))}
        {scheduledCalls.map((call, index) => (
          <div key={`call-${index}`} className="reminder-card call">
            <Phone size={16} className="reminder-icon" />
            <div className="reminder-content">
              <span className="reminder-title">
                {call.type === "pharmacist" ? "Pharmacist Call" : "Follow-up Call"}
              </span>
              {call.date && call.time && (
                <span className="reminder-detail">
                  {call.date} at {call.time}
                </span>
              )}
              {call.pharmacist && (
                <span className="reminder-meds">with {call.pharmacist}</span>
              )}
              {call.description && (
                <span className="reminder-detail">{call.description}</span>
              )}
              {call.reason && (
                <span className="reminder-meds">{call.reason}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

