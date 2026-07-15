/*
==========================================================
VoxAgent AI
Live Voice UI Controller
==========================================================
*/

(function () {
    "use strict";

    if (document.body.getAttribute("data-page") !== "live-calls") {
        return;
    }

    if (window.VoxAPI && !window.VoxAPI.isAuthenticated()) {
        window.location.href = "login.html";
        return;
    }

    class VoiceUI {
        constructor() {
            this.sessionId = null;
            this.active = false;
            this.recording = false;
            this.connected = false;
            this.thinking = false;
            this.currentLanguage = "en";
            this.startTime = null;
            this.timerInterval = null;

            this.tts = typeof VoxTTS !== "undefined" ? new VoxTTS() : null;

            this.el = {
                statusDot: document.getElementById("callStatusDot"),
                statusText: document.getElementById("callStatusText"),
                timer: document.getElementById("callTimer"),
                transcript: document.getElementById("callTranscript"),
                emptyState: document.getElementById("callEmptyState"),
                startBtn: document.getElementById("startCallBtn"),
                endBtn: document.getElementById("endCallBtn"),
                micBtn: document.getElementById("micButton"),
                messageInput: document.getElementById("messageInput"),
                sendBtn: document.getElementById("sendMessageBtn"),
                language: document.getElementById("voiceLanguage"),
                intent: document.getElementById("voiceIntent"),
                sentiment: document.getElementById("voiceSentiment"),
                latency: document.getElementById("voiceLatency"),
            };
        }

        init() {
            if (!this.hasRequiredMarkup()) {
                console.error("Live Calls page is missing required voice UI markup.");
                return;
            }

            this.el.startBtn.addEventListener("click", () => this.startCall());
            this.el.endBtn.addEventListener("click", () => this.endCall());
            this.el.micBtn.addEventListener("click", () => this.toggleRecording());
            this.el.sendBtn.addEventListener("click", () => this.sendTypedMessage());
            this.el.messageInput.addEventListener("keydown", (event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    this.sendTypedMessage();
                }
            });

            this.resetUi();
        }

        hasRequiredMarkup() {
            return Object.values(this.el).every(Boolean);
        }

        startCall() {
            this.sessionId = crypto.randomUUID();
            this.active = true;
            this.connected = false;
            this.currentLanguage = "en";

            this.clearTranscript();
            this.resetMetadata();
            this.startTimer();
            this.bindWebSocket();

            this.el.startBtn.classList.add("hidden");
            this.el.endBtn.classList.remove("hidden");
            this.el.micBtn.classList.remove("hidden");
            this.el.messageInput.classList.remove("hidden");
            this.el.sendBtn.classList.remove("hidden");
            this.el.messageInput.disabled = false;
            this.el.sendBtn.disabled = false;
            this.el.micBtn.disabled = true;

            this.setStatus("Connecting", true);
            VoxWebSocket.connect(this.sessionId);
        }

        bindWebSocket() {
            VoxWebSocket.onOpen = () => {
                this.connected = true;
                this.el.micBtn.disabled = false;
                this.setStatus("Connected", true);
                this.addSystemTurn("Connected. Enable the microphone and speak.");
            };

            VoxWebSocket.onClose = (event, expectedClose) => {
                this.connected = false;
                this.hideThinking();
                this.el.micBtn.disabled = true;

                if (expectedClose || !this.active) {
                    return;
                }

                this.setStatus("Reconnecting", true);
                this.addSystemTurn("Connection lost. Reconnecting...");
            };

            VoxWebSocket.onReconnect = () => {
                this.setStatus("Reconnecting", true);
            };

            VoxWebSocket.onError = () => {
                this.connected = false;
                this.setStatus("Connection error", false);
                this.addSystemTurn("Could not reach the backend WebSocket.");
            };

            VoxWebSocket.onMessage = (message) => this.handleSocketMessage(message);
        }

        handleSocketMessage(message) {
            this.hideThinking();

            if (!this.active) {
                return;
            }

            if (typeof message === "string") {
                this.addAssistantTurn(message);
                this.speak(message);
                return;
            }

            if (!message || typeof message !== "object") {
                return;
            }

            if (message.type === "error") {
                this.setStatus("Error", false);
                this.addSystemTurn(message.message || "The AI returned an error.");
                return;
            }

            if (message.language || message.detected_language) {
                this.currentLanguage = message.language || message.detected_language;
            }

            const responseText = message.response || message.reply || message.text;

            if (!responseText) {
                return;
            }

            this.updateMetadata(message);
            this.addAssistantTurn(responseText, message);
            this.speak(responseText);
            this.setStatus("Connected", true);
        }

        async toggleRecording() {
            if (!this.active || !this.connected) {
                this.addSystemTurn("Start a connected call before speaking.");
                return;
            }

            if (!this.recording) {
                await this.startRecording();
                return;
            }

            await this.stopRecording();
        }

        async startRecording() {
            try {
                this.recording = true;
                this.setMicState(true);
                this.setStatus("Listening", true);
                await VoxAudio.start();
            } catch (err) {
                console.error(err);
                this.recording = false;
                this.setMicState(false);
                this.setStatus("Microphone denied", true);
                this.addSystemTurn(err.message || "Could not access the microphone.");
            }
        }

        async stopRecording() {
            this.recording = false;
            this.setMicState(false);
            this.setStatus("Transcribing", true);

            let blob = null;

            try {
                blob = await VoxAudio.stop();
            } catch (err) {
                console.error(err);
            }

            if (!blob || blob.size === 0) {
                this.setStatus("Connected", true);
                this.addSystemTurn("No audio captured.");
                return;
            }

            await this.transcribe(blob);
        }

        async transcribe(blob) {
            const form = new FormData();
            form.append("audio", blob, "voice.webm");

            try {
                const response = await fetch(this.apiUrl("/api/voice/transcribe"), {
                    method: "POST",
                    body: form,
                });

                const payload = await response.json();

                if (!response.ok) {
                    throw new Error(payload.detail || "Speech recognition failed.");
                }

                const transcription = String(payload.transcription || "").trim();

                if (!transcription) {
                    this.setStatus("Connected", true);
                    this.addSystemTurn("No speech was recognized.");
                    return;
                }

                if (payload.language) {
                    this.currentLanguage = payload.language;
                    this.el.language.textContent = payload.language.toUpperCase();
                }

                this.addUserTurn(transcription);
                this.askAI(transcription);
            } catch (err) {
                console.error(err);
                this.setStatus("Speech error", true);
                this.addSystemTurn(err.message || "Speech recognition failed.");
            }
        }

        askAI(text) {
            if (!this.connected) {
                this.addSystemTurn("WebSocket is not connected.");
                return;
            }

            this.showThinking();
            this.setStatus("Thinking", true);

            const sent = VoxWebSocket.send({
                type: "message",
                text,
            });

            if (!sent) {
                this.hideThinking();
                this.setStatus("Connection error", true);
                this.addSystemTurn("Could not send the message.");
            }
        }

        sendTypedMessage() {
            const text = this.el.messageInput.value.trim();

            if (!text || !this.active) {
                return;
            }

            this.el.messageInput.value = "";
            this.addUserTurn(text);
            this.askAI(text);
        }

        endCall() {
            this.active = false;
            this.connected = false;
            this.hideThinking();
            this.stopTimer();

            if (this.recording) {
                VoxAudio.cancel();
                this.recording = false;
            }

            VoxAudio.release();
            VoxWebSocket.disconnect();

            if (this.tts) {
                this.tts.stop();
            }

            this.addSystemTurn("Call ended.");
            this.resetUi(false);
        }

        resetUi(clearTranscript = true) {
            this.stopTimer();
            this.setStatus("No active call", false);
            this.setMicState(false);
            this.resetMetadata();

            this.el.timer.textContent = "00:00";
            this.el.startBtn.classList.remove("hidden");
            this.el.startBtn.disabled = false;
            this.el.endBtn.classList.add("hidden");
            this.el.endBtn.disabled = false;
            this.el.micBtn.classList.add("hidden");
            this.el.micBtn.disabled = true;
            this.el.messageInput.classList.add("hidden");
            this.el.messageInput.value = "";
            this.el.messageInput.disabled = true;
            this.el.sendBtn.classList.add("hidden");
            this.el.sendBtn.disabled = true;

            if (clearTranscript) {
                this.clearTranscript();
            }
        }

        startTimer() {
            this.stopTimer();
            this.startTime = Date.now();
            this.el.timer.textContent = "00:00";

            this.timerInterval = setInterval(() => {
                const seconds = Math.floor((Date.now() - this.startTime) / 1000);
                const minutes = Math.floor(seconds / 60);
                const remainingSeconds = seconds % 60;

                this.el.timer.textContent = `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
            }, 1000);
        }

        stopTimer() {
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
                this.timerInterval = null;
            }
        }

        setStatus(text, live) {
            this.el.statusText.textContent = text;
            this.el.statusDot.style.display = live ? "" : "none";
        }

        setMicState(recording) {
            this.el.micBtn.classList.toggle("recording", recording);
            this.el.micBtn.innerHTML = recording
                ? '<i class="fa-solid fa-stop"></i> Stop'
                : '<i class="fa-solid fa-microphone"></i> Speak';
        }

        showThinking() {
            if (this.thinking) {
                return;
            }

            this.thinking = true;
            this.appendTurn("ai", "Thinking...", "processing", "thinkingTurn");
        }

        hideThinking() {
            this.thinking = false;

            const turn = document.getElementById("thinkingTurn");
            if (turn) {
                turn.remove();
            }
        }

        addUserTurn(text) {
            this.appendTurn("user", text, this.currentTimeLabel());
        }

        addAssistantTurn(text, metadata = {}) {
            const meta = [
                (metadata.language || metadata.detected_language || this.currentLanguage || "en").toUpperCase(),
                metadata.intent || "general",
                metadata.sentiment || "neutral",
                `${metadata.latency_ms || 0}ms`,
            ].join(" | ");

            this.appendTurn("ai", text, meta);
        }

        addSystemTurn(text) {
            this.appendTurn("system", text, this.currentTimeLabel());
        }

        appendTurn(role, text, metaText = "", id = "") {
            if (this.el.emptyState) {
                this.el.emptyState.hidden = true;
            }

            const turn = document.createElement("div");
            turn.className = `turn turn-${role}`;

            if (id) {
                turn.id = id;
            }

            const avatar = document.createElement("div");
            avatar.className = "turn-avatar";
            avatar.innerHTML = role === "user"
                ? '<i class="fa-solid fa-user"></i>'
                : role === "system"
                    ? '<i class="fa-solid fa-circle-info"></i>'
                    : '<i class="fa-solid fa-robot"></i>';

            const bubble = document.createElement("div");
            bubble.className = "turn-bubble";

            const body = document.createElement("p");
            body.className = "turn-text";
            body.textContent = text;
            bubble.appendChild(body);

            if (metaText) {
                const meta = document.createElement("span");
                meta.className = "turn-meta";
                meta.textContent = metaText;
                bubble.appendChild(meta);
            }

            turn.appendChild(avatar);
            turn.appendChild(bubble);
            this.el.transcript.appendChild(turn);
            this.scrollTranscript();
        }

        clearTranscript() {
            this.el.transcript.innerHTML = "";

            if (this.el.emptyState) {
                this.el.emptyState.hidden = false;
                this.el.transcript.appendChild(this.el.emptyState);
            }
        }

        updateMetadata(data) {
            const language = data.language || data.detected_language || this.currentLanguage || "en";

            this.el.language.textContent = language.toUpperCase();
            this.el.intent.textContent = data.intent || "general";
            this.el.sentiment.textContent = data.sentiment || "neutral";
            this.el.latency.textContent = `${data.latency_ms || 0} ms`;
        }

        resetMetadata() {
            this.el.language.textContent = "-";
            this.el.intent.textContent = "-";
            this.el.sentiment.textContent = "-";
            this.el.latency.textContent = "-";
        }

        speak(text) {
            if (this.tts) {
                this.tts.speak(text, this.currentLanguage);
            }
        }

        scrollTranscript() {
            this.el.transcript.scrollTop = this.el.transcript.scrollHeight;
        }

        currentTimeLabel() {
            return new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
        }

        apiUrl(path) {
            const host = location.hostname || "127.0.0.1";
            return `http://${host}:8000${path}`;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        window.VoiceUI = new VoiceUI();
        window.VoiceUI.init();
    });
})();
