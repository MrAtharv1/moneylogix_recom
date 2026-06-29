/**
 * useWebSocket.ts — Connects to the FastAPI health monitor websocket.
 */
import { useState, useEffect, useRef } from 'react';
import type { HealthEvent } from '../types/strategy';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useHealthMonitor(strategyId: string | null) {
  const [latestEvent, setLatestEvent] = useState<HealthEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [healthHistory, setHealthHistory] = useState<HealthEvent[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!strategyId) return;

    setConnectionStatus('connecting');
    // Using standard WebSocket API
    const socket = new WebSocket(`ws://localhost:8000/ws/health/${strategyId}`);
    ws.current = socket;

    socket.onopen = () => {
      setConnectionStatus('connected');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // SAFETY GUARD: If the backend sends an error, stop processing!
        if (data.error) {
          console.error("WebSocket Backend Error:", data.error);
          setConnectionStatus('error');
          socket.close(); // Close immediately to prevent loops
          return;
        }

        // It's a valid HealthEvent. Update state safely.
        setLatestEvent(data);
        setHealthHistory((prev) => [data, ...prev]);
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    socket.onclose = () => {
      // Only set to disconnected if we didn't already flag an error
      setConnectionStatus((prev) => (prev === 'error' ? 'error' : 'disconnected'));
    };

    socket.onerror = () => {
      setConnectionStatus('error');
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    };
  }, [strategyId]);

  return { latestEvent, connectionStatus, healthHistory };
}