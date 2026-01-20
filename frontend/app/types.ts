export interface Patient {
  id: string;
  name: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  conditions: string[];
}

export interface Medication {
  id: string;
  name: string;
  dosage: string;
  condition: string;
  conditionName: string;
  frequency: string;
  instructions: string;
  purpose: string;
  sideEffects: string[];
  verified: boolean;
}

export interface Reminder {
  type: "daily_text" | "calendar" | "auto_refill";
  time?: string;
  medications?: string[];
  frequency?: string;
  enabled?: boolean;
}

export interface ScheduledCall {
  type: "pharmacist" | "followup";
  date?: string;
  time?: string;
  pharmacist?: string;
  reason?: string;
  days?: number;
  description?: string;
}

export interface SessionState {
  patient: Patient;
  medications: Medication[];
  consented: boolean;
  medicationsVerified: boolean;
  confidenceScore: number | null;
  concerns: string[];
  reminders: Reminder[];
  scheduledCalls: ScheduledCall[];
  currentWorkflow: WorkflowStep;
  lexBotActive?: boolean;
  currentLlm?: "openai" | "gemini";
}

export type WorkflowStep =
  | "welcome"
  | "scheduling"
  | "verification"
  | "confidence"
  | "education"
  | "reminders"
  | "wrapup"
  | "completed";

export const WORKFLOW_STEPS: { key: WorkflowStep; label: string }[] = [
  { key: "welcome", label: "Welcome" },
  { key: "verification", label: "Verify Meds" },
  { key: "confidence", label: "Check-in" },
  { key: "education", label: "Education" },
  { key: "reminders", label: "Reminders" },
  { key: "wrapup", label: "Wrap Up" },
];

