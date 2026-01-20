"use client";

import { WorkflowStep, WORKFLOW_STEPS } from "../types";
import { Check, Clock, Circle } from "lucide-react";
import { LlmIndicator } from "./LlmIndicator";

interface WorkflowProgressProps {
  currentStep: WorkflowStep;
  currentLlm?: "openai" | "gemini";
}

export function WorkflowProgress({ currentStep, currentLlm }: WorkflowProgressProps) {
  const currentIndex = WORKFLOW_STEPS.findIndex((s) => s.key === currentStep);
  const isScheduling = currentStep === "scheduling";

  return (
    <div className="workflow-progress">
      <h3 className="workflow-title">Session Progress</h3>
      <LlmIndicator provider={currentLlm} />
      {isScheduling && (
        <div className="scheduling-badge">
          <Clock size={14} />
          <span>Scheduling</span>
        </div>
      )}
      <div className="steps-container">
        {WORKFLOW_STEPS.map((step, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = step.key === currentStep;
          const isPending = index > currentIndex;

          return (
            <div
              key={step.key}
              className={`step ${isCompleted ? "completed" : ""} ${isCurrent ? "current" : ""} ${isPending ? "pending" : ""}`}
            >
              <div className="step-indicator">
                {isCompleted ? (
                  <Check size={14} strokeWidth={3} />
                ) : isCurrent ? (
                  <div className="pulse-dot" />
                ) : (
                  <Circle size={8} />
                )}
              </div>
              <span className="step-label">{step.label}</span>
              {index < WORKFLOW_STEPS.length - 1 && (
                <div className={`step-connector ${isCompleted ? "completed" : ""}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

