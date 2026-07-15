/*
==========================================================
VoxAgent AI
WebSocket Client
==========================================================
*/

(function () {
    "use strict";

    class VoxWebSocket {
        constructor() {
            this.socket = null;
            this.sessionId = null;
            this.connected = false;
            this.connecting = false;
            this.manuallyClosed = false;
            this.reconnectDelay = 3000;
            this.reconnectTimer = null;
            this.heartbeatInterval = null;

            this.onMessage = null;
            this.onOpen = null;
            this.onClose = null;
            this.onError = null;
            this.onReconnect = null;
        }

        connect(sessionId) {
            if (!sessionId) {
                throw new Error("WebSocket session id is required.");
            }

            if (
                this.socket &&
                (this.socket.readyState === WebSocket.OPEN ||
                    this.socket.readyState === WebSocket.CONNECTING) &&
                this.sessionId === sessionId
            ) {
                return;
            }

            this.sessionId = sessionId;
            this.manuallyClosed = false;
            this.connecting = true;
            this.clearReconnectTimer();

            const protocol = location.protocol === "https:" ? "wss" : "ws";
            const host = location.hostname || "127.0.0.1";
            const token = localStorage.getItem("voxagent-token") || "";
            const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
            const url = `${protocol}://${host}:8000/ws/${encodeURIComponent(sessionId)}${tokenParam}`;

            this.socket = new WebSocket(url);

            this.socket.onopen = () => {
                this.connected = true;
                this.connecting = false;
                this.startHeartbeat();

                if (this.onOpen) {
                    this.onOpen();
                }
            };

            this.socket.onmessage = (event) => {
                let data = event.data;

                try {
                    data = JSON.parse(event.data);
                } catch (err) {
                    // Plain-text server messages are valid during development.
                }

                if (data && typeof data === "object" && data.type === "pong") {
                    return;
                }

                if (this.onMessage) {
                    this.onMessage(data);
                }
            };

            this.socket.onerror = (event) => {
                if (this.onError) {
                    this.onError(event);
                }
            };

            this.socket.onclose = (event) => {
                const expectedClose = this.manuallyClosed;

                this.connected = false;
                this.connecting = false;
                this.stopHeartbeat();

                if (this.onClose) {
                    this.onClose(event, expectedClose);
                }

                if (!expectedClose) {
                    this.scheduleReconnect();
                }
            };
        }

        send(data) {
            if (!this.connected || !this.socket || this.socket.readyState !== WebSocket.OPEN) {
                return false;
            }

            const payload = typeof data === "string" ? data : JSON.stringify(data);
            this.socket.send(payload);
            return true;
        }

        startHeartbeat() {
            this.stopHeartbeat();

            this.heartbeatInterval = setInterval(() => {
                this.send({
                    type: "ping",
                    timestamp: Date.now(),
                });
            }, 30000);
        }

        stopHeartbeat() {
            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }
        }

        scheduleReconnect() {
            this.clearReconnectTimer();

            this.reconnectTimer = setTimeout(() => {
                if (!this.sessionId || this.manuallyClosed) {
                    return;
                }

                if (this.onReconnect) {
                    this.onReconnect();
                }

                this.connect(this.sessionId);
            }, this.reconnectDelay);
        }

        clearReconnectTimer() {
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        }

        disconnect() {
            this.manuallyClosed = true;
            this.connected = false;
            this.connecting = false;
            this.clearReconnectTimer();
            this.stopHeartbeat();

            if (this.socket) {
                this.socket.close(1000, "Client disconnected");
                this.socket = null;
            }
        }
    }

    window.VoxWebSocket = new VoxWebSocket();
})();
