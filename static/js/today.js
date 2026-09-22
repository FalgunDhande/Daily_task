const TIME_BLOCKS = ['Morning', 'Afternoon', 'Evening', 'Night'];
const BLOCK_ICONS = { Morning: 'fa-sun', Afternoon: 'fa-cloud-sun', Evening: 'fa-cloud-moon', Night: 'fa-moon' };

function renderTodayItem(t) {
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
        </div>
      </div>
      <div class="task-actions">
        <button data-action="edit" title="Edit"><i class="fa-solid fa-pen"></i></button>
        <button data-action="delete" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    </div>`;
}

async function loadToday() {
  const today = new Date().toISOString().slice(0, 10);
  const tasks = await API.get(`/api/tasks?date=${today}`);
  const dateObj = new Date(today + 'T00:00:00');
  document.getElementById('todayDateHeading').textContent = dateObj.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' });

  const completed = tasks.filter(t => t.status === 'completed').length;
  const pct = tasks.length ? Math.round(completed / tasks.length * 100) : 0;
  document.getElementById('todayProgressFill').style.width = pct + '%';

  const tasksById = {};
  tasks.forEach(t => tasksById[t.id] = t);

  const container = document.getElementById('todayBlocks');
  if (tasks.length === 0) {
    container.innerHTML = `<div class="empty-state"><i class="fa-regular fa-calendar-check"></i>Nothing scheduled today. Add a task to get going.</div>`;
    return;
  }

  container.innerHTML = TIME_BLOCKS.map(block => {
    const items = tasks.filter(t => (t.time_block || 'Morning') === block);
    if (items.length === 0) return '';
    return `
      <div class="time-block">
        <h4><i class="fa-solid ${BLOCK_ICONS[block]}"></i> ${block}</h4>
        <div class="task-list">${items.map(renderTodayItem).join('')}</div>
      </div>`;
  }).join('');

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

document.addEventListener('DOMContentLoaded', () => loadToday().catch(err => Toast(err.message, 'error')));
document.addEventListener('task:changed', () => loadToday().catch(err => Toast(err.message, 'error')));
