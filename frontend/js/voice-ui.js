/*
==========================================================
VoxAgent AI
Voice UI Controller
==========================================================

Responsibilities

✓ Handle microphone button
✓ Connect WebSocket
✓ Display connection status
✓ Display AI messages
✓ Display user messages
✓ Update conversation panel

No AI logic.
No MediaRecorder logic.
No WebSocket implementation.

==========================================================
*/

(function () {

    "use strict";

    class VoiceUI {

        constructor() {

            this.sessionId = crypto.randomUUID();

            this.micButton = document.getElementById("micButton");

            this.statusBadge = document.getElementById("voiceStatus");

            this.chatContainer = document.getElementById("voiceConversation");

            this.recording = false;

        }

        init() {

            this.connectWebSocket();

            if (this.micButton) {

                this.micButton.addEventListener(

                    "click",

                    () => this.toggleRecording()

                );

            }

        }

        connectWebSocket() {

            VoxWebSocket.connect(this.sessionId);

            VoxWebSocket.onOpen = () => {

                this.setStatus("Connected", "#22c55e");

            };

            VoxWebSocket.onClose = () => {

                this.setStatus("Disconnected", "#ef4444");

            };

            VoxWebSocket.onError = () => {

                this.setStatus("Error", "#f59e0b");

            };

            VoxWebSocket.onMessage = (message) => {

                if (message.response) {
                    this.addMessage("assistant", message.response);
                }

                if (message.language) {
                    // Update language badge
                }

                if (message.sentiment) {
                    // Update sentiment indicator
                }

                if (message.intent) {
                    // Optional debug/analytics
                }
            };
        }

        async toggleRecording() {

            if (!this.recording) {

                this.recording = true;

                this.setMicState(true);

                this.addMessage(

                    "system",

                    "🎤 Listening..."

                );

                await VoxAudio.start();

                return;

            }

            this.recording = false;

            this.setMicState(false);

            const blob = await VoxAudio.stop();

            if (!blob)
                return;

            this.addMessage(

                "system",

                "Uploading audio..."

            );

            const form = new FormData();

            form.append(

                "audio",

                blob,

                "voice.webm"

            );

            try {

                const response = await fetch(

                    "http://localhost:8000/api/voice/transcribe",

                    {

                        method: "POST",

                        body: form

                    }

                );

                const json = await response.json();

                console.log(json);

                if (json.transcription) {

                    this.addMessage(

                        "user",

                        json.transcription

                    );

                    VoxWebSocket.send({

                        type: "message",

                        text: json.transcription

                    });

                }

            }

            catch (err) {

                console.error(err);

                this.addMessage(

                    "system",

                    "Audio upload failed."

                );

            }

        }

        addMessage(role, text) {

            if (!this.chatContainer)
                return;

            const div = document.createElement("div");

            div.className = `voice-message ${role}`;

            div.innerHTML = `

                <div class="voice-role">

                    ${role.toUpperCase()}

                </div>

                <div class="voice-text">

                    ${text}

                </div>

            `;

            this.chatContainer.appendChild(div);

            this.chatContainer.scrollTop =

                this.chatContainer.scrollHeight;

        }

        setStatus(text, color) {

            if (!this.statusBadge)
                return;

            this.statusBadge.textContent = text;

            this.statusBadge.style.background = color;

        }

        setMicState(active) {

            if (!this.micButton)
                return;

            this.micButton.classList.toggle(

                "recording",

                active

            );

            this.micButton.innerHTML = active

                ? '<i class="fa-solid fa-stop"></i> Stop'

                : '<i class="fa-solid fa-microphone"></i> Speak';

        }

    }

    window.VoiceUI = new VoiceUI();

    document.addEventListener(

        "DOMContentLoaded",

        () => {

            VoiceUI.init();

        }

    );

})();