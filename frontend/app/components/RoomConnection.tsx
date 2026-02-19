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
import { CalendarDashboard } from "./CalendarDashboard";
import { Loader2, PhoneCall, PhoneOff, Mic, Calendar, Plane, Bot } from "lucide-react";

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
      const roomName = `calendar-${Date.now()}`;
      const params = new URLSearchParams({
        room: roomName,
        username: "User",
      });
      const res = await fetch(`/api/token?${params}`);
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
            <span className="logo-icon">
              <Calendar size={22} />
            </span>
            <span className="logo-text">Calendar Assistant</span>
          </div>
          <span className="demo-badge">Voice AI Demo</span>
        </div>

        <div className="landing-hero">
          <h1>Voice-Powered Calendar & Travel Assistant</h1>
          <p className="hero-subtitle">
            Talk to your AI assistant to manage your calendar, book travel,
            and automatically reschedule conflicting meetings.
          </p>
        </div>

        <div className="landing-content">
          <div className="demo-overview">
            <h2>How It Works</h2>
            <p>
              Simply tell the assistant what you need. It can look up your
              calendar, find flights, book travel, and move meetings that
              conflict with your plans — all through natural conversation.
            </p>

            <div className="workflow-preview">
              <h3>Example Flow</h3>
              <div className="workflow-steps-preview">
                <div className="preview-step">
                  <span className="step-number">1</span>
                  <div>
                    <strong>Ask for Help</strong>
                    <p>Tell the assistant you want to book travel for next week</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">2</span>
                  <div>
                    <strong>Flight Search</strong>
                    <p>The assistant finds available flights and suggests the best options</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">3</span>
                  <div>
                    <strong>Calendar Check</strong>
                    <p>It checks your calendar for conflicts during travel times</p>
                  </div>
                </div>
                <div className="preview-step">
                  <span className="step-number">4</span>
                  <div>
                    <strong>Reschedule & Book</strong>
                    <p>Moves conflicting meetings, notifies attendees, and books your flight</p>
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
                <h4>Voice-First</h4>
                <p>Natural conversation for hands-free calendar and travel management</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon realtime">
                  <Calendar size={20} />
                </div>
                <h4>Calendar Management</h4>
                <p>View, move, and reschedule meetings with automatic attendee notifications</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon workflow">
                  <Plane size={20} />
                </div>
                <h4>Travel Booking</h4>
                <p>Search flights, compare options, and book travel all through voice</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon multi-llm">
                  <Bot size={20} />
                </div>
                <h4>Smart Conflict Resolution</h4>
                <p>Automatically identifies and resolves scheduling conflicts</p>
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
                Start Session
              </>
            )}
          </button>
          <p className="cta-note">
            Click to begin a voice session with your calendar assistant
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
            <CalendarDashboard state={sessionState} />
          </div>
        </div>
      </LiveKitRoom>
    </div>
  );
}
