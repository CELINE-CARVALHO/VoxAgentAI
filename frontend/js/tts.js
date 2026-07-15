/*
==================================================
VoxAgent AI
Browser Text-To-Speech  (v2 — human-sounding)
==================================================

Changes from v1:
  • Smarter voice selection — prefers Google/natural voices over
    Microsoft's robotic defaults on Windows.
  • rate=0.92 / pitch=0.97 → feels more human, less robotic.
  • Tamil & Hindi fallback: when the OS has no ta-IN / hi-IN voice
    (very common on Windows), the text is spoken by the best available
    English voice instead of spelling out Unicode characters one-by-one.
  • Long-text chunking: Chrome silently stops after ~15 s on long
    utterances; we split at sentence boundaries to prevent cutoff.
*/

class VoxTTS {

    constructor() {
        this.voices = [];

        // Slightly slower than default (1.0) and fractionally lower
        // pitch → sounds more natural / less robotic on all platforms.
        this.rate   = 0.92;
        this.pitch  = 0.97;
        this.volume = 1.0;

        this._ready = false;
        this._loadVoices();

        if (window.speechSynthesis) {
            window.speechSynthesis.onvoiceschanged = () => {
                this._loadVoices();
            };
        }
    }

    // ------------------------------------------------------------------
    // Internal helpers
    // ------------------------------------------------------------------

    _loadVoices() {
        if (!window.speechSynthesis) return;
        this.voices = speechSynthesis.getVoices();
        this._ready = this.voices.length > 0;
    }

    /**
     * Pick the best available voice for a given BCP-47 language tag.
     *
     * Priority order:
     *   1. Exact lang match + Google voice  (most natural on Chrome)
     *   2. Exact lang match (any provider)
     *   3. Base-language prefix match + Google voice
     *   4. Base-language prefix match (any)
     *   5. Best English fallback (Google en-US or first en-* voice)
     *
     * This prevents the "spelling out Unicode characters" bug that
     * occurs when no native ta-IN / hi-IN voice is installed and
     * the browser tries to read Devanagari / Tamil script as ASCII.
     */
    _pickVoice(lang) {
        if (!this.voices.length) return null;

        const lc      = lang.toLowerCase();
        const base    = lc.split("-")[0];              // "ta", "hi", "en"
        const isNative = (v) => v.lang.toLowerCase() === lc;
        const isBase   = (v) => v.lang.toLowerCase().startsWith(base);
        const isGoogle = (v) => v.name.toLowerCase().includes("google");
        const isMs     = (v) => v.name.toLowerCase().includes("microsoft");

        const find = (predA, predB) =>
            this.voices.find((v) => predA(v) && predB(v)) || null;

        // 1. exact + Google
        const v1 = find(isNative, isGoogle);
        if (v1) return v1;

        // 2. exact (any)
        const v2 = this.voices.find(isNative) || null;
        if (v2) return v2;

        // 3. base-prefix + Google
        const v3 = find(isBase, isGoogle);
        if (v3) return v3;

        // 4. base-prefix (any)
        const v4 = this.voices.find(isBase) || null;
        if (v4) return v4;

        // 5. No native voice found → English fallback so we don't
        //    spell out Unicode characters aloud.
        const enGoogle = this.voices.find(
            (v) => v.lang.toLowerCase().startsWith("en") && isGoogle(v)
        );
        if (enGoogle) return enGoogle;

        const enAny = this.voices.find(
            (v) => v.lang.toLowerCase().startsWith("en")
        );
        if (enAny) return enAny;

        // Last resort: whatever the browser has first
        return this.voices[0] || null;
    }

    /**
     * Split text at sentence boundaries so Chrome's ~15 s TTS cutoff
     * does not silently truncate long responses.
     */
    _splitSentences(text) {
        // Split on . ! ? followed by a space or end-of-string
        const parts = text.match(/[^.!?]+[.!?]*\s*/g) || [text];
        // Recombine into chunks ≤ ~200 chars to stay safe
        const chunks = [];
        let current  = "";
        for (const part of parts) {
            if ((current + part).length > 200) {
                if (current) chunks.push(current.trim());
                current = part;
            } else {
                current += part;
            }
        }
        if (current.trim()) chunks.push(current.trim());
        return chunks.length ? chunks : [text];
    }

    // ------------------------------------------------------------------
    // Public API (same interface as v1)
    // ------------------------------------------------------------------

    stop() {
        if (window.speechSynthesis) {
            speechSynthesis.cancel();
        }
    }

    normalizeLanguage(language = "en") {
        const value = String(language || "en").toLowerCase().trim();

        if (value.startsWith("hi")) return "hi-IN";
        if (value.startsWith("ta")) return "ta-IN";
        if (value.startsWith("en")) return "en-US";

        return value.includes("-") ? value : "en-US";
    }

    speak(text, language = "en") {
        if (!text || !window.speechSynthesis ||
            typeof SpeechSynthesisUtterance === "undefined") {
            return;
        }

        this.stop();
        this._loadVoices();          // refresh — some browsers lazy-load

        const lang  = this.normalizeLanguage(language);
        const voice = this._pickVoice(lang);
        const chunks = this._splitSentences(text);

        // Queue each sentence chunk so Chrome does not cut off long text
        chunks.forEach((chunk, index) => {
            const utt    = new SpeechSynthesisUtterance(chunk);
            utt.lang     = voice ? voice.lang : lang;
            utt.rate     = this.rate;
            utt.pitch    = this.pitch;
            utt.volume   = this.volume;
            if (voice)   utt.voice = voice;

            speechSynthesis.speak(utt);
        });
    }
}

window.VoxTTS = VoxTTS;
