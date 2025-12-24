"use client";

import { Medication } from "../types";
import { Pill, Check, Clock } from "lucide-react";

interface MedicationsListProps {
  medications: Medication[];
  verified: boolean;
}

const CONDITION_COLORS: Record<string, string> = {
  HTN: "#3b82f6",
  DM: "#8b5cf6",
  CHOL: "#f59e0b",
};

export function MedicationsList({ medications, verified }: MedicationsListProps) {
  return (
    <div className="medications-list">
      <div className="section-header">
        <Pill size={18} />
        <h3>Medications</h3>
        {verified && (
          <span className="verified-badge">
            <Check size={12} />
            Verified
          </span>
        )}
      </div>
      <div className="medications-grid">
        {medications.map((med) => (
          <div key={med.id} className="medication-card">
            <div
              className="condition-indicator"
              style={{ backgroundColor: CONDITION_COLORS[med.condition] || "#6b7280" }}
            />
            <div className="medication-content">
              <div className="medication-header">
                <span className="medication-name">{med.name}</span>
                <span className="medication-dosage">{med.dosage}</span>
              </div>
              <span className="medication-condition">{med.conditionName}</span>
              <span className="medication-frequency">{med.frequency}</span>
            </div>
            <div className="medication-status">
              {med.verified ? (
                <Check size={16} className="verified-icon" />
              ) : (
                <Clock size={16} className="pending-icon" />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

