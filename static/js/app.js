/* Shared app-wide logic: theme, sidebar, task modal, toasts, reminders.
   Page-specific scripts (tasks.js, calendar.js, analytics.js, habits.js) hook into
   window.TaskModal / window.Toast / window.API for their own rendering. */

const API = {
  async get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Request failed');
    return r.json();
  },
  async post(url, body) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Request failed');
    return r.json();
  },
  async put(url, body) {
    const r = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Request failed');
    return r.json();
  },
  async del(url) {
    const r = await fetch(url, { method: 'DELETE' });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Request failed');
    return r.json();
  },
};
window.API = API;

/* ---------- Toasts ---------- */
function toast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info';
  el.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, 3000);
}
window.Toast = toast;

/* ---------- Theme ---------- */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const icon = document.querySelector('#themeToggleBtn i');
  if (icon) icon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
}
function initTheme() {
  const saved = localStorage.getItem('theme') || 'light';
  applyTheme(saved);
  const btn = document.getElementById('themeToggleBtn');
  if (btn) {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', next);
      applyTheme(next);
    });
  }
}

/* ---------- Sidebar (mobile) ---------- */
function initSidebar() {
  const btn = document.getElementById('hamburgerBtn');
  const sidebar = document.getElementById('sidebar');
  if (!btn || !sidebar) return;
  btn.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 900 && sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

/* ---------- Categories cache ---------- */
let categoriesCache = [];
async function loadCategories() {
  categoriesCache = await API.get('/api/categories');
  const select = document.getElementById('taskCategory');
  if (select) {
    select.innerHTML = categoriesCache.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  }
  return categoriesCache;
}
window.getCategories = () => categoriesCache;

/* ---------- Task Modal ---------- */
const TaskModal = {
  overlay: null, form: null, editingId: null, selectedDays: new Set(),
  onSaved: null, // optional callback(task) set by page scripts

  init() {
    this.overlay = document.getElementById('taskModalOverlay');
    this.form = document.getElementById('taskForm');
    if (!this.overlay || !this.form) return;

    document.getElementById('openAddTaskBtn').addEventListener('click', () => this.openForAdd());
    document.getElementById('closeTaskModalBtn').addEventListener('click', () => this.close());
    document.getElementById('cancelTaskBtn').addEventListener('click', () => this.close());
    this.overlay.addEventListener('click', (e) => { if (e.target === this.overlay) this.close(); });

    document.getElementById('taskRecurrence').addEventListener('change', (e) => {
      document.getElementById('customDaysWrap').hidden = e.target.value !== 'custom';
    });

    document.querySelectorAll('#weekdayPicker button').forEach(b => {
      b.addEventListener('click', () => {
        const d = b.dataset.day;
        b.classList.toggle('selected');
        if (b.classList.contains('selected')) this.selectedDays.add(d); else this.selectedDays.delete(d);
      });
    });

    this.form.addEventListener('submit', (e) => this.handleSubmit(e));
  },

  openForAdd(prefillDate) {
    this.editingId = null;
    document.getElementById('taskModalTitle').textContent = 'Add New Task';
    document.getElementById('saveTaskBtn').textContent = 'Add Task';
    this.form.reset();
    document.getElementById('taskId').value = '';
    document.getElementById('taskDate').value = prefillDate || new Date().toISOString().slice(0, 10);
    document.getElementById('customDaysWrap').hidden = true;
    this.selectedDays = new Set();
    document.querySelectorAll('#weekdayPicker button').forEach(b => b.classList.remove('selected'));
    this.overlay.classList.add('open');
  },

  openForEdit(task) {
    this.editingId = task.id;
    document.getElementById('taskModalTitle').textContent = 'Edit Task';
    document.getElementById('saveTaskBtn').textContent = 'Save Changes';
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskCategory').value = task.category_id || '';
    document.getElementById('taskPriority').value = task.priority;
    document.getElementById('taskDate').value = task.due_date || '';
    document.getElementById('taskTime').value = task.due_time || '';
    document.getElementById('taskTimeBlock').value = task.time_block || 'Morning';
    document.getElementById('taskRecurrence').value = task.recurrence === 'none' ? 'none' : task.recurrence;
    document.getElementById('customDaysWrap').hidden = task.recurrence !== 'custom';
    document.getElementById('taskReminder').value = task.reminder_time || '';
    document.getElementById('taskNotes').value = task.notes || '';
    this.overlay.classList.add('open');
  },

  close() { this.overlay.classList.remove('open'); },

  async handleSubmit(e) {
    e.preventDefault();
    const payload = {
      title: document.getElementById('taskTitle').value,
      category_id: document.getElementById('taskCategory').value || null,
      priority: document.getElementById('taskPriority').value,
      due_date: document.getElementById('taskDate').value,
      due_time: document.getElementById('taskTime').value || null,
      time_block: document.getElementById('taskTimeBlock').value,
      recurrence: document.getElementById('taskRecurrence').value,
      recurrence_days: Array.from(this.selectedDays),
      reminder_time: document.getElementById('taskReminder').value || null,
      notes: document.getElementById('taskNotes').value,
    };
    try {
      let task;
      if (this.editingId) {
        task = await API.put(`/api/tasks/${this.editingId}`, payload);
        toast('Task updated', 'success');
      } else {
        task = await API.post('/api/tasks', payload);
        toast('Task added', 'success');
      }
      this.close();
      if (this.onSaved) this.onSaved(task);
      document.dispatchEvent(new CustomEvent('task:changed'));
    } catch (err) {
      toast(err.message || 'Something went wrong', 'error');
    }
  },
};
window.TaskModal = TaskModal;

/* ---------- Confirm delete modal ---------- */
const ConfirmDelete = {
  pendingId: null,
  init() {
    this.overlay = document.getElementById('confirmModalOverlay');
    document.getElementById('cancelDeleteBtn').addEventListener('click', () => this.close());
    this.overlay.addEventListener('click', (e) => { if (e.target === this.overlay) this.close(); });
    document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
      if (!this.pendingId) return;
      try {
        await API.del(`/api/tasks/${this.pendingId}`);
        toast('Task deleted', 'success');
        document.dispatchEvent(new CustomEvent('task:changed'));
      } catch (err) {
        toast(err.message || 'Delete failed', 'error');
      }
      this.close();
    });
  },
  open(id) { this.pendingId = id; this.overlay.classList.add('open'); },
  close() { this.pendingId = null; this.overlay.classList.remove('open'); },
};
window.ConfirmDelete = ConfirmDelete;

/* ---------- Bell icon — show upcoming reminders dropdown ---------- */
async function loadReminderBadge() {
  try {
    const reminders = await API.get('/api/notifications/upcoming');
    const badge = document.getElementById('reminderBadge');
    if (badge) {
      if (reminders.length > 0) { badge.hidden = false; badge.textContent = reminders.length; }
      else badge.hidden = true;
    }
    const panel = document.getElementById('reminderPanel');
    if (panel) {
      panel.innerHTML = reminders.length
        ? reminders.map(r => {
            const t = new Date(r.remind_at + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const kindIcon = r.kind === 'overdue' ? '⚠️' : '🔔';
            return `<div class="reminder-item"><span class="reminder-time">${kindIcon} ${t}</span>${r.task_title}</div>`;
          }).join('')
        : `<div class="reminder-item">No upcoming reminders</div>`;
    }
  } catch (_) {}
}

function initReminderPanel() {
  const btn = document.getElementById('reminderBtn');
  if (!btn) return;
  let panel = document.getElementById('reminderPanel');
  if (!panel) {
    panel = document.createElement('div');
    panel.className = 'reminder-panel';
    panel.id = 'reminderPanel';
    btn.parentElement.style.position = 'relative';
    btn.parentElement.appendChild(panel);
  }
  btn.addEventListener('click', () => { panel.classList.toggle('open'); });
  document.addEventListener('click', (e) => {
    if (!panel.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
      panel.classList.remove('open');
    }
  });
  loadReminderBadge();
  setInterval(loadReminderBadge, 60_000);
}

/* ---------- Helpers used across pages ---------- */
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}
function categoryColor(id) {
  const c = categoriesCache.find(c => c.id === id);
  return c ? c.color : '#64748b';
}
window.formatDate = formatDate;
window.categoryColor = categoryColor;

/* ---------- Init on every page ---------- */
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  initSidebar();
  TaskModal.init();
  ConfirmDelete.init();
  initReminderPanel();
  await loadCategories();
  document.dispatchEvent(new CustomEvent('categories:ready'));

  // ── Notification system ──────────────────────────────────────────────
  if (window.NotificationManager) {
    await window.NotificationManager.init();
  }
});
