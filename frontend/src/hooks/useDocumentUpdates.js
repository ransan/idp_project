import { useEffect, useRef } from 'react';

/**
 * WebSocket hook that subscribes to real-time document updates.
 * Calls `onMessage(event)` when a document status changes.
 * Auto-reconnects on disconnect.
 */
export function useDocumentUpdates(onMessage) {
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    let ws;
    let reconnectTimer;
    let unmounted = false;

    const connect = () => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      ws = new WebSocket(`${proto}://${host}/api/v1/ws?token=${token}`);

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          cbRef.current(data);
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        if (!unmounted) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      unmounted = true;
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, []);
}
