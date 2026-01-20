"use client";

import { Cpu, Sparkles } from "lucide-react";

interface LlmIndicatorProps {
  provider: "openai" | "gemini" | undefined;
}

export function LlmIndicator({ provider }: LlmIndicatorProps) {
  if (!provider) {
    return null;
  }

  const isOpenAI = provider === "openai";

  return (
    <div className={`llm-indicator ${provider}`}>
      <div className="llm-icon">
        {isOpenAI ? <Cpu size={14} /> : <Sparkles size={14} />}
      </div>
      <div className="llm-content">
        <span className="llm-label">Powered by</span>
        <span className="llm-name">{isOpenAI ? "OpenAI GPT-4o" : "Google Gemini"}</span>
      </div>
      <div className="llm-pulse" />
    </div>
  );
}
