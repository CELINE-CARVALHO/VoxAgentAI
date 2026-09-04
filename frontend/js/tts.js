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

    _transliterate(text) {
        if (!text) return text;

        const DEVANAGARI_VOWELS = {
            '\u0905': 'a', '\u0906': 'aa', '\u0907': 'i', '\u0908': 'ee',
            '\u0909': 'u', '\u090a': 'oo', '\u090b': 'ri', '\u090f': 'e',
            '\u0910': 'ai', '\u0913': 'o', '\u0914': 'au'
        };

        const DEVANAGARI_MATRAS = {
            '\u093e': 'aa', '\u093f': 'i', '\u0940': 'ee', '\u0941': 'u',
            '\u0942': 'oo', '\u0943': 'ri', '\u0947': 'e', '\u0948': 'ai',
            '\u094b': 'o', '\u094c': 'au', '\u0902': 'n', '\u0901': 'n',
            '\u0903': 'h'
        };

        const DEVANAGARI_CONSONANTS = {
            '\u0915': 'ka', '\u0916': 'kha', '\u0917': 'ga', '\u0918': 'gha', '\u0919': 'nga',
            '\u091a': 'cha', '\u091b': 'chha', '\u091c': 'ja', '\u091d': 'jha', '\u091e': 'nya',
            '\u091f': 'ta', '\u0920': 'tha', '\u0921': 'da', '\u0922': 'dha', '\u0923': 'na',
            '\u0924': 'ta', '\u0925': 'tha', '\u0926': 'da', '\u0927': 'dha', '\u0928': 'na',
            '\u092a': 'pa', '\u092b': 'pha', '\u092c': 'ba', '\u092d': 'bha', '\u092e': 'ma',
            '\u092f': 'ya', '\u0930': 'ra', '\u0931': 'ra', '\u0932': 'la', '\u0933': 'la',
            '\u0934': 'la', '\u0935': 'va', '\u0936': 'sha', '\u0937': 'sha', '\u0938': 'sa',
            '\u0939': 'ha'
        };

        const HALANT = '\u094d';
        const NUKTA = '\u093c';

        const TAMIL_VOWELS = {
            '\u0b85': 'a', '\u0b86': 'aa', '\u0b87': 'i', '\u0b88': 'ee',
            '\u0b89': 'u', '\u0b8a': 'oo', '\u0b8e': 'e', '\u0b8f': 'ae',
            '\u0b90': 'ai', '\u0b92': 'o', '\u0b93': 'oe', '\u0b94': 'au'
        };

        const TAMIL_MATRAS = {
            '\u0bbe': 'aa', '\u0bbf': 'i', '\u0bc0': 'ee', '\u0bc1': 'u',
            '\u0bc2': 'oo', '\u0bc6': 'e', '\u0bc7': 'ae', '\u0bc8': 'ai',
            '\u0bca': 'o', '\u0bcb': 'oe', '\u0bcc': 'au', '\u0b82': 'n'
        };

        const TAMIL_CONSONANTS = {
            '\u0b95': 'ka', '\u0b99': 'nga', '\u0b9a': 'cha', '\u0b9c': 'ja', '\u0b9e': 'nya',
            '\u0b9f': 'ta', '\u0ba3': 'na', '\u0ba4': 'ta', '\u0ba8': 'na', '\u0ba9': 'na',
            '\u0baa': 'pa', '\u0bae': 'ma', '\u0baf': 'ya', '\u0bb0': 'ra', '\u0bb1': 'ra',
            '\u0bb2': 'la', '\u0bb3': 'la', '\u0bb4': 'zha', '\u0bb5': 'va', '\u0bb7': 'sha',
            '\u0bb8': 'sa', '\u0bb9': 'ha'
        };

        const PULLI = '\u0bcd';
        const AYTHAM = '\u0b83';

        let res = [];
        let i = 0;
        let n = text.length;

        while (i < n) {
            let char = text[i];

            // Devanagari range
            if (char >= '\u0900' && char <= '\u097f') {
                if (char === NUKTA) {
                    i++;
                    continue;
                }
                if (DEVANAGARI_CONSONANTS[char]) {
                    let baseConsonant = DEVANAGARI_CONSONANTS[char];
                    let nextIdx = i + 1;
                    let hasNukta = false;
                    if (nextIdx < n && text[nextIdx] === NUKTA) {
                        hasNukta = true;
                        nextIdx++;
                    }
                    if (hasNukta) {
                        const nuktaMap = { 'ka': 'qa', 'kha': 'kha', 'ga': 'gha', 'ja': 'za', 'da': 'ra', 'dha': 'rha', 'pa': 'fa' };
                        baseConsonant = nuktaMap[baseConsonant] || baseConsonant;
                    }
                    if (nextIdx < n && text[nextIdx] === HALANT) {
                        res.push(baseConsonant.slice(0, -1));
                        i = nextIdx + 1;
                    } else if (nextIdx < n && DEVANAGARI_MATRAS[text[nextIdx]]) {
                        let matra = DEVANAGARI_MATRAS[text[nextIdx]];
                        res.push(baseConsonant.slice(0, -1) + matra);
                        i = nextIdx + 1;
                    } else {
                        res.push(baseConsonant);
                        i = nextIdx;
                    }
                } else if (DEVANAGARI_VOWELS[char]) {
                    res.push(DEVANAGARI_VOWELS[char]);
                    i++;
                } else if (DEVANAGARI_MATRAS[char]) {
                    res.push(DEVANAGARI_MATRAS[char]);
                    i++;
                } else {
                    i++;
                }
            }
            // Tamil range
            else if (char >= '\u0b80' && char <= '\u0bff') {
                if (char === AYTHAM) {
                    res.push('kh');
                    i++;
                } else if (TAMIL_CONSONANTS[char]) {
                    let baseConsonant = TAMIL_CONSONANTS[char];
                    let nextIdx = i + 1;
                    if (nextIdx < n && text[nextIdx] === PULLI) {
                        res.push(baseConsonant.slice(0, -1));
                        i = nextIdx + 1;
                    } else if (nextIdx < n && TAMIL_MATRAS[text[nextIdx]]) {
                        let matra = TAMIL_MATRAS[text[nextIdx]];
                        res.push(baseConsonant.slice(0, -1) + matra);
                        i = nextIdx + 1;
                    } else {
                        res.push(baseConsonant);
                        i = nextIdx;
                    }
                } else if (TAMIL_VOWELS[char]) {
                    res.push(TAMIL_VOWELS[char]);
                    i++;
                } else if (TAMIL_MATRAS[char]) {
                    res.push(TAMIL_MATRAS[char]);
                    i++;
                } else {
                    i++;
                }
            }
            else {
                res.push(char);
                i++;
            }
        }
        return res.join('');
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
        let voice = this._pickVoice(lang);

        // Fallback: If voice is English but requested language is Hindi or Tamil, and text contains Unicode Hindi/Tamil
        const isEnglishFallback = voice && voice.lang.toLowerCase().startsWith("en") && !lang.startsWith("en");
        const hasUnicodeIndic = /[\u0900-\u097F\u0B80-\u0BFF]/.test(text);

        if (isEnglishFallback && hasUnicodeIndic) {
            text = this._transliterate(text);
            // Re-pick voice for English since we transliterated to Hinglish/Tanglish
            voice = this._pickVoice("en-US");
        }

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
