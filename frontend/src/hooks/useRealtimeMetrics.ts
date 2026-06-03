import { useEffect, useRef, useState } from "react";

import { getSnapshot, WS_BASE } from "../services/api";
import type { Snapshot } from "../types";

export function useRealtimeMetrics(token: string | null) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [status, setStatus] = useState<"connecting" | "live" | "offline">("connecting");
  const timer = useRef<number | undefined>();

  useEffect(() => {
    if (!token) {
      setSnapshot(null);
      setStatus("offline");
      return;
    }

    let socket: WebSocket | null = null;
    let closed = false;

    getSnapshot(token).then(setSnapshot).catch(() => setStatus("offline"));

    const connect = () => {
      setStatus("connecting");
      socket = new WebSocket(`${WS_BASE}/metrics?token=${encodeURIComponent(token)}`);
      socket.onopen = () => setStatus("live");
      socket.onmessage = (event) => {
        setSnapshot(JSON.parse(event.data));
        setStatus("live");
      };
      socket.onerror = () => setStatus("offline");
      socket.onclose = () => {
        if (!closed) {
          setStatus("offline");
          timer.current = window.setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      closed = true;
      if (timer.current) window.clearTimeout(timer.current);
      socket?.close();
    };
  }, [token]);

  return { snapshot, status };
}

