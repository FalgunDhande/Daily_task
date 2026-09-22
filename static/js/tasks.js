let allTasksById = {};

function renderFullTaskItem(t) {
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
          ${t.due_date ? `<span class="chip outline"><i class="fa-regular fa-calendar"></i> ${formatDate(t.due_date)}</span>` : ''}
          ${t.due_time ? `<span class="chip outline"><i class="fa-regular fa-clock"></i> ${t.due_time}</span>` : ''}
          ${t.recurrence && t.recurrence !== 'none' ? `<span class="chip outline"><i class="fa-solid fa-repeat"></i> ${t.recurrence}</span>` : ''}
          ${overdue}
        </div>
      </div>
      <div class="task-actions">
        <button data-action="edit" title="Edit"><i class="fa-solid fa-pen"></i></button>
        <button data-action="delete" title="Delete"><i class="fa-solid fa-trash"></i></button>
      </div>
    </div>`;
}

function buildQuery() {
  const params = new URLSearchParams();
  const search = document.getElementById('searchInput').value.trim();
  const category = document.getElementById('filterCategory').value;
  const priority = document.getElementById('filterPriority').value;
  const status = document.getElementById('filterStatus').value;
  const overdue = document.getElementById('filterOverdue').value;
  const sort = document.getElementById('sortBy').value;
  if (search) params.set('search', search);
  if (category) params.set('category_id', category);
  if (priority) params.set('priority', priority);
  if (status) params.set('status', status);
  if (overdue) params.set('overdue', overdue);
  if (sort) params.set('sort', sort);
  return params.toString();
}

async function loadTasks() {
  const container = document.getElementById('taskListContainer');
  const tasks = await API.get(`/api/tasks?${buildQuery()}`);
  document.getElementById('taskCountHeading').textContent = `${tasks.length} Task${tasks.length === 1 ? '' : 's'}`;

  allTasksById = {};
  tasks.forEach(t => allTasksById[t.id] = t);

  if (tasks.length === 0) {
    container.innerHTML = `<div class="empty-state"><i class="fa-solid fa-inbox"></i>No tasks match your filters.</div>`;
    return;
  }
  container.innerHTML = tasks.map(renderFullTaskItem).join('');

  container.onclick = async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const item = e.target.closest('.task-item');
    const id = item.dataset.id;
    const task = allTasksById[id];
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

  // ── Highlight task from notification click (?highlight=taskId) ──────
  _highlightFromUrl();
}

function _highlightFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const highlightId = params.get('highlight');
  if (!highlightId) return;
  const el = document.querySelector(`.task-item[data-id="${highlightId}"]`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('task-highlight');
  setTimeout(() => el.classList.remove('task-highlight'), 3000);
  // Clean URL without reload
  const url = new URL(window.location);
  url.searchParams.delete('highlight');
  window.history.replaceState({}, '', url);
}

function populateCategoryFilter() {
  const select = document.getElementById('filterCategory');
  const cats = getCategories();
  select.innerHTML = '<option value="">All Categories</option>' + cats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
}

document.addEventListener('categories:ready', populateCategoryFilter);

['searchInput', 'filterCategory', 'filterPriority', 'filterStatus', 'filterOverdue', 'sortBy'].forEach(id => {
  document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById(id);
    const evt = el.tagName === 'SELECT' ? 'change' : 'input';
    el.addEventListener(evt, () => loadTasks().catch(err => Toast(err.message, 'error')));
  });
});

document.addEventListener('DOMContentLoaded', () => loadTasks().catch(err => Toast(err.message, 'error')));
document.addEventListener('task:changed', () => loadTasks().catch(err => Toast(err.message, 'error')));
