let charts = {};

function destroyCharts() {
  Object.values(charts).forEach(c => c && c.destroy());
  charts = {};
}

async function loadAnalytics() {
  const now = new Date();
  const data = await API.get(`/api/analytics?year=${now.getFullYear()}&month=${now.getMonth() + 1}`);

  document.getElementById('analyticsStats').innerHTML = `
    <div class="stat-card"><div class="stat-icon" style="background:#6366f1"><i class="fa-solid fa-list"></i></div><div class="stat-value">${data.total_tasks}</div><div class="stat-label">Total Tasks</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#22c55e"><i class="fa-solid fa-check"></i></div><div class="stat-value">${data.completed_tasks}</div><div class="stat-label">Completed</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#f59e0b"><i class="fa-regular fa-clock"></i></div><div class="stat-value">${data.pending_tasks}</div><div class="stat-label">Pending</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#ef4444"><i class="fa-solid fa-triangle-exclamation"></i></div><div class="stat-value">${data.overdue_tasks}</div><div class="stat-label">Overdue</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#0ea5e9"><i class="fa-solid fa-percent"></i></div><div class="stat-value">${data.completion_pct}%</div><div class="stat-label">Completion Rate</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#8b5cf6"><i class="fa-solid fa-fire"></i></div><div class="stat-value">${data.current_streak}</div><div class="stat-label">Current Streak</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#ec4899"><i class="fa-solid fa-trophy"></i></div><div class="stat-value">${data.longest_streak}</div><div class="stat-label">Longest Streak</div></div>
    <div class="stat-card"><div class="stat-icon" style="background:#14b8a6"><i class="fa-solid fa-star"></i></div><div class="stat-value" style="font-size:1rem;">${data.most_productive_category || '—'}</div><div class="stat-label">Top Category</div></div>
  `;

  destroyCharts();
  const days = Array.from({ length: data.charts.daily_completion_pct.length }, (_, i) => i + 1);

  charts.daily = new Chart(document.getElementById('dailyPctChart'), {
    type: 'line',
    data: { labels: days, datasets: [{ label: 'Completion %', data: data.charts.daily_completion_pct, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,.15)', fill: true, tension: .3 }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } },
  });

  charts.cp = new Chart(document.getElementById('completedPendingChart'), {
    type: 'doughnut',
    data: {
      labels: ['Completed', 'Pending/Overdue'],
      datasets: [{ data: [data.charts.completed_vs_pending.completed, data.charts.completed_vs_pending.pending], backgroundColor: ['#22c55e', '#f59e0b'] }],
    },
  });

  const catEntries = Object.entries(data.charts.category_distribution);
  charts.cat = new Chart(document.getElementById('categoryChart'), {
    type: 'pie',
    data: {
      labels: catEntries.map(e => e[0]),
      datasets: [{ data: catEntries.map(e => e[1]), backgroundColor: ['#6366f1', '#0ea5e9', '#22c55e', '#f97316', '#ec4899', '#eab308', '#64748b', '#8b5cf6'] }],
    },
  });

  charts.trend = new Chart(document.getElementById('weeklyTrendChart'), {
    type: 'bar',
    data: {
      labels: data.charts.weekly_trend.map(w => w.week),
      datasets: [{ label: 'Completion %', data: data.charts.weekly_trend.map(w => w.pct), backgroundColor: '#8b5cf6', borderRadius: 6 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } },
  });
}

document.addEventListener('DOMContentLoaded', () => loadAnalytics().catch(err => Toast(err.message, 'error')));
document.addEventListener('task:changed', () => loadAnalytics().catch(err => Toast(err.message, 'error')));
