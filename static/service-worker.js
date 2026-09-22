/* Daily Tracker Service Worker — handles push events and offline caching */

const CACHE_NAME = 'daily-tracker-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/notifications.js',
  '/static/manifest.json',
];

// ─── Install: cache static shell ─────────────────────────────────────────────
self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
});

// ─── Activate: clean old caches ──────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ─── Fetch: network-first, cache fallback ────────────────────────────────────
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

// ─── Push: receive VAPID push and show notification ──────────────────────────
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) {}

  const taskId    = data.task_id || 0;
  const kind      = data.kind || 'reminder';
  const title     = kind === 'overdue'  ? '⚠️ Overdue Task'
                  : kind === 'summary'  ? '📋 Daily Summary'
                  : kind === 'test'     ? '🔔 Test Notification'
                  :                       '🔔 Daily Tracker';
  const body      = data.body  || data.task_title || 'You have a task reminder.';
  const tag       = `dt-${kind}-${taskId}-${Date.now()}`;
  const taskUrl   = taskId ? `/tasks?highlight=${taskId}` : '/';

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon:      '/static/icons/icon-192.png',
      badge:     '/static/icons/icon-192.png',
      tag,
      timestamp: Date.now(),
      requireInteraction: kind === 'overdue',
      data: { taskId, taskUrl, kind },
      actions: [
        { action: 'open',    title: 'Open Task' },
        { action: 'dismiss', title: 'Dismiss'   },
      ],
    })
  );
});

// ─── Notification click ───────────────────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const taskUrl = (event.notification.data && event.notification.data.taskUrl) || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Focus existing open window if possible
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus();
          client.navigate(taskUrl);
          return;
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(taskUrl);
    })
  );
});
