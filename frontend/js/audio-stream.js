/*
==========================================================
VoxAgent AI
Real-Time Audio Streaming
==========================================================

Current Phase

✓ Capture microphone
✓ Stream audio chunks
✓ Connect to Audio WebSocket

Future

✓ PCM Conversion
✓ Voice Activity Detection
✓ Noise Suppression
✓ Echo Cancellation
✓ Automatic Gain Control
✓ Barge-In
==========================================================
*/

class AudioStream {

    constructor() {

        this.ws = null;

        this.stream = null;

        this.recorder = null;

        this.recording = false;

        this.chunkSize = 250;

    }

    //----------------------------------------------------

    connect(sessionId = "demo") {

        this.ws = new WebSocket(

            `ws://${location.host}/ws/audio/${sessionId}`

        );

        this.ws.binaryType = "arraybuffer";

        this.ws.onopen = () => {

            console.log("Audio WebSocket Connected");

        };

        this.ws.onmessage = (e) => {

            console.log("Audio WS:", e.data);

        };

        this.ws.onclose = () => {

            console.log("Audio WS Closed");

        };

        this.ws.onerror = (e) => {

            console.error(e);

        };

    }

    //----------------------------------------------------

    async start() {

        if (this.recording) {

            return;

        }

        this.stream = await navigator.mediaDevices.getUserMedia({

            audio: {

                echoCancellation: true,

                noiseSuppression: true,

                autoGainControl: true,

            }

        });

        this.recorder = new MediaRecorder(

            this.stream,

            {

                mimeType: "audio/webm"

            }

        );

        this.recorder.ondataavailable = (event) => {

            if (!event.data.size) {

                return;

            }

            if (!this.ws) {

                return;

            }

            if (this.ws.readyState !== WebSocket.OPEN) {

                return;

            }

            event.data.arrayBuffer().then(buffer => {

                this.ws.send(buffer);

            });

        };

        this.recorder.start(this.chunkSize);

        this.recording = true;

        console.log("Recording Started");

    }

    //----------------------------------------------------

    stop() {

        if (!this.recording) {

            return;

        }

        this.recorder.stop();

        this.stream.getTracks().forEach(

            track => track.stop()

        );

        this.recording = false;

        console.log("Recording Stopped");

    }

}

window.AudioStream = AudioStream;