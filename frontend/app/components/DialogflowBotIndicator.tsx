"use client";

import { Bot, MapPin } from "lucide-react";

interface DialogflowBotIndicatorProps {
  active: boolean;
}

export function DialogflowBotIndicator({ active }: DialogflowBotIndicatorProps) {
  if (!active) {
    return null;
  }

  return (
    <div className="dialogflow-bot-indicator">
      <div className="dialogflow-bot-icon">
        <Bot size={16} />
      </div>
      <div className="dialogflow-bot-content">
        <div className="dialogflow-bot-header">
          <span className="dialogflow-bot-label">Google Dialogflow</span>
          <span className="dialogflow-bot-badge">Active</span>
        </div>
        <div className="dialogflow-bot-status">
          <MapPin size={12} />
          <span>Finding closest location...</span>
        </div>
      </div>
      <div className="dialogflow-bot-pulse" />
    </div>
  );
}
