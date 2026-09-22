/**
 * notifications.js — Daily Tracker Notification System
 *
 * Responsibilities:
 *  1. Register service worker (PWA + push readiness)
 *  2. Request / track browser notification permission
 *  3. Poll /api/notifications/due every 60 s for due reminders
 *  4. Fire browser (OS) notifications via the Notifications API
 *  5. Play in-page audio chime (Web Audio API, gracefully handles autoplay block)
 *  6. Show in-app alert overlay when the page is open
 *  7. Expose NotificationManager globally for the Settings page
 */

window.NotificationManager = (function () {
  'use strict';

  /* ── Constants ─────────────────────────────────────────────────────── */
  const POLL_INTERVAL_MS  = 60_000;   // 1 minute
  const AUDIO_SRC         = '/static/sounds/reminder.wav';
  const SW_SRC            = '/static/service-worker.js';
  const PREF_KEY          = 'dt_notif_prefs';

  /* ── State ──────────────────────────────────────────────────────────── */
  let _swRegistration  = null;
  let _audioCtx        = null;
  let _audioBuffer     = null;
  let _audioReady      = false;
  let _userInteracted  = false;
  let _pollTimer       = null;
  let _seenIds         = new Set();   // reminder IDs dispatched this session

  /* ── Preferences (merged: server + localStorage) ───────────────────── */
  let _prefs = {
    notif_browser:         true,
    notif_sound:           true,
    notif_in_app:          true,
    notif_overdue:         true,
    notif_daily_summary:   true,
    notif_reminder_offset: 10,
    notif_summary_time:    '08:00',
    volume:                0.8,       // 0–1, localStorage only
    sound_name:            'default', // localStorage only
  };

  function _loadPrefsFromStorage() {
    try {
      const saved = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
      Object.assign(_prefs, saved);
    } catch (_) {}
  }
  function _savePrefsToStorage() {
    try { localStorage.setItem(PREF_KEY, JSON.stringify(_prefs)); } catch (_) {}
  }
  async function _loadPrefsFromServer() {
    try {
      const s = await window.API.get('/api/notifications/settings');
      Object.assign(_prefs, {
        notif_browser:         s.notif_browser,
        notif_sound:           s.notif_sound,
        notif_in_app:          s.notif_in_app,
        notif_overdue:         s.notif_overdue,
        notif_daily_summary:   s.notif_daily_summary,
        notif_reminder_offset: s.notif_reminder_offset,
        notif_summary_time:    s.notif_summary_time,
      });
    } catch (_) {}
  }

  /* ── Service Worker registration ────────────────────────────────────── */
  async function _registerSW() {
    if (!('serviceWorker' in navigator)) return null;
    try {
      _swRegistration = await navigator.serviceWorker.register(SW_SRC, { scope: '/' });
      return _swRegistration;
    } catch (err) {
      console.warn('[NotificationManager] SW registration failed:', err);
      return null;
    }
  }

  /* ── Permission ─────────────────────────────────────────────────────── */
  function getPermissionStatus() {
    if (!('Notification' in window)) return 'unsupported';
    return Notification.permission; // 'default' | 'granted' | 'denied'
  }

  async function requestPermission() {
    if (!('Notification' in window)) return 'unsupported';
    if (Notification.permission === 'granted') return 'granted';
    if (Notification.permission === 'denied')  return 'denied';
    try {
      const result = await Notification.requestPermission();
      return result;
    } catch (_) { return 'denied'; }
  }

  /* ── Audio ──────────────────────────────────────────────────────────── */
  async function _initAudio() {
    if (_audioReady) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      _audioCtx = new AudioCtx();
      const response = await fetch(AUDIO_SRC);
      const arrayBuf = await response.arrayBuffer();
      _audioBuffer = await _audioCtx.decodeAudioData(arrayBuf);
      _audioReady = true;
    } catch (err) {
      console.warn('[NotificationManager] Audio init failed:', err);
    }
  }

  async function playSound(volume) {
    const vol = (volume !== undefined ? volume : _prefs.volume) || 0.8;
    if (!_prefs.notif_sound) return;
    if (!_userInteracted) {
      console.info('[NotificationManager] Autoplay blocked — user has not interacted yet.');
      return;
    }
    try {
      await _initAudio();
      if (!_audioReady || !_audioCtx || !_audioBuffer) return;
      if (_audioCtx.state === 'suspended') await _audioCtx.resume();
      const source = _audioCtx.createBufferSource();
      source.buffer = _audioBuffer;
      const gainNode = _audioCtx.createGain();
      gainNode.gain.value = Math.max(0, Math.min(1, vol));
      source.connect(gainNode);
      gainNode.connect(_audioCtx.destination);
      source.start(0);
    } catch (err) {
      console.warn('[NotificationManager] playSound failed:', err);
    }
  }

  /* ── In-app alert ───────────────────────────────────────────────────── */
  function _showInAppAlert(reminder) {
    if (!_prefs.notif_in_app) return;
    const el = document.getElementById('notifAlert');
    if (!el) return;

    const kind    = reminder.kind || 'reminder';
    const title   = kind === 'overdue' ? '⚠️ Overdue Task'
                  : kind === 'test'    ? '🔔 Test Notification'
                  :                      '🔔 Task Reminder';
    const dueTime = reminder.task_due_time
      ? ' — ' + _fmt12h(reminder.task_due_time) : '';
    const body    = kind === 'overdue'
      ? `<strong>${reminder.task_title}</strong> is past due and not yet completed.`
      : `<strong>${reminder.task_title}</strong>${dueTime}<br><small>Your task is scheduled now.</small>`;

    document.getElementById('notifAlertTitle').textContent = title;
    document.getElementById('notifAlertBody').innerHTML    = body;

    const openBtn = document.getElementById('notifAlertOpen');
    openBtn.dataset.taskId = reminder.task_id || 0;

    el.classList.remove('notif-hidden');
    el.classList.add('notif-visible');

    // Auto-dismiss after 30s
    const tid = setTimeout(() => _dismissInAppAlert(), 30_000);
    el._autoDismiss = tid;
  }

  function _dismissInAppAlert() {
    const el = document.getElementById('notifAlert');
    if (!el) return;
    clearTimeout(el._autoDismiss);
    el.classList.remove('notif-visible');
    el.classList.add('notif-hidden');
  }

  /* ── Browser notification ────────────────────────────────────────────── */
  function _fireBrowserNotification(reminder) {
    if (!_prefs.notif_browser) return;
    if (Notification.permission !== 'granted') return;

    const kind    = reminder.kind || 'reminder';
    const title   = kind === 'overdue' ? '⚠️ Overdue Task'
                  : kind === 'test'    ? '🔔 Test Notification'
                  : kind === 'summary' ? '📋 Daily Summary'
                  :                      '🔔 Daily Tracker';
    const dueTime = reminder.task_due_time ? ` — ${_fmt12h(reminder.task_due_time)}` : '';
    const body    = kind === 'overdue'
      ? `${reminder.task_title} is past due and not yet completed.`
      : kind === 'summary'
      ? reminder.task_title
      : `${reminder.task_title}${dueTime}\nYour task is scheduled now.`;

    const tag  = `dt-${kind}-${reminder.id || Date.now()}`;
    const notif = new Notification(title, {
      body,
      icon:      '/static/icons/icon-192.png',
      badge:     '/static/icons/icon-192.png',
      tag,
      timestamp: Date.now(),
      requireInteraction: kind === 'overdue',
    });

    notif.onclick = () => {
      window.focus();
      if (reminder.task_id) {
        window.location.href = `/tasks?highlight=${reminder.task_id}`;
      }
      notif.close();
    };

    // Auto-close after 8s
    setTimeout(() => notif.close(), 8_000);
  }

  /* ── Dispatch a reminder (browser notif + in-app + sound) ──────────── */
  async function dispatch(reminder) {
    if (!reminder) return;
    // Skip overdue if user disabled
    if (reminder.kind === 'overdue' && !_prefs.notif_overdue) return;
    _fireBrowserNotification(reminder);
    _showInAppAlert(reminder);
    await playSound(_prefs.volume);
    // Mark as sent on the server
    if (reminder.id) {
      try { await window.API.post(`/api/notifications/${reminder.id}/mark-sent`, {}); }
      catch (_) {}
    }
  }

  /* ── Polling ────────────────────────────────────────────────────────── */
  async function _poll() {
    try {
      const reminders = await window.API.get('/api/notifications/due');
      for (const r of reminders) {
        if (_seenIds.has(r.id)) continue;
        _seenIds.add(r.id);
        await dispatch(r);
      }
    } catch (_) {}
  }

  function _startPolling() {
    if (_pollTimer) clearInterval(_pollTimer);
    _pollTimer = setInterval(_poll, POLL_INTERVAL_MS);
    _poll(); // immediate first check
  }

  /* ── Test helpers ────────────────────────────────────────────────────── */
  async function testNotification() {
    try {
      const payload = await window.API.post('/api/notifications/test', {});
      await dispatch(payload);
      return true;
    } catch (_) { return false; }
  }

  async function testSound() {
    _userInteracted = true; // explicit user gesture
    await _initAudio();
    await playSound(_prefs.volume);
  }

  /* ── Daily summary ───────────────────────────────────────────────────── */
  async function showDailySummary() {
    if (!_prefs.notif_daily_summary) return;
    try {
      const s = await window.API.get('/api/notifications/daily-summary');
      const upcoming = s.upcoming.map(t => `${t.due_time} — ${t.title}`).join('\n');
      const body = `Today: ${s.total} tasks | ✅ ${s.completed} | ⏳ ${s.pending}\nCompletion: ${s.completion_pct}%\n\nNext:\n${upcoming || 'None'}`;
      _fireBrowserNotification({
        id: 0, task_id: 0, kind: 'summary',
        task_title: body, task_due_time: null,
      });
    } catch (_) {}
  }

  /* ── Format time helper ─────────────────────────────────────────────── */
  function _fmt12h(hhmm) {
    if (!hhmm) return '';
    const [h, m] = hhmm.split(':').map(Number);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12  = h % 12 || 12;
    return `${h12}:${String(m).padStart(2, '0')} ${ampm}`;
  }

  /* ── Init ───────────────────────────────────────────────────────────── */
  async function init() {
    _loadPrefsFromStorage();
    await _registerSW();
    await _loadPrefsFromServer();

    // Track user interaction to enable audio
    const markInteracted = () => { _userInteracted = true; };
    document.addEventListener('click',   markInteracted, { once: false, passive: true });
    document.addEventListener('keydown', markInteracted, { once: false, passive: true });

    // Wire in-app alert buttons
    const dismissBtn = document.getElementById('notifAlertDismiss');
    const openBtn    = document.getElementById('notifAlertOpen');
    if (dismissBtn) dismissBtn.addEventListener('click', _dismissInAppAlert);
    if (openBtn) {
      openBtn.addEventListener('click', () => {
        const tid = openBtn.dataset.taskId;
        if (tid && tid !== '0') window.location.href = `/tasks?highlight=${tid}`;
        _dismissInAppAlert();
      });
    }

    // Pre-load audio (no autoplay — just decode)
    _initAudio().catch(() => {});

    // Start polling
    _startPolling();
  }

  /* ── Public API ─────────────────────────────────────────────────────── */
  return {
    init,
    requestPermission,
    getPermissionStatus,
    dispatch,
    playSound,
    testNotification,
    testSound,
    showDailySummary,
    get prefs()  { return { ..._prefs }; },
    updatePrefs(patch) {
      Object.assign(_prefs, patch);
      _savePrefsToStorage();
    },
    markInteracted() { _userInteracted = true; },
  };
})();
