"use client";

import { useEffect, useState, useCallback } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useParticipants,
  useRoomContext,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { RoomEvent } from "livekit-client";
import { SessionState } from "../types";
import { ChatPanel } from "./ChatPanel";
import { PatientDashboard } from "./PatientDashboard";
import { Loader2, PhoneCall, PhoneOff, Mic, LayoutDashboard, ListChecks, Cpu, Bot, ArrowRightLeft, Phone, UserCheck } from "lucide-react";

interface ConnectionState {
  token: string;
  url: string;
}

function RoomContent({
  onStateChange,
}: {
  onStateChange: (state: SessionState | null) => void;
}) {
  const room = useRoomContext();
  const participants = useParticipants();

  useEffect(() => {
    if (!room) return;

    const handleAttributesChanged = () => {
      const agentParticipant = participants.find(
        (p) => p.isAgent || p.identity.includes("agent")
      );
      if (agentParticipant) {
        const stateStr = agentParticipant.attributes?.state;
        if (stateStr) {
          try {
            const state = JSON.parse(stateStr) as SessionState;
            onStateChange(state);
          } catch (e) {
            console.error("Failed to parse state:", e);
          }
        }
      }
    };

    room.on(RoomEvent.ParticipantAttributesChanged, handleAttributesChanged);
    handleAttributesChanged();

    return () => {
      room.off(RoomEvent.ParticipantAttributesChanged, handleAttributesChanged);
    };
  }, [room, participants, onStateChange]);

  return (
    <>
      <RoomAudioRenderer />
      <ChatPanel />
    </>
  );
}

export function RoomConnection() {
  const [connection, setConnection] = useState<ConnectionState | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      const roomName = `health-${Date.now()}`;
      const res = await fetch(
        `/api/token?room=${roomName}&username=Patient`
      );
      if (!res.ok) throw new Error("Failed to get token");

      const data = await res.json();
      setConnection({ token: data.token, url: data.url });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connection failed");
      setIsConnecting(false);
    }
  };

  const disconnect = () => {
    setConnection(null);
    setSessionState(null);
    setIsConnected(false);
  };

  const handleStateChange = useCallback((state: SessionState | null) => {
    setSessionState(state);
  }, []);

  if (!connection) {
    return (
      <div className="landing-page">
        <div className="landing-header">
          <div className="logo">
            <span className="logo-icon">U</span>
            <span className="logo-text">UnitedHealthcare</span>
          </div>
          <span className="demo-badge">AI Demo</span>
        </div>

        <div className="landing-hero">
          <h1>AI-Powered Medication Onboarding</h1>
          <p className="hero-subtitle">
            Experience an intelligent voice assistant that guides patients through
            medication onboarding while providing real-time insights to care teams.
          </p>
        </div>

        <div className="landing-content">
          <div className="demo-overview">
            <h2>What This Demo Shows</h2>
            <p>
              This demonstration showcases how AI can transform the medication
              onboarding experience. A voice-enabled assistant guides patients
              through a structured conversation while a real-time dashboard
              displays extracted insights for care teams.
            </p>

            <div className="workflow-preview">
              <h3>Conversation Flow</h3>
              <div className="workflow-steps-preview">
                <div className="preview-step">
                  <span className="step-number">1</span>
                  <div>
                    <strong>Welcome & Consent</strong>
                    <p>Greet patient, verify identity, obtain verbal consent</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">2</span>
                  <div>
                    <strong>Medication Verification</strong>
                    <p>Review each medication, confirm understanding of dosage and timing</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">3</span>
                  <div>
                    <strong>Confidence Check-in</strong>
                    <p>Assess patient comfort level, identify concerns or questions</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">4</span>
                  <div>
                    <strong>Education</strong>
                    <p>Provide personalized guidance on side effects and interactions</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">5</span>
                  <div>
                    <strong>Reminders Setup</strong>
                    <p>Configure text reminders, calendar events, auto-refill preferences</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">6</span>
                  <div>
                    <strong>Wrap Up</strong>
                    <p>Schedule follow-up calls, pharmacist consultations if needed</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="features-section">
            <h2>Key Capabilities</h2>
            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon voice">
                  <Mic size={20} />
                </div>
                <h4>Voice-First Experience</h4>
                <p>Natural conversation using speech-to-text and text-to-speech for accessible patient interactions</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon realtime">
                  <LayoutDashboard size={20} />
                </div>
                <h4>Real-Time Dashboard</h4>
                <p>Live extraction of patient data, concerns, and confidence scores as the conversation progresses</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon workflow">
                  <ListChecks size={20} />
                </div>
                <h4>Structured Workflow</h4>
                <p>Guided conversation flow ensures consistent, compliant medication onboarding sessions</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon multi-llm">
                  <Cpu size={20} />
                </div>
                <h4>Multi-LLM Support</h4>
                <p>Seamlessly switches between OpenAI and Google Gemini based on task requirements</p>
              </div>
            </div>

            <div className="multi-agent-section">
              <h3>Multi-Agent Architecture</h3>
              <p>This demo showcases intelligent agent handoffs between different AI systems:</p>
              <div className="agent-flow">
                <div className="agent-card primary">
                  <Bot size={18} />
                  <span>LiveKit Voice Agent</span>
                  <p>Primary conversation handler</p>
                </div>
                <div className="agent-arrow">
                  <ArrowRightLeft size={16} />
                </div>
                <div className="agent-card lex">
                  <Bot size={18} />
                  <span>Amazon Lex</span>
                  <p>Pharmacy call scheduling</p>
                </div>
              </div>
              <p className="agent-note">
                When the patient needs to schedule a pharmacist consultation, the system
                seamlessly transfers the call to Amazon Lex for appointment booking, then
                returns control to the main agent.
              </p>
            </div>

            <div className="telephony-section">
              <h3>Telephony & Escalation Support</h3>
              <div className="telephony-features">
                <div className="telephony-card">
                  <div className="telephony-icon">
                    <Phone size={18} />
                  </div>
                  <div className="telephony-content">
                    <strong>PSTN Telephony Integration</strong>
                    <p>Supports inbound and outbound calls over traditional phone lines, making the AI assistant accessible to patients without internet access.</p>
                  </div>
                </div>
                <div className="telephony-card">
                  <div className="telephony-icon supervisor">
                    <UserCheck size={18} />
                  </div>
                  <div className="telephony-content">
                    <strong>Warm Handoff to Supervisor</strong>
                    <p>Say "I'd like to speak to a supervisor" at any time. The system performs a warm transfer, briefing the human agent on the conversation context before connecting.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="landing-cta">
          {error && <div className="error-message">{error}</div>}
          <button
            className="connect-button"
            onClick={connect}
            disabled={isConnecting}
          >
            {isConnecting ? (
              <>
                <Loader2 className="spinner" size={20} />
                Connecting...
              </>
            ) : (
              <>
                <PhoneCall size={20} />
                Start Demo Session
              </>
            )}
          </button>
          <p className="cta-note">
            Click to begin an interactive voice session with the AI assistant
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="room-container">
      <LiveKitRoom
        token={connection.token}
        serverUrl={connection.url}
        connect={true}
        audio={true}
        video={false}
        onConnected={() => {
          setIsConnecting(false);
          setIsConnected(true);
        }}
        onDisconnected={() => {
          setIsConnected(false);
        }}
        onError={(e) => {
          setError(e.message);
          setIsConnecting(false);
        }}
      >
        <div className="session-layout">
          <div className="chat-section">
            <RoomContent onStateChange={handleStateChange} />
            <button className="disconnect-button" onClick={disconnect}>
              <PhoneOff size={16} />
              End Session
            </button>
          </div>
          <div className="dashboard-section">
            <PatientDashboard state={sessionState} />
          </div>
        </div>
      </LiveKitRoom>
    </div>
  );
}

