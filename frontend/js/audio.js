/*
=========================================================
VoxAgent AI
Audio Recorder
=========================================================
*/

(function () {
    "use strict";

    class VoxAudio {
        constructor() {
            this.stream = null;
            this.recorder = null;
            this.chunks = [];
            this.recording = false;
            this.mimeType = this.pickMimeType();
        }

        pickMimeType() {
            if (!window.MediaRecorder) {
                return "";
            }

            if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                return "audio/webm;codecs=opus";
            }

            if (MediaRecorder.isTypeSupported("audio/webm")) {
                return "audio/webm";
            }

            return "";
        }

        async initialize() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Microphone recording is not supported in this browser.");
            }

            if (this.stream && this.stream.active) {
                return;
            }

            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
        }

        async start() {
            if (this.recording) {
                return;
            }

            await this.initialize();

            this.chunks = [];

            const options = this.mimeType ? { mimeType: this.mimeType } : undefined;
            this.recorder = new MediaRecorder(this.stream, options);

            this.recorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.chunks.push(event.data);
                }
            };

            this.recorder.start(250);
            this.recording = true;
        }

        stop() {
            return new Promise((resolve) => {
                if (!this.recorder || this.recorder.state === "inactive") {
                    this.recording = false;
                    resolve(null);
                    return;
                }

                this.recorder.onstop = () => {
                    this.recording = false;

                    const blob = new Blob(this.chunks, {
                        type: this.mimeType || "audio/webm",
                    });

                    this.chunks = [];
                    resolve(blob);
                };

                this.recorder.stop();
            });
        }

        cancel() {
            if (this.recorder && this.recorder.state !== "inactive") {
                this.recorder.stop();
            }

            this.recording = false;
            this.chunks = [];
        }

        release() {
            this.cancel();

            if (this.stream) {
                this.stream.getTracks().forEach((track) => track.stop());
                this.stream = null;
            }
        }

        isRecording() {
            return this.recording;
        }
    }

    window.VoxAudio = new VoxAudio();
})();
