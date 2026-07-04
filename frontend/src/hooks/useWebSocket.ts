import { useState, useEffect, useRef, useCallback } from 'react';
import type { HealthEvent } from '../types/strategy';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export function useHealthMonitor(strategyId: string | null) {
  const [latestEvent, setLatestEvent] = useState<HealthEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [healthHistory, setHealthHistory] = useState<HealthEvent[]>([]);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectDelay = 30000; // Cap delay at 30 seconds

  const connect = useCallback(() => {
    if (!strategyId) return;

    setConnectionStatus('connecting');
    const socket = new WebSocket(`${WS_BASE_URL}/ws/health/${strategyId}`);
    ws.current = socket;

    socket.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttempts.current = 0; // Reset attempts on successful connection
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.error('WebSocket error:', data.error);
          setConnectionStatus('error');
          socket.close();
          return;
        }
        setLatestEvent(data);
        setHealthHistory(prev => [data, ...prev]);
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    socket.onclose = (event) => {
      // Don't reconnect if it was closed cleanly by the component unmounting
      if (event.code === 1000) {
        setConnectionStatus('disconnected');
        return;
      }
      
      setConnectionStatus('error');
      
      // Exponential backoff: 1s, 2s, 4s, 8s... up to maxReconnectDelay
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), maxReconnectDelay);
      
      reconnectTimeout.current = setTimeout(() => {
        reconnectAttempts.current += 1;
        connect();
      }, delay);
    };

    socket.onerror = () => {
      // The onclose handler will naturally fire after onerror and handle the reconnection
      setConnectionStatus('error');
    };
  }, [strategyId]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
        // Code 1000 indicates a normal, expected closure (unmount)
        ws.current.close(1000, "Component unmounted"); 
      }
    };
  }, [connect]);

  return { latestEvent, connectionStatus, healthHistory };
}