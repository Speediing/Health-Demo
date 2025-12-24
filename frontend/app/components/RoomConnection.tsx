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
import { Loader2, PhoneCall, PhoneOff } from "lucide-react";

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
      const roomName = `onehealth-${Date.now()}`;
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
      <div className="connection-screen">
        <div className="connection-card">
          <div className="connection-header">
            <div className="logo">
              <span className="logo-icon">+</span>
              <span className="logo-text">OneHealthLink</span>
            </div>
            <h1>Medication Onboarding</h1>
            <p>
              Connect to speak with your healthcare assistant about your new
              medications.
            </p>
          </div>
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
        </div>
        <PatientDashboard state={sessionState} />
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

