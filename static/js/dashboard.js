function greetingText() {
  const h = new Date().getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}

function renderTaskItem(t) {
  const overdue = t.is_overdue ? '<span class="overdue-tag"><i class="fa-solid fa-triangle-exclamation"></i> Overdue</span>' : '';
  return `
    <div class="task-item ${t.status === 'completed' ? 'completed' : ''}" data-id="${t.id}">
      <button class="task-check ${t.status === 'completed' ? 'checked' : ''}" data-action="toggle">
        ${t.status === 'completed' ? '<i class="fa-solid fa-check"></i>' : ''}
      </button>
      <div class="task-info">
        <div class="task-title">${t.title}</div>
        <div class="task-meta">
          <span class="chip priority-${t.priority}">${t.priority}</span>
          ${t.category ? `<span class="chip outline">${t.category}</span>` : ''}
          ${t.due_time ? `<span class="chip outline"><i class="fa-regular fa-clock"></i> ${t.due_time}</span>` : ''}
          ${overdue}
        </div>
      </div>
      <div class="task-actions">
        <button data-action="edit" title="Edit"><i class="fa-solid fa-pen"></i></button>
        <button data-action="delete" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    </div>`;
}

function bindTaskListEvents(container, tasksById) {
  container.onclick = async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const item = e.target.closest('.task-item');
    const id = item.dataset.id;
    const task = tasksById[id];
    const action = btn.dataset.action;
    if (action === 'toggle') {
      try {
        if (task.status === 'completed') await API.post(`/api/tasks/${id}/uncomplete`);
        else await API.post(`/api/tasks/${id}/complete`);
        document.dispatchEvent(new CustomEvent('task:changed'));
      } catch (err) { Toast(err.message, 'error'); }
    } else if (action === 'edit') {
      TaskModal.openForEdit(task);
    } else if (action === 'delete') {
      ConfirmDelete.open(id);
    }
  };
}

let weekChartInstance = null;

async function loadDashboard() {
  const [summary, todayTasks] = await Promise.all([
    API.get('/api/dashboard'),
    API.get(`/api/tasks?date=${new Date().toISOString().slice(0, 10)}`),
  ]);

  document.getElementById('greetingTitle').textContent = `${greetingText()}, Falgun 👋`;
  document.getElementById('currentStreak').textContent = summary.current_streak;
  document.getElementById('dashDailyPct').textContent = summary.daily_completion_pct + '%';
  document.getElementById('dashMonthlyPct').textContent = summary.monthly_completion_pct + '%';

  document.getElementById('statsGrid').innerHTML = `
    <div class="stat-card"><div class="stat-icon" style="background:#6366f1"><i class="fa-solid fa-list-check"></i></div><div class="stat-value">${summary.completed_today}</div><div class="stat-label">Completed Today</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#f59e0b"><i class="fa-regular fa-clock"></i></div><div class="stat-value">${summary.pending_today}</div><div class="stat-label">Pending Today</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#22c55e"><i class="fa-solid fa-check-double"></i></div><div class="stat-value">${summary.total_completed}</div><div class="stat-label">Total Completed</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#ef4444"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="stat-value">${summary.overdue_tasks}</div><div class="stat-label">Overdue Tasks</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#0ea5e9"><i class="fa-solid fa-forward"></i></div><div class="stat-value">${summary.upcoming_tasks}</div><div class="stat-label">Upcoming (7d)</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#8b5cf6"><i class="fa-solid fa-trophy"></i></div><div class="stat-value">${summary.longest_streak}</div><div class="stat-label">Longest Streak</div></div>
  `;

  document.getElementById('dashProgressFill').style.width = summary.daily_completion_pct + '%';
  document.getElementById('dashCompletedCount').textContent = `${summary.completed_today} completed`;
  document.getElementById('dashPendingCount').textContent = `${summary.pending_today} pending`;

  const listEl = document.getElementById('dashTaskList');
  if (todayTasks.length === 0) {
    listEl.innerHTML = `<div class="empty-state"><i class="fa-regular fa-calendar-check"></i>No tasks for today yet. Add one to get started!</div>`;
  } else {
    const tasksById = {};
    todayTasks.forEach(t => tasksById[t.id] = t);
    listEl.innerHTML = todayTasks.map(renderTaskItem).join('');
    bindTaskListEvents(listEl, tasksById);
  }

  // simple week chart: last 7 days completion count from history
  try {
    const history = await API.get('/api/history?days=7');
    const days = [];
    const counts = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      days.push(d.toLocaleDateString(undefined, { weekday: 'short' }));
      const entry = history.find(h => h.date === key);
      counts.push(entry ? entry.completed.length : 0);
    }
    const ctx = document.getElementById('weekChart');
    if (weekChartInstance) weekChartInstance.destroy();
    weekChartInstance = new Chart(ctx, {
      type: 'bar',
      data: { labels: days, datasets: [{ label: 'Completed', data: counts, backgroundColor: '#6366f1', borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  } catch (e) { /* chart is best-effort */ }
}

document.addEventListener('DOMContentLoaded', () => {
  TaskModal.onSaved = () => {};
  loadDashboard().catch(err => Toast(err.message, 'error'));
});
document.addEventListener('task:changed', () => loadDashboard().catch(err => Toast(err.message, 'error')));
