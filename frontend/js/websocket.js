/*
==========================================================
VoxAgent AI
WebSocket Client
==========================================================

Responsibilities

✓ Connect to backend
✓ Auto reconnect
✓ Send messages
✓ Receive JSON
✓ Heartbeat
✓ Disconnect

No UI logic belongs here.
==========================================================
*/

(function () {

    "use strict";

    class VoxWebSocket {

        constructor() {

            this.socket = null;

            this.sessionId = null;

            this.connected = false;

            this.reconnectDelay = 3000;

            this.onMessage = null;

            this.onOpen = null;

            this.onClose = null;

            this.onError = null;

            this.heartbeatInterval = null;
        }

        connect(sessionId) {

            this.sessionId = sessionId;

            const url = `ws://${location.hostname}:8000/ws/${sessionId}`;

            this.socket = new WebSocket(url);

            this.socket.onopen = () => {

                console.log("✅ WebSocket Connected");

                this.connected = true;

                this.startHeartbeat();

                if (this.onOpen)
                    this.onOpen();

            };

            this.socket.onmessage = (event) => {

                let data = event.data;

                try {

                    data = JSON.parse(event.data);

                }
                catch (e) { }

                if (this.onMessage)
                    this.onMessage(data);

            };

            this.socket.onerror = (event) => {

                console.error(event);

                if (this.onError)
                    this.onError(event);

            };

            this.socket.onclose = () => {

                console.log("❌ WebSocket Closed");

                this.connected = false;

                this.stopHeartbeat();

                if (this.onClose)
                    this.onClose();

                setTimeout(() => {

                    console.log("Reconnecting...");

                    this.connect(this.sessionId);

                }, this.reconnectDelay);

            };

        }

        send(data) {

            if (!this.connected)
                return;

            if (typeof data !== "string")
                data = JSON.stringify(data);

            this.socket.send(data);

        }

        startHeartbeat() {

            this.stopHeartbeat();

            this.heartbeatInterval = setInterval(() => {

                if (this.connected) {

                    this.send({

                        type: "ping",

                        timestamp: Date.now()

                    });

                }

            }, 30000);

        }

        stopHeartbeat() {

            if (this.heartbeatInterval) {

                clearInterval(this.heartbeatInterval);

                this.heartbeatInterval = null;

            }

        }

        disconnect() {

            this.stopHeartbeat();

            if (this.socket)
                this.socket.close();

        }

    }

    window.VoxWebSocket = new VoxWebSocket();

})();