const state = {
  tasks: [],
  filters: { q: '', status: 'All', priority: 'All', category: 'All' },
  sort: 'newest',
  theme: localStorage.getItem('trainingtrack-theme') || 'light',
  editingId: null,
};

const $ = (id) => document.getElementById(id);

const api = {
  async request(url, options = {}) {
    const response = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    const contentType = response.headers.get('content-type') || '';
    const body = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) throw new Error(body?.error || 'Something went wrong.');
    return body;
  },
  list() {
    const params = new URLSearchParams();
    Object.entries(state.filters).forEach(([key, value]) => value && value !== 'All' && params.set(key, value));
    return this.request(`/api/tasks?${params.toString()}`);
  },
  stats() { return this.request('/api/stats'); },
  create(payload) { return this.request('/api/tasks', { method: 'POST', body: JSON.stringify(payload) }); },
  update(id, payload) { return this.request(`/api/tasks/${id}`, { method: 'PUT', body: JSON.stringify(payload) }); },
  remove(id) { return this.request(`/api/tasks/${id}`, { method: 'DELETE' }); },
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;'
  }[char]));
}

function statusClass(status) {
  return status === 'Completed' ? 'done' : status === 'In Progress' ? 'progress' : 'pending';
}

function dueLabel(task) {
  if (!task.due_date) return '<span class="muted">No due date</span>';
  if (task.is_overdue) return `<span class="due overdue">Overdue · ${escapeHtml(task.due_date)}</span>`;
  return `<span class="due">Due ${escapeHtml(task.due_date)}</span>`;
}

function sortTasks(tasks) {
  const copy = [...tasks];
  if (state.sort === 'oldest') return copy.sort((a, b) => a.id - b.id);
  if (state.sort === 'priority') {
    const order = { High: 0, Medium: 1, Low: 2 };
    return copy.sort((a, b) => order[a.priority] - order[b.priority] || b.id - a.id);
  }
  if (state.sort === 'due') return copy.sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'));
  return copy;
}

function renderBoard() {
  const columns = {
    Pending: $('pendingList'),
    'In Progress': $('progressList'),
    Completed: $('doneList'),
  };
  Object.values(columns).forEach((node) => { node.innerHTML = ''; });
  const sorted = sortTasks(state.tasks);
  const counts = { Pending: 0, 'In Progress': 0, Completed: 0 };

  sorted.forEach((task) => {
    counts[task.status] += 1;
    const card = document.createElement('article');
    card.className = `task-card priority-${task.priority.toLowerCase()}`;
    card.innerHTML = `
      <div class="task-card-head"><div class="task-labels"><span class="priority-dot" aria-label="${escapeHtml(task.priority)} priority"></span><span class="category">${escapeHtml(task.category)}</span></div><button class="more-btn" aria-label="Task actions" data-action="edit" data-id="${task.id}">•••</button></div>
      <h3>${escapeHtml(task.title)}</h3><p>${escapeHtml(task.notes || 'No notes added yet.')}</p>
      <div class="task-card-footer">${dueLabel(task)}<span class="chip ${statusClass(task.status)}">${escapeHtml(task.status)}</span></div>
      <div class="task-card-actions"><button class="text-btn" data-action="edit" data-id="${task.id}">Edit</button><button class="text-btn danger" data-action="delete" data-id="${task.id}">Delete</button></div>`;
    columns[task.status].appendChild(card);
  });

  $('pendingCount').textContent = counts.Pending;
  $('progressCount').textContent = counts['In Progress'];
  $('doneCount').textContent = counts.Completed;
  ['Pending', 'In Progress', 'Completed'].forEach((status) => {
    const list = columns[status];
    if (!list.children.length) list.innerHTML = '<div class="empty-column">No tasks here</div>';
  });
}

function renderStats(stats) {
  $('totalCount').textContent = stats.total;
  $('doneStat').textContent = stats.completed;
  const active = stats.in_progress + stats.pending;
  $('activeStat').textContent = `${active} active`;
  $('activeStatDuplicate').textContent = active;
  $('overdueStat').textContent = stats.overdue;

  const completionRate = stats.total ? Math.round((stats.completed / stats.total) * 100) : 0;
  $('healthProgress').style.width = `${completionRate}%`;
  $('healthLabel').textContent = stats.total === 0 ? 'Getting started'
    : completionRate >= 75 ? 'On track'
    : completionRate >= 40 ? 'Building momentum' : 'In progress';
}

function populateCategories(categoriesInput) {
  const current = $('categoryFilter').value;
  const categories = [...new Set(categoriesInput)].sort();
  $('categoryFilter').innerHTML = '<option>All</option>' + categories.map((category) => `<option>${escapeHtml(category)}</option>`).join('');
  $('categoryFilter').value = categories.includes(current) ? current : 'All';
}

async function load() {
  setLoading(true);
  try {
    const [tasks, stats] = await Promise.all([api.list(), api.stats()]);
    state.tasks = tasks;
    renderBoard();
    renderStats(stats);
    populateCategories(stats.categories.map((item) => item.category));
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading) {
  $('app').classList.toggle('loading', isLoading);
  $('refreshBtn').classList.toggle('spinning', isLoading);
}

function openModal(task = null) {
  state.editingId = task?.id ?? null;
  $('modalTitle').textContent = task ? 'Edit task' : 'Create a new task';
  $('modalSubtitle').textContent = task ? 'Update details and save your changes.' : 'Add a task to your workspace.';
  $('taskId').value = task?.id || '';
  $('title').value = task?.title || '';
  $('category').value = task?.category || 'Frontend';
  $('priority').value = task?.priority || 'Medium';
  $('status').value = task?.status || 'Pending';
  $('dueDate').value = task?.due_date || '';
  $('notes').value = task?.notes || '';
  $('modal').classList.remove('hidden');
  setTimeout(() => $('title').focus(), 0);
}

function closeModal() {
  $('modal').classList.add('hidden');
  state.editingId = null;
  $('taskForm').reset();
  $('category').value = 'Frontend';
  $('priority').value = 'Medium';
  $('status').value = 'Pending';
}

async function saveTask(event) {
  event.preventDefault();
  const payload = { title: $('title').value.trim(), category: $('category').value, priority: $('priority').value,
    status: $('status').value, due_date: $('dueDate').value, notes: $('notes').value.trim() };
  try {
    $('saveBtn').disabled = true;
    if (state.editingId) {
      await api.update(state.editingId, payload);
      showToast('Task updated successfully.');
    } else {
      await api.create(payload);
      showToast('Task created successfully.');
    }
    closeModal();
    await load();
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    $('saveBtn').disabled = false;
  }
}

async function deleteTask(id) {
  const task = state.tasks.find((item) => item.id === id);
  if (!task || !confirm(`Delete “${task.title}”?`)) return;
  try {
    await api.remove(id);
    showToast('Task deleted.');
    await load();
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function handleTaskAction(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const id = Number(button.dataset.id);
  const task = state.tasks.find((item) => item.id === id);
  if (button.dataset.action === 'edit') openModal(task);
  if (button.dataset.action === 'delete') deleteTask(id);
}

function applyFilters() {
  state.filters = { q: $('search').value.trim(), status: $('statusFilter').value,
    priority: $('priorityFilter').value, category: $('categoryFilter').value };
  load();
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.setAttribute('role', 'status');
  toast.innerHTML = `<strong>${type === 'error' ? 'Action failed' : 'Done'}</strong><span>${escapeHtml(message)}</span>`;
  $('toastStack').appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => toast.remove(), 3200);
}

function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = state.theme;
  localStorage.setItem('trainingtrack-theme', state.theme);
  $('themeBtn').setAttribute('aria-label', `Switch to ${state.theme === 'dark' ? 'light' : 'dark'} mode`);
}

function initialise() {
  document.documentElement.dataset.theme = state.theme;
  $('themeBtn').addEventListener('click', toggleTheme);
  $('addBtn').addEventListener('click', () => openModal());
  $('closeBtn').addEventListener('click', closeModal);
  $('cancelBtn').addEventListener('click', closeModal);
  $('taskForm').addEventListener('submit', saveTask);
  $('taskGrid').addEventListener('click', handleTaskAction);
  $('refreshBtn').addEventListener('click', load);
  $('search').addEventListener('keydown', (event) => { if (event.key === 'Enter') applyFilters(); });
  $('searchBtn').addEventListener('click', applyFilters);
  $('statusFilter').addEventListener('change', applyFilters);
  $('priorityFilter').addEventListener('change', applyFilters);
  $('categoryFilter').addEventListener('change', applyFilters);
  $('sortBy').addEventListener('change', () => { state.sort = $('sortBy').value; renderBoard(); });
  $('modal').addEventListener('click', (event) => { if (event.target === $('modal')) closeModal(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && !$('modal').classList.contains('hidden')) closeModal(); });
  load();
}

document.addEventListener('DOMContentLoaded', initialise);
