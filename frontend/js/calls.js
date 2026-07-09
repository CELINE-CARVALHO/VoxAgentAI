/* ==========================================================================
   VoxAgent AI - calls.js
   Live Call console driven by the real backend: /api/calls/start,
   /api/calls/:id/message, /api/calls/:id/end. Language, intent, sentiment,
   and response come from Gemini server-side. Web Speech API is layered on top
   as optional STT input and TTS playback; typed messages work on their own.
   ========================================================================== */

(function () {
  'use strict';

  if (document.body.getAttribute('data-page') !== 'live-calls') return;
  if (!window.VoxAPI.isAuthenticated()) { window.location.href = 'login.html'; return; }

  const { toast } = window.VoxUtils;

  const el = {
    statusDot: document.getElementById('callStatusDot'),
    statusText: document.getElementById('callStatusText'),
    timer: document.getElementById('callTimer'),
    transcript: document.getElementById('callTranscript'),
    emptyState: document.getElementById('callEmptyState'),
    startBtn: document.getElementById('startCallBtn'),
    endBtn: document.getElementById('endCallBtn'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendMessageBtn'),
  };

  if (Object.values(el).some((node) => !node)) {
    console.error('Live calls page is missing required markup.');
    return;
  }

  const state = {
    callId: null,
    active: false,
    sending: false,
    startTime: null,
    timerInterval: null,
    recognition: null,
    recognitionSupported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
    synthSupported: !!window.speechSynthesis,
  };

  const BCP47_BY_LANG = {
    en: 'en-US',
    es: 'es-ES',
    fr: 'fr-FR',
    de: 'de-DE',
    hi: 'hi-IN',
    pt: 'pt-PT',
    ja: 'ja-JP',
    zh: 'zh-CN',
    ar: 'ar-SA',
    ru: 'ru-RU',
    it: 'it-IT',
    ko: 'ko-KR',
  };

  function formatTimer(ms) {
    const totalSec = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  function setStatus(text, live) {
    el.statusText.textContent = text;
    el.statusDot.style.display = live ? '' : 'none';
  }

  function appendTurn(role, text, metaText) {
    if (el.emptyState && !el.emptyState.hidden) el.emptyState.hidden = true;

    const turnEl = document.createElement('div');
    turnEl.className = `turn turn-${role}`;
    turnEl.style.cssText = 'display:flex; gap:var(--space-3); align-items:flex-start;' +
      (role === 'user' ? ' flex-direction:row-reverse;' : '');

    const avatarEl = document.createElement('div');
    avatarEl.className = 'turn-avatar';
    avatarEl.innerHTML = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const bubbleEl = document.createElement('div');
    bubbleEl.className = 'turn-bubble';

    const textEl = document.createElement('p');
    textEl.className = 'turn-text';
    textEl.textContent = text;

    bubbleEl.appendChild(textEl);

    if (metaText) {
      const metaEl = document.createElement('span');
      metaEl.className = 'turn-meta text-muted';
      metaEl.style.cssText = 'font-size:var(--fs-xs); display:block; margin-top:4px;';
      metaEl.textContent = metaText;
      bubbleEl.appendChild(metaEl);
    }

    turnEl.appendChild(avatarEl);
    turnEl.appendChild(bubbleEl);
    el.transcript.appendChild(turnEl);
    el.transcript.scrollTop = el.transcript.scrollHeight;
  }

  function currentTimeLabel() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function startTimer() {
    state.startTime = Date.now();
    state.timerInterval = setInterval(() => {
      el.timer.textContent = formatTimer(Date.now() - state.startTime);
    }, 1000);
  }

  function stopTimer() {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }

  function speak(text, langCode) {
    if (!state.synthSupported) return;
    const bcp47 = BCP47_BY_LANG[langCode] || 'en-US';

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = bcp47;

    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find((v) => v.lang === bcp47) || voices.find((v) => v.lang.startsWith(langCode));
    if (matchedVoice) utterance.voice = matchedVoice;

    window.speechSynthesis.speak(utterance);
  }

  function createRecognition() {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      const transcript = lastResult[0].transcript;
      sendUtterance(transcript);
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'permission-denied') {
        toast('Microphone access denied - you can still type messages below.', 'error');
      }
    };

    recognition.onend = () => {
      if (state.active) {
        try { recognition.start(); } catch (e) { /* already started */ }
      }
    };

    return recognition;
  }

  async function sendUtterance(rawText) {
    const text = rawText.trim();
    if (!text || !state.active || state.sending || !state.callId) return;

    appendTurn('user', text, currentTimeLabel());
    state.sending = true;
    setStatus('Thinking...', true);
    el.sendBtn.disabled = true;

    try {
      const result = await window.VoxAPI.sendMessage(state.callId, text);
      appendTurn(
        'ai',
        result.reply,
        `${result.language?.toUpperCase() || 'EN'} - ${result.intent || 'general'} - ${result.sentiment || 'neutral'} - ${result.latency_ms ?? 0}ms`
      );
      speak(result.reply, result.language);
    } catch (err) {
      toast(err.message, 'error');
      appendTurn('ai', 'Sorry, something went wrong reaching the AI agent.', 'error');
    } finally {
      state.sending = false;
      setStatus('Listening...', true);
      el.sendBtn.disabled = false;
    }
  }

  async function startCall() {
    el.startBtn.disabled = true;
    setStatus('Connecting...', true);

    try {
      const { call, greeting } = await window.VoxAPI.startCall({});
      state.callId = call.id;
      state.active = true;

      startTimer();
      setStatus('Listening...', true);

      el.startBtn.classList.add('hidden');
      el.endBtn.classList.remove('hidden');
      el.messageInput.classList.remove('hidden');
      el.sendBtn.classList.remove('hidden');
      el.messageInput.disabled = false;
      el.sendBtn.disabled = false;
      el.messageInput.focus();

      appendTurn('ai', greeting.reply, `${greeting.language?.toUpperCase() || 'EN'} - greeting - ${greeting.latency_ms ?? 0}ms`);
      speak(greeting.reply, greeting.language);

      if (state.recognitionSupported) {
        state.recognition = createRecognition();
        try { state.recognition.start(); } catch (e) { console.warn('Speech recognition could not start:', e); }
      }
    } catch (err) {
      toast(err.message, 'error');
      setStatus('No active call', false);
      el.startBtn.disabled = false;
    }
  }

  async function endCall() {
    const callId = state.callId;
    state.active = false;

    stopTimer();
    setStatus('Ending call...', false);
    if (state.recognition) {
      state.recognition.onend = null;
      state.recognition.stop();
    }
    if (state.synthSupported) window.speechSynthesis.cancel();

    el.endBtn.disabled = true;
    try {
      if (callId) await window.VoxAPI.endCall(callId);
    } catch (err) {
      toast(err.message, 'error');
    }

    state.callId = null;
    setStatus('No active call', false);
    el.startBtn.classList.remove('hidden');
    el.startBtn.disabled = false;
    el.endBtn.classList.add('hidden');
    el.endBtn.disabled = false;
    el.messageInput.classList.add('hidden');
    el.sendBtn.classList.add('hidden');
    el.messageInput.value = '';
    el.messageInput.disabled = true;
    el.sendBtn.disabled = true;
    el.timer.textContent = '00:00';
  }

  el.startBtn.addEventListener('click', startCall);
  el.endBtn.addEventListener('click', endCall);
  el.sendBtn.addEventListener('click', () => {
    const text = el.messageInput.value;
    if (!text.trim()) return;
    sendUtterance(text);
    el.messageInput.value = '';
  });
  el.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      el.sendBtn.click();
    }
  });

  if (state.synthSupported) {
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
  }
})();
