"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  useLocalParticipant,
  useRemoteParticipants,
  useChat,
  useTrackTranscription,
  useTracks,
  useRoomContext,
} from "@livekit/components-react";
import { Track, RoomEvent, TranscriptionSegment } from "livekit-client";
import { Mic, MicOff, MessageSquare, Send, Volume2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isFinal: boolean;
}

export function ChatPanel() {
  const [inputMode, setInputMode] = useState<"voice" | "text">("voice");
  const [textInput, setTextInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const room = useRoomContext();
  const { localParticipant } = useLocalParticipant();
  const remoteParticipants = useRemoteParticipants();
  const { send: sendChat } = useChat();

  const agentParticipant = remoteParticipants.find(
    (p) => p.isAgent || p.identity.includes("agent")
  );

  const localTracks = useTracks([Track.Source.Microphone], {
    onlySubscribed: false,
  }).filter((t) => t.participant.identity === localParticipant?.identity);

  const agentTracks = useTracks([Track.Source.Microphone], {
    onlySubscribed: true,
  }).filter((t) => t.participant.identity === agentParticipant?.identity);

  const localTrack = localTracks[0];
  const agentTrack = agentTracks[0];

  const { segments: userSegments } = useTrackTranscription(localTrack);
  const { segments: agentSegments } = useTrackTranscription(agentTrack);

  const processSegments = useCallback(
    (segments: TranscriptionSegment[], role: "user" | "assistant") => {
      if (!segments || segments.length === 0) return;

      setMessages((prev) => {
        const newMessages = [...prev];

        segments.forEach((segment) => {
          const existingIndex = newMessages.findIndex(
            (m) => m.id === segment.id
          );
          if (existingIndex >= 0) {
            newMessages[existingIndex] = {
              ...newMessages[existingIndex],
              content: segment.text,
              isFinal: segment.final,
            };
          } else if (segment.text.trim()) {
            newMessages.push({
              id: segment.id,
              role,
              content: segment.text,
              timestamp: new Date(),
              isFinal: segment.final,
            });
          }
        });

        return newMessages;
      });
    },
    []
  );

  useEffect(() => {
    processSegments(userSegments, "user");
  }, [userSegments, processSegments]);

  useEffect(() => {
    processSegments(agentSegments, "assistant");
  }, [agentSegments, processSegments]);

  useEffect(() => {
    if (agentTrack?.publication?.track) {
      const track = agentTrack.publication.track;
      const checkSpeaking = () => {
        setIsAgentSpeaking(track.isMuted === false);
      };
      const interval = setInterval(checkSpeaking, 100);
      return () => clearInterval(interval);
    }
  }, [agentTrack]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendText = async () => {
    if (!textInput.trim() || !sendChat) return;

    const messageId = `user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "user",
        content: textInput,
        timestamp: new Date(),
        isFinal: true,
      },
    ]);

    await sendChat(textInput);
    setTextInput("");
  };

  const toggleMicrophone = async () => {
    if (!localParticipant) return;
    await localParticipant.setMicrophoneEnabled(
      !localParticipant.isMicrophoneEnabled
    );
  };

  const isMicEnabled = localParticipant?.isMicrophoneEnabled ?? false;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-title">
          <Volume2
            size={18}
            className={isAgentSpeaking ? "speaking" : ""}
          />
          <span>OneHealthLink Assistant</span>
        </div>
        <div className="mode-toggle">
          <button
            className={inputMode === "voice" ? "active" : ""}
            onClick={() => setInputMode("voice")}
          >
            <Mic size={16} />
            Voice
          </button>
          <button
            className={inputMode === "text" ? "active" : ""}
            onClick={() => setInputMode("text")}
          >
            <MessageSquare size={16} />
            Text
          </button>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <p>Conversation will appear here...</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${msg.role} ${msg.isFinal ? "final" : "interim"}`}
            >
              <div className="message-content">{msg.content}</div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {inputMode === "voice" ? (
          <button
            className={`mic-button ${isMicEnabled ? "active" : ""}`}
            onClick={toggleMicrophone}
          >
            {isMicEnabled ? <Mic size={24} /> : <MicOff size={24} />}
            <span>{isMicEnabled ? "Tap to mute" : "Tap to speak"}</span>
          </button>
        ) : (
          <div className="text-input-wrapper">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSendText()}
              placeholder="Type your message..."
            />
            <button onClick={handleSendText} disabled={!textInput.trim()}>
              <Send size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

