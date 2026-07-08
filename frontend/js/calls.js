/* ==========================================================================
   VoxAgent AI — calls.js
   Live Call Simulator engine: state machine, Web Speech API (STT + TTS),
   mock RAG pipeline (language/intent/sentiment detection + knowledge base),
   and live transcript rendering.

   NOTE (prototype simplification): Real language identification normally
   happens via a dedicated model before/alongside STT. Browser SpeechRecognition
   requires a `lang` to be set in advance and does not auto-detect it. For this
   demo, we run a lightweight keyword-based "language detector" on the
   recognized text so the UI can still demonstrate the multilingual pipeline
   end-to-end without a paid cloud speech service.
   ========================================================================== */

(function () {
  'use strict';

  /* ------------------------------------------------------------------------
     0. GUARD — only run this script on the live-calls page
     ------------------------------------------------------------------------ */
  if (document.body.getAttribute('data-page') !== 'live-calls') return;

  /* ------------------------------------------------------------------------
     1. DOM REFERENCES
     ------------------------------------------------------------------------ */
  const el = {
    callId: document.getElementById('callId'),
    callTimer: document.getElementById('callTimer'),
    liveWave: document.getElementById('liveWave'),
    callStateLabel: document.getElementById('callStateLabel'),
    detectedLanguage: document.getElementById('detectedLanguage'),
    currentIntent: document.getElementById('currentIntent'),
    currentSentiment: document.getElementById('currentSentiment'),
    startBtn: document.getElementById('startCallBtn'),
    pauseBtn: document.getElementById('pauseCallBtn'),
    resumeBtn: document.getElementById('resumeCallBtn'),
    muteBtn: document.getElementById('muteCallBtn'),
    endBtn: document.getElementById('endCallBtn'),
    callHint: document.getElementById('callHint'),
    transcriptScroll: document.getElementById('transcriptScroll'),
    transcriptEmpty: document.getElementById('transcriptEmpty'),
    clearBtn: document.getElementById('clearTranscriptBtn'),
    manualForm: document.getElementById('manualInputForm'),
    manualInput: document.getElementById('manualInput'),
    manualSendBtn: document.getElementById('manualSendBtn'),
  };

  /* ------------------------------------------------------------------------
     2. STATE
     ------------------------------------------------------------------------ */
  const state = {
    active: false,
    paused: false,
    muted: false,
    startTime: null,
    timerInterval: null,
    recognition: null,
    recognitionSupported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    synthSupported: !!window.speechSynthesis,
    turnCount: 0,
    lastDetectedLangCode: 'en',
  };

  /* ------------------------------------------------------------------------
     3. LANGUAGE TABLE
     Maps a short code -> display info + BCP-47 tag (for TTS voice matching)
     ------------------------------------------------------------------------ */
  const LANGUAGES = {
    en: { label: 'English', flag: '🇬🇧', bcp47: 'en-US', keywords: ['the', 'hello', 'order', 'refund', 'please', 'thanks', 'help', 'status'] },
    es: { label: 'Spanish', flag: '🇪🇸', bcp47: 'es-ES', keywords: ['hola', 'pedido', 'gracias', 'cómo', 'qué', 'por favor', 'ayuda', 'estado'] },
    fr: { label: 'French', flag: '🇫🇷', bcp47: 'fr-FR', keywords: ['bonjour', 'commande', 'merci', 'comment', 'aide', 'statut', "s'il", 'remboursement'] },
    de: { label: 'German', flag: '🇩🇪', bcp47: 'de-DE', keywords: ['hallo', 'bestellung', 'danke', 'wie', 'hilfe', 'status', 'bitte', 'erstattung'] },
    hi: { label: 'Hindi', flag: '🇮🇳', bcp47: 'hi-IN', keywords: ['नमस्ते', 'धन्यवाद', 'मदद', 'ऑर्डर', 'कृपया', 'स्थिति'] },
  };

  /* ------------------------------------------------------------------------
     4. MOCK KNOWLEDGE BASE (simulates the Pinecone-retrieved RAG context)
     Each entry: intent tag, trigger keywords, and per-language response templates
     ------------------------------------------------------------------------ */
  const KNOWLEDGE_BASE = [
    {
      intent: 'Order Status Inquiry',
      keywords: ['order', 'status', 'pedido', 'estado', 'commande', 'statut', 'bestellung', 'ऑर्डर', 'स्थिति', 'track', 'shipped', 'delivery'],
      responses: {
        en: 'Your order was shipped yesterday and is expected to arrive within 2-3 business days.',
        es: 'Tu pedido fue enviado ayer y llega en 2 a 3 días hábiles.',
        fr: 'Votre commande a été expédiée hier et arrivera dans 2 à 3 jours ouvrables.',
        de: 'Ihre Bestellung wurde gestern versandt und trifft in 2 bis 3 Werktagen ein.',
        hi: 'आपका ऑर्डर कल भेज दिया गया था और 2-3 कार्य दिवसों में पहुंच जाएगा।',
      },
    },
    {
      intent: 'Refund Request',
      keywords: ['refund', 'reembolso', 'reembolso', 'remboursement', 'erstattung', 'money back', 'return'],
      responses: {
        en: 'I can help with that. Refunds are processed within 5-7 business days after the item is received.',
        es: 'Puedo ayudarte con eso. Los reembolsos se procesan en 5 a 7 días hábiles.',
        fr: 'Je peux vous aider. Les remboursements sont traités sous 5 à 7 jours ouvrables.',
        de: 'Ich kann Ihnen helfen. Rückerstattungen werden innerhalb von 5-7 Werktagen bearbeitet.',
        hi: 'मैं इसमें आपकी मदद कर सकता हूँ। रिफंड 5-7 कार्य दिवसों में संसाधित होता है।',
      },
    },
    {
      intent: 'Technical Support',
      keywords: ['not working', 'error', 'bug', 'issue', 'problem', 'ayuda técnica', 'problème', 'fehler', 'समस्या'],
      responses: {
        en: "I'm sorry you're running into that. Could you tell me which device and app version you're using?",
        es: 'Lamento el inconveniente. ¿Podrías decirme qué dispositivo y versión de la app usas?',
        fr: "Je suis désolé pour ce problème. Pouvez-vous me dire quel appareil et quelle version vous utilisez ?",
        de: 'Das tut mir leid. Können Sie mir sagen, welches Gerät und welche App-Version Sie verwenden?',
        hi: 'मुझे खेद है। क्या आप बता सकते हैं कि आप कौन सा डिवाइस और ऐप वर्शन उपयोग कर रहे हैं?',
      },
    },
    {
      intent: 'Greeting',
      keywords: ['hello', 'hi', 'hola', 'bonjour', 'hallo', 'नमस्ते', 'hey'],
      responses: {
        en: "Hello! I'm your AI assistant. How can I help you today?",
        es: '¡Hola! Soy tu asistente de IA. ¿Cómo puedo ayudarte hoy?',
        fr: "Bonjour ! Je suis votre assistant IA. Comment puis-je vous aider aujourd'hui ?",
        de: 'Hallo! Ich bin Ihr KI-Assistent. Wie kann ich Ihnen heute helfen?',
        hi: 'नमस्ते! मैं आपका एआई सहायक हूं। मैं आज आपकी कैसे मदद कर सकता हूं?',
      },
    },
    {
      intent: 'Gratitude',
      keywords: ['thanks', 'thank you', 'gracias', 'merci', 'danke', 'धन्यवाद'],
      responses: {
        en: "You're welcome! Is there anything else I can help you with?",
        es: '¡De nada! ¿Hay algo más en lo que pueda ayudarte?',
        fr: "Je vous en prie ! Y a-t-il autre chose que je puisse faire pour vous ?",
        de: 'Gerne! Gibt es noch etwas, womit ich Ihnen helfen kann?',
        hi: 'आपका स्वागत है! क्या मैं आपकी और किसी चीज़ में मदद कर सकता हूँ?',
      },
    },
  ];

  const FALLBACK_RESPONSE = {
    en: "I want to make sure I get this right — could you rephrase that or give me a bit more detail?",
    es: 'Quiero asegurarme de entender bien. ¿Podrías darme un poco más de detalle?',
    fr: "Je veux être sûr de bien comprendre. Pourriez-vous préciser un peu plus ?",
    de: 'Ich möchte sichergehen, dass ich das richtig verstehe. Könnten Sie das genauer erklären?',
    hi: 'मैं यह सुनिश्चित करना चाहता हूँ कि मैं सही ढंग से समझूँ। क्या आप थोड़ा और विवरण दे सकते हैं?',
  };

  /* ------------------------------------------------------------------------
     5. SENTIMENT KEYWORD LISTS (very lightweight lexical sentiment classifier)
     ------------------------------------------------------------------------ */
  const SENTIMENT_WORDS = {
    positive: ['thanks', 'thank', 'great', 'gracias', 'perfecto', 'merci', 'danke', 'good', 'awesome', 'happy', 'love', 'excellent'],
    negative: ['angry', 'bad', 'terrible', 'awful', 'frustrated', 'annoyed', 'not working', 'problem', 'issue', 'error', 'malo', 'problème', 'schlecht'],
  };

  /* ------------------------------------------------------------------------
     6. UTILITIES
     ------------------------------------------------------------------------ */
  function pad(n) { return String(n).padStart(2, '0'); }

  function formatTimer(ms) {
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${pad(min)}:${pad(sec)}`;
  }

  function generateCallId() {
    const rand = Math.floor(1000 + Math.random() * 9000);
    return `#C-${rand}`;
  }

  function detectLanguage(text) {
    const lower = text.toLowerCase();
    let bestMatch = { code: 'en', score: 0 };
    Object.entries(LANGUAGES).forEach(([code, data]) => {
      const score = data.keywords.reduce((acc, kw) => acc + (lower.includes(kw.toLowerCase()) ? 1 : 0), 0);
      if (score > bestMatch.score) bestMatch = { code, score };
    });
    // Fall back to the last detected language if nothing matched, so the
    // conversation doesn't flip-flop to English on short utterances.
    return bestMatch.score > 0 ? bestMatch.code : state.lastDetectedLangCode;
  }

  function detectIntentAndResponse(text, langCode) {
    const lower = text.toLowerCase();
    const match = KNOWLEDGE_BASE.find((entry) =>
      entry.keywords.some((kw) => lower.includes(kw.toLowerCase()))
    );
    if (match) {
      return {
        intent: match.intent,
        response: match.responses[langCode] || match.responses.en,
      };
    }
    return {
      intent: 'General Inquiry',
      response: FALLBACK_RESPONSE[langCode] || FALLBACK_RESPONSE.en,
    };
  }

  function detectSentiment(text) {
    const lower = text.toLowerCase();
    const posScore = SENTIMENT_WORDS.positive.reduce((a, w) => a + (lower.includes(w) ? 1 : 0), 0);
    const negScore = SENTIMENT_WORDS.negative.reduce((a, w) => a + (lower.includes(w) ? 1 : 0), 0);
    if (posScore > negScore) return 'positive';
    if (negScore > posScore) return 'negative';
    return 'neutral';
  }

  /* ------------------------------------------------------------------------
     7. UI UPDATES
     ------------------------------------------------------------------------ */
  function updateWaveState(isSpeaking) {
    if (isSpeaking) {
      el.liveWave.classList.remove('idle');
    } else {
      el.liveWave.classList.add('idle');
    }
  }

  function updateStateLabel(text) {
    el.callStateLabel.textContent = text;
  }

  function updateDetectedLanguage(code) {
    state.lastDetectedLangCode = code;
    const lang = LANGUAGES[code] || LANGUAGES.en;
    el.detectedLanguage.innerHTML = `<i class="fa-solid fa-language"></i> ${lang.flag} ${lang.label}`;
  }

  function updateIntent(intentLabel) {
    el.currentIntent.innerHTML = `<i class="fa-solid fa-bullseye"></i> ${intentLabel}`;
  }

  function updateSentiment(sentiment) {
    const iconMap = {
      positive: 'fa-face-smile',
      neutral: 'fa-face-meh',
      negative: 'fa-face-frown',
    };
    const classMap = {
      positive: 'sentiment-positive',
      neutral: 'sentiment-neutral',
      negative: 'sentiment-negative',
    };
    el.currentSentiment.className = `meta-value ${classMap[sentiment]}`;
    el.currentSentiment.innerHTML = `<i class="fa-solid ${iconMap[sentiment]}"></i> ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}`;
  }

  function appendTurn(role, text, metaText) {
    if (el.transcriptEmpty && !el.transcriptEmpty.hidden) {
      el.transcriptEmpty.hidden = true;
    }
    state.turnCount += 1;

    const turnEl = document.createElement('div');
    turnEl.className = `turn turn-${role}`;

    const avatarEl = document.createElement('div');
    avatarEl.className = 'turn-avatar';
    avatarEl.innerHTML = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'turn-bubble';

    const textEl = document.createElement('p');
    textEl.className = 'turn-text';
    textEl.textContent = text;

    const metaEl = document.createElement('span');
    metaEl.className = 'turn-meta';
    metaEl.textContent = metaText;

    bubbleEl.appendChild(textEl);
    bubbleEl.appendChild(metaEl);
    turnEl.appendChild(avatarEl);
    turnEl.appendChild(bubbleEl);

    el.transcriptScroll.appendChild(turnEl);
    el.transcriptScroll.scrollTop = el.transcriptScroll.scrollHeight;
  }

  function currentTimeLabel() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /* ------------------------------------------------------------------------
     8. TEXT-TO-SPEECH (AI response playback)
     ------------------------------------------------------------------------ */
  function speak(text, langCode) {
    if (!state.synthSupported) return;
    const bcp47 = (LANGUAGES[langCode] || LANGUAGES.en).bcp47;

    // Cancel anything currently queued so responses don't overlap
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = bcp47;
    utterance.rate = 1;
    utterance.pitch = 1;

    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) => v.lang === bcp47) || voices.find((v) => v.lang.startsWith(langCode));
    if (matchedVoice) utterance.voice = matchedVoice;

    utterance.onstart = () => updateWaveState(true);
    utterance.onend = () => updateWaveState(!state.paused && state.active ? true : false);

    window.speechSynthesis.speak(utterance);
  }

  /* ------------------------------------------------------------------------
     9. CORE PIPELINE — user utterance -> detection -> response -> speak
     ------------------------------------------------------------------------ */
  function processUserUtterance(rawText) {
    const text = rawText.trim();
    if (!text) return;

    const langCode = detectLanguage(text);
    const sentiment = detectSentiment(text);
    const { intent, response } = detectIntentAndResponse(text, langCode);

    updateDetectedLanguage(langCode);
    updateIntent(intent);
    updateSentiment(sentiment);

    appendTurn('user', text, currentTimeLabel());

    // Simulate embedding + vector search + LLM generation latency
    updateStateLabel('Thinking…');
    const simulatedLatencyMs = 280 + Math.floor(Math.random() * 260);

    setTimeout(() => {
      appendTurn('ai', response, `Gemini · ${simulatedLatencyMs}ms`);
      updateStateLabel(state.muted ? 'Muted' : 'Listening…');
      speak(response, langCode);
    }, simulatedLatencyMs);
  }

  /* ------------------------------------------------------------------------
     10. SPEECH RECOGNITION SETUP
     ------------------------------------------------------------------------ */
  function createRecognition() {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US'; // Base recognition locale; our lexical detector then flags the actual language

    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      const transcript = lastResult[0].transcript;
      processUserUtterance(transcript);
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'permission-denied') {
        updateStateLabel('Microphone access denied');
        el.callHint.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Microphone access was denied. You can still type messages below.';
      }
    };

    recognition.onend = () => {
      // Auto-restart if the call is still active/unmuted (browsers stop recognition periodically)
      if (state.active && !state.paused && !state.muted) {
        try { recognition.start(); } catch (e) { /* already started */ }
      }
    };

    return recognition;
  }

  /* ------------------------------------------------------------------------
     11. CALL TIMER
     ------------------------------------------------------------------------ */
  function startTimer() {
    state.startTime = Date.now();
    state.timerInterval = setInterval(() => {
      el.callTimer.textContent = formatTimer(Date.now() - state.startTime);
    }, 1000);
  }

  function stopTimer() {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }

  /* ------------------------------------------------------------------------
     12. CALL CONTROL ACTIONS
     ------------------------------------------------------------------------ */
  function startCall() {
    state.active = true;
    state.paused = false;
    state.muted = false;

    el.callId.textContent = generateCallId();
    startTimer();
    updateWaveState(true);
    updateStateLabel('Listening…');
    el.callHint.innerHTML = '<i class="fa-solid fa-microphone"></i> Speak now — the AI agent is listening.';

    el.startBtn.disabled = true;
    el.pauseBtn.disabled = false;
    el.muteBtn.disabled = false;
    el.endBtn.disabled = false;
    el.manualInput.disabled = false;
    el.manualSendBtn.disabled = false;

    if (state.recognitionSupported) {
      state.recognition = createRecognition();
      try {
        state.recognition.start();
      } catch (e) {
        console.warn('Speech recognition could not start:', e);
      }
    } else {
      el.callHint.innerHTML = '<i class="fa-solid fa-circle-info"></i> Speech recognition isn\'t supported in this browser. Type a message below instead.';
    }

    // Greet the caller to kick off the conversation, mirroring a real IVR/agent opener
    setTimeout(() => {
      const greeting = 'Hello! Thanks for calling. How can I help you today?';
      appendTurn('ai', greeting, 'Gemini · 210ms');
      speak(greeting, 'en');
    }, 500);
  }

  function pauseCall() {
    state.paused = true;
    updateStateLabel('Paused');
    updateWaveState(false);
    if (state.recognition) state.recognition.stop();

    el.pauseBtn.hidden = true;
    el.pauseBtn.disabled = true;
    el.resumeBtn.hidden = false;
    el.resumeBtn.disabled = false;
  }

  function resumeCall() {
    state.paused = false;
    updateStateLabel(state.muted ? 'Muted' : 'Listening…');
    updateWaveState(!state.muted);

    if (state.recognitionSupported && !state.muted) {
      try { state.recognition.start(); } catch (e) { /* already started */ }
    }

    el.resumeBtn.hidden = true;
    el.resumeBtn.disabled = true;
    el.pauseBtn.hidden = false;
    el.pauseBtn.disabled = false;
  }

  function toggleMute() {
    state.muted = !state.muted;
    el.muteBtn.classList.toggle('active', state.muted);
    el.muteBtn.innerHTML = state.muted
      ? '<i class="fa-solid fa-microphone-slash"></i> Unmute'
      : '<i class="fa-solid fa-microphone"></i> Mute';

    if (state.muted) {
      updateStateLabel('Muted');
      updateWaveState(false);
      if (state.recognition) state.recognition.stop();
    } else if (state.active && !state.paused) {
      updateStateLabel('Listening…');
      updateWaveState(true);
      if (state.recognitionSupported) {
        try { state.recognition.start(); } catch (e) { /* already started */ }
      }
    }
  }

  function endCall() {
    state.active = false;
    state.paused = false;
    state.muted = false;

    stopTimer();
    updateWaveState(false);
    updateStateLabel('Call ended');
    el.callHint.innerHTML = '<i class="fa-solid fa-circle-check"></i> Call ended. Click "Start Call" to begin a new session.';

    if (state.recognition) {
      state.recognition.onend = null; // prevent auto-restart
      state.recognition.stop();
    }
    if (state.synthSupported) window.speechSynthesis.cancel();

    el.startBtn.disabled = false;
    el.pauseBtn.disabled = true;
    el.pauseBtn.hidden = false;
    el.resumeBtn.disabled = true;
    el.resumeBtn.hidden = true;
    el.muteBtn.disabled = true;
    el.muteBtn.classList.remove('active');
    el.muteBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Mute';
    el.endBtn.disabled = true;
    el.manualInput.disabled = true;
    el.manualSendBtn.disabled = true;

    el.detectedLanguage.innerHTML = '<i class="fa-solid fa-language"></i> —';
    el.currentIntent.innerHTML = '<i class="fa-solid fa-bullseye"></i> —';
    el.currentSentiment.className = 'meta-value sentiment-neutral';
    el.currentSentiment.innerHTML = '<i class="fa-solid fa-face-meh"></i> Neutral';
  }

  function clearTranscript() {
    el.transcriptScroll.innerHTML = '';
    el.transcriptScroll.appendChild(el.transcriptEmpty);
    el.transcriptEmpty.hidden = false;
    state.turnCount = 0;
  }

  /* ------------------------------------------------------------------------
     13. MANUAL TEXT INPUT FALLBACK
     ------------------------------------------------------------------------ */
  function handleManualSubmit(e) {
    e.preventDefault();
    if (!state.active || state.paused) return;
    const text = el.manualInput.value;
    if (!text.trim()) return;
    processUserUtterance(text);
    el.manualInput.value = '';
  }

  /* ------------------------------------------------------------------------
     14. EVENT BINDINGS
     ------------------------------------------------------------------------ */
  el.startBtn.addEventListener('click', startCall);
  el.pauseBtn.addEventListener('click', pauseCall);
  el.resumeBtn.addEventListener('click', resumeCall);
  el.muteBtn.addEventListener('click', toggleMute);
  el.endBtn.addEventListener('click', endCall);
  el.clearBtn.addEventListener('click', clearTranscript);
  el.manualForm.addEventListener('submit', handleManualSubmit);

  // Ensure voices are loaded (some browsers populate this list asynchronously)
  if (state.synthSupported) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }

  // Initial idle state for the wave visualization
  updateWaveState(false);
})();
