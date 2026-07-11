/*
=========================================================
VoxAgent AI
Audio Service
=========================================================

Responsibilities

✓ Request microphone permission
✓ Start recording
✓ Stop recording
✓ Return audio blob

No websocket code.
No UI code.

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

        }

        async initialize() {

            if (this.stream)
                return;

            this.stream = await navigator.mediaDevices.getUserMedia({

                audio: {

                    echoCancellation: true,

                    noiseSuppression: true,

                    autoGainControl: true

                }

            });

        }

        async start() {

            await this.initialize();

            this.chunks = [];

            this.recorder = new MediaRecorder(this.stream);

            this.recorder.ondataavailable = (event) => {

                if (event.data.size > 0)

                    this.chunks.push(event.data);

            };

            this.recorder.start(250);

            this.recording = true;

            console.log("🎤 Recording Started");

        }

        stop() {

            return new Promise((resolve) => {

                if (!this.recorder) {

                    resolve(null);

                    return;

                }

                this.recorder.onstop = () => {

                    this.recording = false;

                    const blob = new Blob(

                        this.chunks,

                        {

                            type: "audio/webm"

                        }

                    );

                    console.log("🛑 Recording Stopped");

                    resolve(blob);

                };

                this.recorder.stop();

            });

        }

        isRecording() {

            return this.recording;

        }

    }

    window.VoxAudio = new VoxAudio();

})();