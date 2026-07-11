/*
=========================================================
VoxAgent AI Recorder
=========================================================
*/

(function () {

    "use strict";

    class VoxRecorder {

        constructor() {

            this.recording = false;

        }

        async toggle() {

            if (!this.recording) {

                await VoxAudio.start();

                this.recording = true;

                return;

            }

            const blob = await VoxAudio.stop();

            this.recording = false;

            if (!blob)
                return;

            const formData = new FormData();

            formData.append(

                "audio",

                blob,

                "voice.webm"

            );

            const response = await fetch(

                "http://127.0.0.1:8000/api/voice/transcribe",

                {

                    method: "POST",

                    body: formData

                }

            );

            const json = await response.json();

            console.log(json);

        }

    }

    window.VoxRecorder = new VoxRecorder();

})();