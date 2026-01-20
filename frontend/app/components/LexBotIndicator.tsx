"use client";

import { Bot, Phone } from "lucide-react";

interface LexBotIndicatorProps {
  active: boolean;
}

export function LexBotIndicator({ active }: LexBotIndicatorProps) {
  if (!active) {
    return null;
  }

  return (
    <div className="lex-bot-indicator">
      <div className="lex-bot-icon">
        <Bot size={16} />
      </div>
      <div className="lex-bot-content">
        <div className="lex-bot-header">
          <span className="lex-bot-label">Amazon Lex</span>
          <span className="lex-bot-badge">Active</span>
        </div>
        <div className="lex-bot-status">
          <Phone size={12} />
          <span>Fetching call center hours...</span>
        </div>
      </div>
      <div className="lex-bot-pulse" />
    </div>
  );
}
