import { AccessToken } from "livekit-server-sdk";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const room = searchParams.get("room") || "onehealth-demo";
  const username = searchParams.get("username") || "Patient";
  const supervisorPhone = searchParams.get("supervisorPhone") || "";

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json(
      { error: "Server misconfigured" },
      { status: 500 }
    );
  }

  // Build room metadata with configurable settings
  const roomMetadata = JSON.stringify({
    supervisorPhone: supervisorPhone,
  });

  const at = new AccessToken(apiKey, apiSecret, {
    identity: username,
    ttl: "1h",
  });

  at.addGrant({
    room,
    roomJoin: true,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true,
    roomCreate: true,
  });

  // Set room metadata in the token
  at.metadata = roomMetadata;

  const token = await at.toJwt();

  return NextResponse.json({
    token,
    url: process.env.LIVEKIT_URL,
  });
}

