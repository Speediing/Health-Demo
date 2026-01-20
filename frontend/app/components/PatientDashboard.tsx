"use client";

import { SessionState } from "../types";
import { WorkflowProgress } from "./WorkflowProgress";
import { MedicationsList } from "./MedicationsList";
import { RemindersList } from "./RemindersList";
import { LexBotIndicator } from "./LexBotIndicator";
import { User, Mail, Phone, CheckCircle, XCircle, Activity } from "lucide-react";

interface PatientDashboardProps {
  state: SessionState | null;
}

export function PatientDashboard({ state }: PatientDashboardProps) {
  if (!state) {
    return null;
  }

  return (
    <div className="patient-dashboard">
      <div className="patient-info">
        <div className="patient-header">
          <div className="patient-avatar">
            <User size={24} />
          </div>
          <div className="patient-details">
            <h2>{state.patient.name}</h2>
            <div className="patient-contact">
              <span>
                <Mail size={12} />
                {state.patient.email}
              </span>
            </div>
          </div>
        </div>
        <div className="patient-status">
          <div className={`status-item ${state.consented ? "active" : ""}`}>
            {state.consented ? <CheckCircle size={14} /> : <XCircle size={14} />}
            <span>Consent</span>
          </div>
          {state.confidenceScore !== null && (
            <div className="status-item confidence">
              <Activity size={14} />
              <span>Confidence: {state.confidenceScore}/10</span>
            </div>
          )}
        </div>
        {state.concerns.length > 0 && (
          <div className="concerns-list">
            <span className="concerns-label">Concerns:</span>
            {state.concerns.map((concern, i) => (
              <span key={i} className="concern-tag">
                {concern}
              </span>
            ))}
          </div>
        )}
      </div>

      <LexBotIndicator active={state.lexBotActive ?? false} />

      <WorkflowProgress currentStep={state.currentWorkflow} currentLlm={state.currentLlm} />

      <MedicationsList
        medications={state.medications}
        verified={state.medicationsVerified}
      />

      <RemindersList
        reminders={state.reminders}
        scheduledCalls={state.scheduledCalls}
      />
    </div>
  );
}

