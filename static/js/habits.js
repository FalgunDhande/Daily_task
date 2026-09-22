let currentMonth = new Date().getMonth() + 1;
let currentYear = new Date().getFullYear();

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

async function loadHabits() {
  const wrap = document.getElementById('habitTableWrap');
  const habits = await API.get(`/api/habits?year=${currentYear}&month=${currentMonth}`);
  const total = daysInMonth(currentYear, currentMonth);
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === currentYear && today.getMonth() + 1 === currentMonth;

  if (habits.length === 0) {
    wrap.innerHTML = `<div class="empty-state"><i class="fa-solid fa-repeat"></i>No habits yet. Add your first one!</div>`;
    return;
  }

  const dayHeaders = Array.from({ length: total }, (_, i) => `<th>${i + 1}</th>`).join('');
  const rows = habits.map(h => {
    const cells = Array.from({ length: total }, (_, i) => {
      const day = i + 1;
      const done = h.days[day];
      const future = isCurrentMonth && day > today.getDate();
      return `<td><button class="habit-cell ${done ? 'done' : ''} ${future ? '' : 'clickable'}"
                data-habit="${h.id}" data-day="${day}" ${future ? 'disabled' : ''}>
                ${done ? '<i class="fa-solid fa-check"></i>' : ''}
              </button></td>`;
    }).join('');
    return `<tr>
      <td>${h.name}<div class="habit-streak">🔥 ${h.current_streak}d streak · best ${h.longest_streak}d</div></td>
      ${cells}
    </tr>`;
  }).join('');

  wrap.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <button class="btn btn-ghost btn-sm" id="prevMonthBtn"><i class="fa-solid fa-chevron-left"></i></button>
      <strong>${new Date(currentYear, currentMonth - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</strong>
      <button class="btn btn-ghost btn-sm" id="nextMonthBtn"><i class="fa-solid fa-chevron-right"></i></button>
    </div>
    <table class="habit-table">
      <thead><tr><th>Habit</th>${dayHeaders}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;

  document.getElementById('prevMonthBtn').addEventListener('click', () => {
    currentMonth--; if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    loadHabits();
  });
  document.getElementById('nextMonthBtn').addEventListener('click', () => {
    currentMonth++; if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    loadHabits();
  });

  wrap.querySelectorAll('.habit-cell.clickable').forEach(btn => {
    btn.addEventListener('click', async () => {
      const habitId = btn.dataset.habit;
      const day = btn.dataset.day;
      const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      try {
        await API.post(`/api/habits/${habitId}/toggle`, { date: dateStr });
        loadHabits();
      } catch (err) { Toast(err.message, 'error'); }
    });
  });
}

function initHabitModal() {
  const overlay = document.getElementById('habitModalOverlay');
  document.getElementById('openAddHabitBtn').addEventListener('click', () => overlay.classList.add('open'));
  document.getElementById('closeHabitModalBtn').addEventListener('click', () => overlay.classList.remove('open'));
  document.getElementById('cancelHabitBtn').addEventListener('click', () => overlay.classList.remove('open'));
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('open'); });

  document.getElementById('habitForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await API.post('/api/habits', {
        name: document.getElementById('habitName').value,
        target_frequency: document.getElementById('habitFrequency').value,
        target_count: parseInt(document.getElementById('habitTargetCount').value, 10),
        goal: document.getElementById('habitGoal').value,
      });
      Toast('Habit added', 'success');
      overlay.classList.remove('open');
      document.getElementById('habitForm').reset();
      loadHabits();
    } catch (err) { Toast(err.message, 'error'); }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initHabitModal();
  loadHabits().catch(err => Toast(err.message, 'error'));
});
