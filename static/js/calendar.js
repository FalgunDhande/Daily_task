let fcCalendar = null;
let currentDayDate = null;

function renderDayTaskItem(t) {
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

async function openDayModal(dateStr) {
  currentDayDate = dateStr;
  const overlay = document.getElementById('dayModalOverlay');
  const titleEl = document.getElementById('dayModalTitle');
  const listEl = document.getElementById('dayModalTaskList');
  titleEl.textContent = formatDate(dateStr);
  listEl.innerHTML = `<div class="loader"><div class="spinner"></div>Loading...</div>`;
  overlay.classList.add('open');

  const tasks = await API.get(`/api/calendar/day/${dateStr}`);
  const tasksById = {};
  tasks.forEach(t => tasksById[t.id] = t);

  listEl.innerHTML = tasks.length
    ? tasks.map(renderDayTaskItem).join('')
    : `<div class="empty-state"><i class="fa-regular fa-calendar"></i>No tasks for this day.</div>`;

  listEl.onclick = async (e) => {
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
        openDayModal(dateStr);
      } catch (err) { Toast(err.message, 'error'); }
    } else if (action === 'edit') {
      TaskModal.openForEdit(task);
    } else if (action === 'delete') {
      ConfirmDelete.open(id);
    }
  };
}

document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('calendarEl');
  fcCalendar = new FullCalendar.Calendar(el, {
    initialView: 'dayGridMonth',
    headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' },
    height: 'auto',
    events: async (info, success, failure) => {
      try {
        const events = await API.get(`/api/calendar?start=${info.startStr.slice(0, 10)}&end=${info.endStr.slice(0, 10)}`);
        success(events);
      } catch (err) { failure(err); }
    },
    dateClick: (info) => openDayModal(info.dateStr),
    eventClick: (info) => openDayModal(info.event.startStr.slice(0, 10)),
  });
  fcCalendar.render();

  document.getElementById('closeDayModalBtn').addEventListener('click', () => {
    document.getElementById('dayModalOverlay').classList.remove('open');
  });
  document.getElementById('dayModalOverlay').addEventListener('click', (e) => {
    if (e.target.id === 'dayModalOverlay') e.target.classList.remove('open');
  });
  document.getElementById('addTaskForDayBtn').addEventListener('click', () => {
    document.getElementById('dayModalOverlay').classList.remove('open');
    TaskModal.openForAdd(currentDayDate);
  });
});

document.addEventListener('task:changed', () => {
  if (fcCalendar) fcCalendar.refetchEvents();
});
