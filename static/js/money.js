/* Money Management Module Frontend Logic */

(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────────────────────
  const state = {
    currentView: 'dashboard',
    categories: [],
    paymentMethods: [],
    selectedDate: new Date().toISOString().split('T')[0],
    calYear: new Date().getFullYear(),
    calMonth: new Date().getMonth() + 1,
    budgetYear: new Date().getFullYear(),
    budgetMonth: new Date().getMonth() + 1,
    analyticsYear: new Date().getFullYear(),
    analyticsMonth: new Date().getMonth() + 1,
    txns: {
      page: 1,
      per_page: 25,
      total: 0,
      pages: 1,
    },
    charts: {},
  };

  // ── Formatters ────────────────────────────────────────────────────────────
  function formatINR(val) {
    const num = Number(val) || 0;
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatShortDate(dStr) {
    if (!dStr) return '';
    const [y, m, d] = dStr.split('-');
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]} ${y}`;
  }

  const MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  // ── Initialization ────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async () => {
    // Only init if money tabs exist on page
    if (!document.getElementById('moneyTabs')) return;

    await loadInitialData();
    initTabNavigation();
    initQuickActions();
    initModals();
    initTransactionsView();
    initDailyView();
    initCalendarView();
    initBudgetsView();
    initGoalsView();
    initRecurringView();
    initAnalyticsView();

    // Default load
    switchView('dashboard');
  });

  async function loadInitialData() {
    try {
      const [cats, pms] = await Promise.all([
        API.get('/api/money/categories'),
        API.get('/api/money/payment-methods'),
      ]);
      state.categories = cats;
      state.paymentMethods = pms;
      populateCategorySelects();
      populatePaymentSelects();
    } catch (err) {
      console.error('Failed to load money metadata:', err);
    }
  }

  function populateCategorySelects() {
    const filter = document.getElementById('txnCategoryFilter');
    if (filter) {
      filter.innerHTML = '<option value="">All Categories</option>' +
        state.categories.map(c => `<option value="${c.id}">${c.name} (${c.type})</option>`).join('');
    }
    const txnSelect = document.getElementById('txnCategory');
    if (txnSelect) {
      txnSelect.innerHTML = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }
    const recSelect = document.getElementById('recurringCategory');
    if (recSelect) {
      recSelect.innerHTML = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }
  }

  function populatePaymentSelects() {
    const filter = document.getElementById('txnPaymentFilter');
    if (filter) {
      filter.innerHTML = '<option value="">All Payments</option>' +
        state.paymentMethods.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
    const txnSelect = document.getElementById('txnPayment');
    if (txnSelect) {
      txnSelect.innerHTML = state.paymentMethods.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
    const recSelect = document.getElementById('recurringPayment');
    if (recSelect) {
      recSelect.innerHTML = state.paymentMethods.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
  }

  // ── Tab Navigation ────────────────────────────────────────────────────────
  function initTabNavigation() {
    const tabs = document.querySelectorAll('.money-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.getAttribute('data-view');
        switchView(view);
      });
    });
  }

  function switchView(viewName) {
    state.currentView = viewName;
    document.querySelectorAll('.money-tab').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-view') === viewName);
    });
    document.querySelectorAll('.money-view').forEach(v => {
      v.classList.toggle('active', v.id === `view-${viewName}`);
    });

    switch (viewName) {
      case 'dashboard':
        loadDashboard();
        break;
      case 'daily':
        loadDailySpending();
        break;
      case 'transactions':
        loadTransactions();
        break;
      case 'calendar':
        loadCalendar();
        break;
      case 'budgets':
        loadBudgets();
        break;
      case 'goals':
        loadGoals();
        break;
      case 'recurring':
        loadRecurring();
        break;
      case 'analytics':
        loadAnalytics();
        break;
    }
  }

  // ── Quick Actions ─────────────────────────────────────────────────────────
  function initQuickActions() {
    document.getElementById('quickAddExpense')?.addEventListener('click', () => openTxnModal('expense'));
    document.getElementById('quickAddIncome')?.addEventListener('click', () => openTxnModal('income'));
    document.getElementById('quickAddBudget')?.addEventListener('click', () => openBudgetModal());
    document.getElementById('quickAddGoal')?.addEventListener('click', () => openGoalModal());
  }

  // ── 1. Dashboard View ─────────────────────────────────────────────────────
  async function loadDashboard() {
    try {
      const [summary, limit, insightsData, budgetData] = await Promise.all([
        API.get('/api/money/summary'),
        API.get('/api/money/daily-limit'),
        API.get('/api/money/insights'),
        API.get('/api/money/budgets'),
      ]);

      renderDashboardOverview(summary);
      renderDashboardStats(summary);
      renderDashboardBudgetProgress(budgetData, summary);
      renderDashboardDailyLimit(limit);
      renderDashboardInsights(insightsData.insights);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  }

  function renderDashboardOverview(s) {
    const header = document.getElementById('moneyOverviewHeader');
    if (!header) return;
    header.innerHTML = `
      <div class="moh-title">
        <h2>Money Overview</h2>
        <p>${s.month_name} ${s.year}</p>
      </div>
      <div class="moh-figures">
        <div class="moh-fig">
          <div class="label">Total Income</div>
          <div class="val val-income">${formatINR(s.month_income)}</div>
        </div>
        <div class="moh-fig">
          <div class="label">Total Expenses</div>
          <div class="val val-expense">${formatINR(s.month_expenses)}</div>
        </div>
        <div class="moh-fig">
          <div class="label">Net Remaining</div>
          <div class="val val-balance">${formatINR(s.remaining)}</div>
        </div>
      </div>
    `;
  }

  function renderDashboardStats(s) {
    const grid = document.getElementById('moneyStatsGrid');
    if (!grid) return;
    grid.innerHTML = `
      <div class="card stat-card">
        <div class="stat-icon red"><i class="fa-solid fa-calendar-day"></i></div>
        <div class="stat-value">${formatINR(s.today_spending)}</div>
        <div class="stat-label">Today's Spending</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon orange"><i class="fa-solid fa-calendar-week"></i></div>
        <div class="stat-value">${formatINR(s.week_spending)}</div>
        <div class="stat-label">This Week's Spending</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon red"><i class="fa-solid fa-calendar"></i></div>
        <div class="stat-value">${formatINR(s.month_expenses)}</div>
        <div class="stat-label">This Month's Spending</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green"><i class="fa-solid fa-money-bill-wave"></i></div>
        <div class="stat-value">${formatINR(s.month_income)}</div>
        <div class="stat-label">Monthly Income</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon blue"><i class="fa-solid fa-wallet"></i></div>
        <div class="stat-value">${formatINR(s.remaining)}</div>
        <div class="stat-label">Remaining Balance</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon purple"><i class="fa-solid fa-chart-pie"></i></div>
        <div class="stat-value">${formatINR(s.budget_remaining)}</div>
        <div class="stat-label">Budget Remaining</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green"><i class="fa-solid fa-piggy-bank"></i></div>
        <div class="stat-value">${formatINR(s.savings)}</div>
        <div class="stat-label">Savings (${s.savings_rate}%)</div>
      </div>
    `;
  }

  function renderDashboardBudgetProgress(budget, summary) {
    const el = document.getElementById('dashBudgetProgress');
    if (!el) return;
    if (!budget || !budget.amount) {
      el.innerHTML = `
        <div class="empty-state" style="padding:20px 0;">
          <i class="fa-solid fa-chart-pie"></i>
          <p>No budget set for this month</p>
          <button class="btn btn-primary btn-sm" style="margin-top:10px;" onclick="document.getElementById('quickAddBudget').click()">Set Budget</button>
        </div>
      `;
      return;
    }
    const pct = summary.budget_used_pct || 0;
    const barClass = pct >= 90 ? 'danger' : pct >= 75 ? 'warning' : 'primary';
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;font-weight:600;margin-bottom:6px;">
        <span>Spent: ${formatINR(summary.month_expenses)}</span>
        <span>Budget: ${formatINR(summary.budget)} (${pct}%)</span>
      </div>
      <div class="progress-bar-wrap">
        <div class="progress-bar-fill ${barClass}" style="width:${Math.min(pct, 100)}%;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:.85rem;color:var(--text-muted);margin-top:8px;">
        <span>Remaining: <strong style="color:${summary.budget_remaining < 0 ? 'var(--danger)' : 'var(--success)'};">${formatINR(summary.budget_remaining)}</strong></span>
        <span>${summary.budget_remaining < 0 ? 'Over budget!' : 'On track'}</span>
      </div>
    `;
  }

  function renderDashboardDailyLimit(limit) {
    const el = document.getElementById('dashDailyLimit');
    if (!el) return;
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
        <div style="background:var(--surface-2);padding:12px;border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:.75rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;">Daily Safe Spend</div>
          <div style="font-size:1.2rem;font-weight:700;color:var(--primary);margin-top:4px;">${formatINR(limit.suggested_daily)}</div>
        </div>
        <div style="background:var(--surface-2);padding:12px;border-radius:8px;border:1px solid var(--border);">
          <div style="font-size:.75rem;color:var(--text-muted);text-transform:uppercase;font-weight:600;">Spent Today</div>
          <div style="font-size:1.2rem;font-weight:700;color:${limit.today_spent > limit.suggested_daily ? 'var(--danger)' : 'var(--text)'};margin-top:4px;">${formatINR(limit.today_spent)}</div>
        </div>
      </div>
      <div style="font-size:.85rem;color:var(--text-muted);">
        Days remaining this month: <strong>${limit.days_remaining}</strong> | Left today: <strong style="color:var(--success);">${formatINR(limit.remaining_today)}</strong>
      </div>
    `;
  }

  function renderDashboardInsights(insights) {
    const el = document.getElementById('dashInsights');
    if (!el) return;
    if (!insights || insights.length === 0) {
      el.innerHTML = '<div class="empty-state" style="padding:15px 0;">No insights yet. Record more transactions to view AI insights.</div>';
      return;
    }
    el.innerHTML = insights.map(i => `
      <div class="insight-item">
        <div class="insight-icon" style="background:${i.color}20;color:${i.color};">
          <i class="fa-solid ${i.icon}"></i>
        </div>
        <div class="insight-text">${i.text}</div>
      </div>
    `).join('');
  }

  // ── 2. Daily View ─────────────────────────────────────────────────────────
  function initDailyView() {
    const picker = document.getElementById('dailyDatePicker');
    if (picker) {
      picker.value = state.selectedDate;
      picker.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        loadDailySpending();
      });
    }
    document.getElementById('dailyPrev')?.addEventListener('click', () => {
      const d = new Date(state.selectedDate);
      d.setDate(d.getDate() - 1);
      state.selectedDate = d.toISOString().split('T')[0];
      if (picker) picker.value = state.selectedDate;
      loadDailySpending();
    });
    document.getElementById('dailyNext')?.addEventListener('click', () => {
      const d = new Date(state.selectedDate);
      d.setDate(d.getDate() + 1);
      state.selectedDate = d.toISOString().split('T')[0];
      if (picker) picker.value = state.selectedDate;
      loadDailySpending();
    });
  }

  async function loadDailySpending() {
    try {
      const data = await API.get(`/api/money/daily?date=${state.selectedDate}`);
      const title = document.getElementById('dailyDateTitle');
      if (title) title.textContent = `${data.day_name}, ${data.date_display}`;

      const summary = document.getElementById('dailySummary');
      if (summary) {
        summary.innerHTML = `
          <div class="card stat-card">
            <div class="stat-icon red"><i class="fa-solid fa-receipt"></i></div>
            <div class="stat-value">${formatINR(data.total)}</div>
            <div class="stat-label">Total Spent Today</div>
          </div>
          <div class="card stat-card">
            <div class="stat-icon blue"><i class="fa-solid fa-list-ol"></i></div>
            <div class="stat-value">${data.transactions.length}</div>
            <div class="stat-label">Transactions</div>
          </div>
        `;
      }

      const cbEl = document.getElementById('dailyCategoryBreakdown');
      if (cbEl) {
        if (!data.category_breakdown.length) {
          cbEl.innerHTML = '<div class="empty-state" style="padding:15px 0;">No expenses recorded for this date.</div>';
        } else {
          cbEl.innerHTML = `
            <div style="display:flex;flex-direction:column;gap:8px;">
              ${data.category_breakdown.map(c => `
                <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);">
                  <span style="font-weight:600;">${c.name}</span>
                  <span style="font-weight:700;color:var(--danger);">${formatINR(c.amount)}</span>
                </div>
              `).join('')}
            </div>
          `;
        }
      }

      const listEl = document.getElementById('dailyTransactionList');
      if (listEl) {
        if (!data.transactions.length) {
          listEl.innerHTML = '<div class="empty-state" style="padding:15px 0;">No transactions on this day.</div>';
        } else {
          listEl.innerHTML = `
            <table class="txn-table">
              <tbody>
                ${data.transactions.map(t => renderTxnRow(t)).join('')}
              </tbody>
            </table>
          `;
          attachTxnActionListeners(listEl);
        }
      }
    } catch (err) {
      console.error('Failed to load daily spending:', err);
    }
  }

  // ── 3. Transactions View ──────────────────────────────────────────────────
  function initTransactionsView() {
    const search = document.getElementById('txnSearch');
    let debounceTimer;
    search?.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.txns.page = 1;
        loadTransactions();
      }, 300);
    });

    ['txnTypeFilter', 'txnCategoryFilter', 'txnPaymentFilter', 'txnDateFrom', 'txnDateTo', 'txnSort'].forEach(id => {
      document.getElementById(id)?.addEventListener('change', () => {
        state.txns.page = 1;
        loadTransactions();
      });
    });

    document.getElementById('exportCsv')?.addEventListener('click', () => triggerExport('csv'));
    document.getElementById('exportXlsx')?.addEventListener('click', () => triggerExport('xlsx'));
  }

  function getTxnFilterQuery() {
    const params = new URLSearchParams();
    params.set('page', state.txns.page);
    params.set('per_page', state.txns.per_page);

    const search = document.getElementById('txnSearch')?.value.trim();
    if (search) params.set('search', search);

    const type = document.getElementById('txnTypeFilter')?.value;
    if (type) params.set('type', type);

    const cat = document.getElementById('txnCategoryFilter')?.value;
    if (cat) params.set('category_id', cat);

    const pm = document.getElementById('txnPaymentFilter')?.value;
    if (pm) params.set('payment_method_id', pm);

    const dFrom = document.getElementById('txnDateFrom')?.value;
    if (dFrom) params.set('date_from', dFrom);

    const dTo = document.getElementById('txnDateTo')?.value;
    if (dTo) params.set('date_to', dTo);

    const sort = document.getElementById('txnSort')?.value;
    if (sort) params.set('sort', sort);

    return params.toString();
  }

  async function loadTransactions() {
    try {
      const qs = getTxnFilterQuery();
      const res = await API.get(`/api/money/transactions?${qs}`);
      state.txns.total = res.total;
      state.txns.pages = res.pages;

      const countEl = document.getElementById('txnResultCount');
      if (countEl) countEl.textContent = `Transactions (${res.total})`;

      const tbody = document.getElementById('txnTableBody');
      if (tbody) {
        if (!res.transactions.length) {
          tbody.innerHTML = '<tr><td colspan="7" class="text-center" style="padding:30px;"><div class="empty-state">No transactions match your filter criteria.</div></td></tr>';
        } else {
          tbody.innerHTML = res.transactions.map(t => renderTxnRow(t)).join('');
          attachTxnActionListeners(tbody);
        }
      }

      renderPagination();
    } catch (err) {
      console.error('Failed to load transactions:', err);
    }
  }

  function renderTxnRow(t) {
    const isExpense = t.type === 'expense';
    return `
      <tr data-id="${t.id}">
        <td>${formatShortDate(t.transaction_date)}</td>
        <td>
          <div style="font-weight:600;">${escapeHtml(t.description || 'Untitled')}</div>
          ${t.notes ? `<div style="font-size:.78rem;color:var(--text-muted);">${escapeHtml(t.notes)}</div>` : ''}
        </td>
        <td>
          <span style="display:inline-flex;align-items:center;gap:6px;">
            <i class="fa-solid ${t.category_icon || 'fa-circle'}" style="font-size:.8rem;color:var(--primary);"></i>
            ${escapeHtml(t.category_name || 'Uncategorized')}
          </span>
        </td>
        <td>
          <span class="txn-badge ${isExpense ? 'badge-expense' : 'badge-income'}">
            <i class="fa-solid ${isExpense ? 'fa-minus' : 'fa-plus'}"></i> ${t.type}
          </span>
        </td>
        <td>${escapeHtml(t.payment_method_name || '-')}</td>
        <td class="text-right ${isExpense ? 'amount-expense' : 'amount-income'}">
          ${isExpense ? '-' : '+'}${formatINR(t.amount)}
        </td>
        <td>
          <div style="display:flex;gap:6px;">
            <button class="icon-btn edit-txn-btn" data-id="${t.id}" title="Edit"><i class="fa-solid fa-pen-to-square"></i></button>
            <button class="icon-btn delete-txn-btn" data-id="${t.id}" title="Delete" style="color:var(--danger);"><i class="fa-solid fa-trash"></i></button>
          </div>
        </td>
      </tr>
    `;
  }

  function attachTxnActionListeners(container) {
    container.querySelectorAll('.edit-txn-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        const t = await API.get(`/api/money/transactions/${id}`);
        openTxnModal(t.type, t);
      });
    });

    container.querySelectorAll('.delete-txn-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        confirmDelete('Delete Transaction', 'Are you sure you want to delete this transaction?', async () => {
          await API.del(`/api/money/transactions/${id}`);
          Toast('Transaction deleted', 'success');
          loadTransactions();
          if (state.currentView === 'daily') loadDailySpending();
        });
      });
    });
  }

  function renderPagination() {
    const el = document.getElementById('txnPagination');
    if (!el) return;
    const { page, pages, total, per_page } = state.txns;
    if (pages <= 1) {
      el.innerHTML = `<span>Showing ${total} transactions</span>`;
      return;
    }
    const start = (page - 1) * per_page + 1;
    const end = Math.min(page * per_page, total);
    el.innerHTML = `
      <span>Showing ${start}-${end} of ${total}</span>
      <div style="display:flex;gap:6px;">
        <button class="btn btn-ghost btn-sm" id="prevTxnPage" ${page === 1 ? 'disabled' : ''}><i class="fa-solid fa-chevron-left"></i> Prev</button>
        <button class="btn btn-ghost btn-sm" id="nextTxnPage" ${page === pages ? 'disabled' : ''}>Next <i class="fa-solid fa-chevron-right"></i></button>
      </div>
    `;
    document.getElementById('prevTxnPage')?.addEventListener('click', () => {
      if (state.txns.page > 1) {
        state.txns.page--;
        loadTransactions();
      }
    });
    document.getElementById('nextTxnPage')?.addEventListener('click', () => {
      if (state.txns.page < state.txns.pages) {
        state.txns.page++;
        loadTransactions();
      }
    });
  }

  function triggerExport(fmt) {
    const qs = getTxnFilterQuery();
    window.location.href = `/api/money/export?format=${fmt}&${qs}`;
  }

  // ── 4. Calendar View ──────────────────────────────────────────────────────
  function initCalendarView() {
    document.getElementById('calMoneyPrev')?.addEventListener('click', () => {
      state.calMonth--;
      if (state.calMonth < 1) {
        state.calMonth = 12;
        state.calYear--;
      }
      loadCalendar();
    });
    document.getElementById('calMoneyNext')?.addEventListener('click', () => {
      state.calMonth++;
      if (state.calMonth > 12) {
        state.calMonth = 1;
        state.calYear++;
      }
      loadCalendar();
    });
    document.getElementById('calMoneyToday')?.addEventListener('click', () => {
      state.calYear = new Date().getFullYear();
      state.calMonth = new Date().getMonth() + 1;
      loadCalendar();
    });
  }

  async function loadCalendar() {
    try {
      const data = await API.get(`/api/money/calendar?year=${state.calYear}&month=${state.calMonth}`);
      const title = document.getElementById('calMoneyTitle');
      if (title) title.textContent = `${MONTH_NAMES[state.calMonth - 1]} ${state.calYear}`;

      const grid = document.getElementById('moneyCalendarGrid');
      if (!grid) return;

      const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      let html = weekdays.map(w => `<div style="text-align:center;font-weight:700;font-size:.78rem;color:var(--text-muted);padding:4px 0;">${w}</div>`).join('');

      // Leading empty cells
      for (let i = 0; i < data.first_weekday; i++) {
        html += '<div class="money-cal-day empty"></div>';
      }

      data.days.forEach(d => {
        const hasSpend = d.amount > 0;
        html += `
          <div class="money-cal-day" data-date="${d.date}">
            <div class="cal-date-num">${d.day}</div>
            ${hasSpend ? `<div class="cal-spending-val">${formatINR(d.amount)}</div>` : '<div style="font-size:.75rem;color:var(--text-muted);text-align:right;">-</div>'}
          </div>
        `;
      });

      grid.innerHTML = html;

      grid.querySelectorAll('.money-cal-day:not(.empty)').forEach(cell => {
        cell.addEventListener('click', () => {
          const dt = cell.getAttribute('data-date');
          state.selectedDate = dt;
          const picker = document.getElementById('dailyDatePicker');
          if (picker) picker.value = dt;
          switchView('daily');
        });
      });
    } catch (err) {
      console.error('Failed to load money calendar:', err);
    }
  }

  // ── 5. Budgets View ───────────────────────────────────────────────────────
  function initBudgetsView() {
    document.getElementById('budgetPrevMonth')?.addEventListener('click', () => {
      state.budgetMonth--;
      if (state.budgetMonth < 1) {
        state.budgetMonth = 12;
        state.budgetYear--;
      }
      loadBudgets();
    });
    document.getElementById('budgetNextMonth')?.addEventListener('click', () => {
      state.budgetMonth++;
      if (state.budgetMonth > 12) {
        state.budgetMonth = 1;
        state.budgetYear++;
      }
      loadBudgets();
    });
  }

  async function loadBudgets() {
    try {
      const title = document.getElementById('budgetMonthTitle');
      if (title) title.textContent = `${MONTH_NAMES[state.budgetMonth - 1]} ${state.budgetYear}`;

      const budget = await API.get(`/api/money/budgets?year=${state.budgetYear}&month=${state.budgetMonth}`);
      const container = document.getElementById('budgetContent');
      if (!container) return;

      if (!budget) {
        container.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-chart-pie"></i>
            <p>No budget set for ${MONTH_NAMES[state.budgetMonth - 1]} ${state.budgetYear}</p>
            <button class="btn btn-primary" style="margin-top:12px;" onclick="document.getElementById('quickAddBudget').click()">Set Budget</button>
          </div>
        `;
        return;
      }

      const totalPct = budget.total_pct || 0;
      const totalBarClass = totalPct >= 90 ? 'danger' : totalPct >= 75 ? 'warning' : 'primary';

      container.innerHTML = `
        <div class="card" style="margin-bottom:20px;">
          <div class="card-header">
            <h3>Overall Monthly Budget</h3>
            <button class="btn btn-ghost btn-sm" id="editBudgetBtn"><i class="fa-solid fa-pen-to-square"></i> Edit Budget</button>
          </div>
          <div style="display:flex;justify-content:space-between;font-weight:600;margin-bottom:6px;">
            <span>Spent: ${formatINR(budget.total_spent)}</span>
            <span>Budget: ${formatINR(budget.amount)} (${totalPct}%)</span>
          </div>
          <div class="progress-bar-wrap" style="height:14px;">
            <div class="progress-bar-fill ${totalBarClass}" style="width:${Math.min(totalPct, 100)}%;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:.9rem;color:var(--text-muted);margin-top:10px;">
            <span>Remaining: <strong style="color:${budget.total_remaining < 0 ? 'var(--danger)' : 'var(--success)'};">${formatINR(budget.total_remaining)}</strong></span>
            <span>Status: <strong>${budget.total_remaining < 0 ? 'Exceeded' : 'Under Budget'}</strong></span>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Category Budgets</h3>
          </div>
          <div style="display:flex;flex-direction:column;gap:16px;">
            ${(budget.category_budgets || []).map(cb => {
              const cbPct = cb.pct || 0;
              const cbBarClass = cbPct >= 90 ? 'danger' : cbPct >= 75 ? 'warning' : 'primary';
              return `
                <div style="border-bottom:1px solid var(--border);padding-bottom:12px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-weight:600;display:inline-flex;align-items:center;gap:8px;">
                      <i class="fa-solid ${cb.category_icon || 'fa-circle'}" style="color:var(--primary);"></i>
                      ${escapeHtml(cb.category_name)}
                    </span>
                    <span style="font-size:.9rem;">
                      <strong>${formatINR(cb.spent)}</strong> / ${formatINR(cb.amount)} (${cbPct}%)
                    </span>
                  </div>
                  <div class="progress-bar-wrap">
                    <div class="progress-bar-fill ${cbBarClass}" style="width:${Math.min(cbPct, 100)}%;"></div>
                  </div>
                  <div style="font-size:.8rem;color:var(--text-muted);text-align:right;">
                    Remaining: <span style="color:${cb.remaining < 0 ? 'var(--danger)' : 'var(--success)'};font-weight:600;">${formatINR(cb.remaining)}</span>
                  </div>
                </div>
              `;
            }).join('') || '<div class="empty-state" style="padding:15px 0;">No individual category budgets defined.</div>'}
          </div>
        </div>
      `;

      document.getElementById('editBudgetBtn')?.addEventListener('click', () => openBudgetModal(budget));
    } catch (err) {
      console.error('Failed to load budgets:', err);
    }
  }

  // ── 6. Savings Goals View ─────────────────────────────────────────────────
  function initGoalsView() {
    document.getElementById('addGoalBtn')?.addEventListener('click', () => openGoalModal());
  }

  async function loadGoals() {
    try {
      const goals = await API.get('/api/money/goals');
      const list = document.getElementById('goalsList');
      if (!list) return;

      if (!goals.length) {
        list.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-bullseye"></i>
            <p>No savings goals set yet.</p>
            <button class="btn btn-primary" style="margin-top:12px;" onclick="document.getElementById('addGoalBtn').click()">Create Goal</button>
          </div>
        `;
        return;
      }

      list.innerHTML = `
        <div class="goal-cards-grid">
          ${goals.map(g => {
            const isCompleted = g.status === 'completed';
            return `
              <div class="goal-card" data-id="${g.id}">
                <div class="goal-header">
                  <div>
                    <h4 class="goal-title">${escapeHtml(g.name)}</h4>
                    <div class="goal-meta">${g.target_date ? `Target: ${formatShortDate(g.target_date)}` : 'No deadline'}</div>
                  </div>
                  <span class="txn-badge ${isCompleted ? 'badge-income' : 'badge-expense'}">
                    ${isCompleted ? '<i class="fa-solid fa-check"></i> Completed' : 'In Progress'}
                  </span>
                </div>
                <div class="goal-amounts">
                  <span>Saved: <strong>${formatINR(g.current_amount)}</strong></span>
                  <span>Target: <strong>${formatINR(g.target_amount)}</strong></span>
                </div>
                <div class="progress-bar-wrap">
                  <div class="progress-bar-fill ${isCompleted ? 'success' : 'primary'}" style="width:${Math.min(g.progress_pct, 100)}%;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:.82rem;color:var(--text-muted);margin-top:6px;">
                  <span>${g.progress_pct}% complete</span>
                  <span>Remaining: ${formatINR(g.remaining)}</span>
                </div>
                <div class="goal-actions">
                  ${!isCompleted ? `<button class="btn btn-success btn-sm contribute-goal-btn" data-id="${g.id}"><i class="fa-solid fa-plus"></i> Add Money</button>` : ''}
                  <button class="icon-btn edit-goal-btn" data-id="${g.id}" title="Edit"><i class="fa-solid fa-pen-to-square"></i></button>
                  <button class="icon-btn delete-goal-btn" data-id="${g.id}" title="Delete" style="color:var(--danger);"><i class="fa-solid fa-trash"></i></button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;

      list.querySelectorAll('.contribute-goal-btn').forEach(b => {
        b.addEventListener('click', () => openContribModal(b.getAttribute('data-id')));
      });

      list.querySelectorAll('.edit-goal-btn').forEach(b => {
        b.addEventListener('click', () => {
          const id = b.getAttribute('data-id');
          const goal = goals.find(g => g.id === parseInt(id, 10));
          if (goal) openGoalModal(goal);
        });
      });

      list.querySelectorAll('.delete-goal-btn').forEach(b => {
        b.addEventListener('click', () => {
          const id = b.getAttribute('data-id');
          confirmDelete('Delete Goal', 'Are you sure you want to delete this savings goal?', async () => {
            await API.del(`/api/money/goals/${id}`);
            Toast('Goal deleted', 'success');
            loadGoals();
          });
        });
      });
    } catch (err) {
      console.error('Failed to load goals:', err);
    }
  }

  // ── 7. Recurring View ─────────────────────────────────────────────────────
  function initRecurringView() {
    document.getElementById('addRecurringBtn')?.addEventListener('click', () => openRecurringModal());
  }

  async function loadRecurring() {
    try {
      const items = await API.get('/api/money/recurring');
      const list = document.getElementById('recurringList');
      if (!list) return;

      if (!items.length) {
        list.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-rotate"></i>
            <p>No recurring transactions scheduled.</p>
            <button class="btn btn-primary" style="margin-top:12px;" onclick="document.getElementById('addRecurringBtn').click()">Add Recurring Expense</button>
          </div>
        `;
        return;
      }

      list.innerHTML = `
        <div class="recurring-cards-grid">
          ${items.map(r => `
            <div class="recurring-card" data-id="${r.id}" style="opacity:${r.active ? '1' : '0.6'};">
              <div class="recurring-header">
                <div>
                  <h4 class="recurring-title">${escapeHtml(r.description || 'Recurring Expense')}</h4>
                  <div class="recurring-meta">
                    <span style="text-transform:capitalize;">${r.frequency}</span> | Next: <strong>${formatShortDate(r.next_date)}</strong>
                  </div>
                </div>
                <div class="amount-expense" style="font-size:1.15rem;">
                  -${formatINR(r.amount)}
                </div>
              </div>
              <div style="display:flex;gap:8px;font-size:.85rem;color:var(--text-muted);margin:8px 0;">
                <span><i class="fa-solid ${r.category_icon || 'fa-circle'}"></i> ${escapeHtml(r.category_name || 'Uncategorized')}</span>
                <span>•</span>
                <span>${escapeHtml(r.payment_method_name || 'Default')}</span>
              </div>
              <div class="recurring-actions">
                <button class="btn btn-ghost btn-sm toggle-recurring-btn" data-id="${r.id}" data-active="${r.active}">
                  <i class="fa-solid ${r.active ? 'fa-pause' : 'fa-play'}"></i> ${r.active ? 'Pause' : 'Resume'}
                </button>
                <button class="icon-btn edit-recurring-btn" data-id="${r.id}" title="Edit"><i class="fa-solid fa-pen-to-square"></i></button>
                <button class="icon-btn delete-recurring-btn" data-id="${r.id}" title="Delete" style="color:var(--danger);"><i class="fa-solid fa-trash"></i></button>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      list.querySelectorAll('.toggle-recurring-btn').forEach(b => {
        b.addEventListener('click', async () => {
          const id = b.getAttribute('data-id');
          const currentActive = b.getAttribute('data-active') === 'true';
          await API.put(`/api/money/recurring/${id}`, { active: !currentActive });
          Toast(currentActive ? 'Recurring expense paused' : 'Recurring expense resumed', 'info');
          loadRecurring();
        });
      });

      list.querySelectorAll('.edit-recurring-btn').forEach(b => {
        b.addEventListener('click', () => {
          const id = b.getAttribute('data-id');
          const rec = items.find(r => r.id === parseInt(id, 10));
          if (rec) openRecurringModal(rec);
        });
      });

      list.querySelectorAll('.delete-recurring-btn').forEach(b => {
        b.addEventListener('click', () => {
          const id = b.getAttribute('data-id');
          confirmDelete('Delete Recurring Expense', 'Are you sure you want to delete this recurring rule?', async () => {
            await API.del(`/api/money/recurring/${id}`);
            Toast('Recurring expense deleted', 'success');
            loadRecurring();
          });
        });
      });
    } catch (err) {
      console.error('Failed to load recurring:', err);
    }
  }

  // ── 8. Analytics View ─────────────────────────────────────────────────────
  function initAnalyticsView() {
    document.getElementById('analyticsPrev')?.addEventListener('click', () => {
      state.analyticsMonth--;
      if (state.analyticsMonth < 1) {
        state.analyticsMonth = 12;
        state.analyticsYear--;
      }
      loadAnalytics();
    });
    document.getElementById('analyticsNext')?.addEventListener('click', () => {
      state.analyticsMonth++;
      if (state.analyticsMonth > 12) {
        state.analyticsMonth = 1;
        state.analyticsYear++;
      }
      loadAnalytics();
    });
  }

  async function loadAnalytics() {
    try {
      const title = document.getElementById('analyticsMonthTitle');
      if (title) title.textContent = `${MONTH_NAMES[state.analyticsMonth - 1]} ${state.analyticsYear}`;

      const data = await API.get(`/api/money/analytics?year=${state.analyticsYear}&month=${state.analyticsMonth}`);

      if (typeof Chart === 'undefined') return;

      renderCatPieChart(data.category_pie);
      renderDailyBarChart(data.daily_spending);
      renderMonthCompareChart(data.monthly_comparison);
      renderPaymentPieChart(data.payment_method);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  }

  function destroyChart(name) {
    if (state.charts[name]) {
      state.charts[name].destroy();
      state.charts[name] = null;
    }
  }

  function renderCatPieChart(items) {
    destroyChart('catPie');
    const ctx = document.getElementById('catPieChart')?.getContext('2d');
    if (!ctx) return;
    state.charts.catPie = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: items.map(i => i.name),
        datasets: [{
          data: items.map(i => i.amount),
          backgroundColor: [
            '#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#0ea5e9',
            '#a855f7', '#ec4899', '#14b8a6', '#8b5cf6', '#f97316'
          ],
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function renderDailyBarChart(dailyValues) {
    destroyChart('dailyBar');
    const ctx = document.getElementById('dailyBarChart')?.getContext('2d');
    if (!ctx) return;
    const labels = dailyValues.map((_, idx) => `${idx + 1}`);
    state.charts.dailyBar = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Daily Spending (₹)',
          data: dailyValues,
          backgroundColor: '#6366f1',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  function renderMonthCompareChart(comparison) {
    destroyChart('monthCompare');
    const ctx = document.getElementById('monthCompareChart')?.getContext('2d');
    if (!ctx) return;
    state.charts.monthCompare = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: comparison.map(c => c.month),
        datasets: [
          {
            label: 'Income (₹)',
            data: comparison.map(c => c.income),
            backgroundColor: '#22c55e',
            borderRadius: 4,
          },
          {
            label: 'Expenses (₹)',
            data: comparison.map(c => c.expenses),
            backgroundColor: '#ef4444',
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  function renderPaymentPieChart(items) {
    destroyChart('paymentPie');
    const ctx = document.getElementById('paymentPieChart')?.getContext('2d');
    if (!ctx) return;
    state.charts.paymentPie = new Chart(ctx, {
      type: 'pie',
      data: {
        labels: items.map(i => i.name),
        datasets: [{
          data: items.map(i => i.amount),
          backgroundColor: ['#6366f1', '#0ea5e9', '#22c55e', '#f59e0b', '#a855f7'],
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  // ── 9. Modals Logic ───────────────────────────────────────────────────────
  function initModals() {
    // Transaction modal
    document.getElementById('closeTxnModal')?.addEventListener('click', closeTxnModal);
    document.getElementById('cancelTxnBtn')?.addEventListener('click', closeTxnModal);
    document.getElementById('txnForm')?.addEventListener('submit', handleTxnSubmit);

    // Budget modal
    document.getElementById('closeBudgetModal')?.addEventListener('click', closeBudgetModal);
    document.getElementById('cancelBudgetBtn')?.addEventListener('click', closeBudgetModal);
    document.getElementById('budgetForm')?.addEventListener('submit', handleBudgetSubmit);

    // Goal modal
    document.getElementById('closeGoalModal')?.addEventListener('click', closeGoalModal);
    document.getElementById('cancelGoalBtn')?.addEventListener('click', closeGoalModal);
    document.getElementById('goalForm')?.addEventListener('submit', handleGoalSubmit);

    // Contrib modal
    document.getElementById('closeContribModal')?.addEventListener('click', closeContribModal);
    document.getElementById('cancelContribBtn')?.addEventListener('click', closeContribModal);
    document.getElementById('contribForm')?.addEventListener('submit', handleContribSubmit);

    // Recurring modal
    document.getElementById('closeRecurringModal')?.addEventListener('click', closeRecurringModal);
    document.getElementById('cancelRecurringBtn')?.addEventListener('click', closeRecurringModal);
    document.getElementById('recurringForm')?.addEventListener('submit', handleRecurringSubmit);
  }

  // Transaction Modal Open/Close
  function openTxnModal(type = 'expense', txn = null) {
    const overlay = document.getElementById('txnModalOverlay');
    const title = document.getElementById('txnModalTitle');
    const saveBtn = document.getElementById('saveTxnBtn');
    const idInput = document.getElementById('txnId');
    const typeInput = document.getElementById('txnType');

    typeInput.value = type;
    idInput.value = txn ? txn.id : '';

    const isEdit = !!txn;
    title.textContent = isEdit ? `Edit ${type === 'income' ? 'Income' : 'Expense'}` : `Add ${type === 'income' ? 'Income' : 'Expense'}`;
    saveBtn.textContent = isEdit ? 'Save Changes' : (type === 'income' ? 'Add Income' : 'Add Expense');
    saveBtn.className = type === 'income' ? 'btn btn-success' : 'btn btn-primary';

    document.getElementById('txnAmount').value = txn ? txn.amount : '';
    document.getElementById('txnDescription').value = txn ? txn.description : '';
    document.getElementById('txnCategory').value = txn ? txn.category_id : (state.categories[0]?.id || '');
    document.getElementById('txnPayment').value = txn ? (txn.payment_method_id || '') : (state.paymentMethods[0]?.id || '');
    document.getElementById('txnDate').value = txn ? txn.transaction_date : new Date().toISOString().split('T')[0];
    document.getElementById('txnTime').value = txn && txn.transaction_time ? txn.transaction_time : '';
    document.getElementById('txnNotes').value = txn ? txn.notes : '';

    overlay?.classList.add('open');
    document.getElementById('txnAmount')?.focus();
  }

  function closeTxnModal() {
    document.getElementById('txnModalOverlay')?.classList.remove('open');
  }

  async function handleTxnSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('txnId').value;
    const body = {
      type: document.getElementById('txnType').value,
      amount: parseFloat(document.getElementById('txnAmount').value),
      description: document.getElementById('txnDescription').value.trim(),
      category_id: parseInt(document.getElementById('txnCategory').value, 10) || null,
      payment_method_id: parseInt(document.getElementById('txnPayment').value, 10) || null,
      transaction_date: document.getElementById('txnDate').value,
      transaction_time: document.getElementById('txnTime').value || null,
      notes: document.getElementById('txnNotes').value.trim(),
    };

    try {
      if (id) {
        await API.put(`/api/money/transactions/${id}`, body);
        Toast('Transaction updated', 'success');
      } else {
        await API.post('/api/money/transactions', body);
        Toast('Transaction recorded', 'success');
      }
      closeTxnModal();
      refreshCurrentView();
    } catch (err) {
      Toast(err.message, 'error');
    }
  }

  // Budget Modal
  function openBudgetModal(existingBudget = null) {
    const overlay = document.getElementById('budgetModalOverlay');
    const amountInput = document.getElementById('budgetAmount');
    const catList = document.getElementById('budgetCategoryList');

    amountInput.value = existingBudget ? existingBudget.amount : '';

    // Render expense categories for sub-budgets
    const expenseCats = state.categories.filter(c => c.type !== 'income');
    const existingCatMap = {};
    if (existingBudget && existingBudget.category_budgets) {
      existingBudget.category_budgets.forEach(cb => {
        existingCatMap[cb.category_id] = cb.amount;
      });
    }

    catList.innerHTML = expenseCats.map(c => `
      <div class="budget-cat-row">
        <div class="budget-cat-name">
          <i class="fa-solid ${c.icon || 'fa-circle'}" style="color:var(--primary);"></i>
          <span>${escapeHtml(c.name)}</span>
        </div>
        <input type="number" step="0.01" min="0" data-cat-id="${c.id}" value="${existingCatMap[c.id] || ''}" placeholder="0.00">
      </div>
    `).join('');

    overlay?.classList.add('open');
    amountInput.focus();
  }

  function closeBudgetModal() {
    document.getElementById('budgetModalOverlay')?.classList.remove('open');
  }

  async function handleBudgetSubmit(e) {
    e.preventDefault();
    const amount = parseFloat(document.getElementById('budgetAmount').value);
    const catBudgets = [];
    document.querySelectorAll('#budgetCategoryList input').forEach(inp => {
      const val = parseFloat(inp.value);
      if (val > 0) {
        catBudgets.push({
          category_id: parseInt(inp.getAttribute('data-cat-id'), 10),
          amount: val,
        });
      }
    });

    try {
      await API.post('/api/money/budgets', {
        month: state.budgetMonth,
        year: state.budgetYear,
        amount,
        category_budgets: catBudgets,
      });
      Toast('Budget saved successfully', 'success');
      closeBudgetModal();
      refreshCurrentView();
    } catch (err) {
      Toast(err.message, 'error');
    }
  }

  // Goals Modal
  function openGoalModal(goal = null) {
    const overlay = document.getElementById('goalModalOverlay');
    const title = document.getElementById('goalModalTitle');
    const saveBtn = document.getElementById('saveGoalBtn');
    const idInput = document.getElementById('goalId');

    idInput.value = goal ? goal.id : '';
    title.textContent = goal ? 'Edit Savings Goal' : 'New Savings Goal';
    saveBtn.textContent = goal ? 'Save Changes' : 'Create Goal';

    document.getElementById('goalName').value = goal ? goal.name : '';
    document.getElementById('goalTarget').value = goal ? goal.target_amount : '';
    document.getElementById('goalDate').value = goal ? (goal.target_date || '') : '';

    overlay?.classList.add('open');
    document.getElementById('goalName').focus();
  }

  function closeGoalModal() {
    document.getElementById('goalModalOverlay')?.classList.remove('open');
  }

  async function handleGoalSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('goalId').value;
    const body = {
      name: document.getElementById('goalName').value.trim(),
      target_amount: parseFloat(document.getElementById('goalTarget').value),
      target_date: document.getElementById('goalDate').value || null,
    };

    try {
      if (id) {
        await API.put(`/api/money/goals/${id}`, body);
        Toast('Goal updated', 'success');
      } else {
        await API.post('/api/money/goals', body);
        Toast('Goal created', 'success');
      }
      closeGoalModal();
      loadGoals();
    } catch (err) {
      Toast(err.message, 'error');
    }
  }

  // Contribution Modal
  function openContribModal(goalId) {
    const overlay = document.getElementById('contribModalOverlay');
    document.getElementById('contribGoalId').value = goalId;
    document.getElementById('contribAmount').value = '';
    document.getElementById('contribDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('contribNotes').value = '';

    overlay?.classList.add('open');
    document.getElementById('contribAmount').focus();
  }

  function closeContribModal() {
    document.getElementById('contribModalOverlay')?.classList.remove('open');
  }

  async function handleContribSubmit(e) {
    e.preventDefault();
    const goalId = document.getElementById('contribGoalId').value;
    const body = {
      amount: parseFloat(document.getElementById('contribAmount').value),
      date: document.getElementById('contribDate').value,
      notes: document.getElementById('contribNotes').value.trim(),
    };

    try {
      await API.post(`/api/money/goals/${goalId}/contribute`, body);
      Toast('Contribution added!', 'success');
      closeContribModal();
      loadGoals();
      if (state.currentView === 'dashboard') loadDashboard();
    } catch (err) {
      Toast(err.message, 'error');
    }
  }

  // Recurring Modal
  function openRecurringModal(rec = null) {
    const overlay = document.getElementById('recurringModalOverlay');
    const title = document.getElementById('recurringModalTitle');
    const saveBtn = document.getElementById('saveRecurringBtn');
    const idInput = document.getElementById('recurringId');

    idInput.value = rec ? rec.id : '';
    title.textContent = rec ? 'Edit Recurring Expense' : 'Add Recurring Expense';
    saveBtn.textContent = rec ? 'Save Changes' : 'Add Recurring';

    document.getElementById('recurringDescription').value = rec ? rec.description : '';
    document.getElementById('recurringAmount').value = rec ? rec.amount : '';
    document.getElementById('recurringFrequency').value = rec ? rec.frequency : 'monthly';
    document.getElementById('recurringCategory').value = rec ? (rec.category_id || '') : (state.categories[0]?.id || '');
    document.getElementById('recurringPayment').value = rec ? (rec.payment_method_id || '') : (state.paymentMethods[0]?.id || '');
    document.getElementById('recurringNextDate').value = rec ? rec.next_date : new Date().toISOString().split('T')[0];

    overlay?.classList.add('open');
    document.getElementById('recurringDescription').focus();
  }

  function closeRecurringModal() {
    document.getElementById('recurringModalOverlay')?.classList.remove('open');
  }

  async function handleRecurringSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('recurringId').value;
    const body = {
      description: document.getElementById('recurringDescription').value.trim(),
      amount: parseFloat(document.getElementById('recurringAmount').value),
      frequency: document.getElementById('recurringFrequency').value,
      category_id: parseInt(document.getElementById('recurringCategory').value, 10) || null,
      payment_method_id: parseInt(document.getElementById('recurringPayment').value, 10) || null,
      next_date: document.getElementById('recurringNextDate').value,
    };

    try {
      if (id) {
        await API.put(`/api/money/recurring/${id}`, body);
        Toast('Recurring expense updated', 'success');
      } else {
        await API.post('/api/money/recurring', body);
        Toast('Recurring expense scheduled', 'success');
      }
      closeRecurringModal();
      loadRecurring();
    } catch (err) {
      Toast(err.message, 'error');
    }
  }

  // Confirm Delete Dialog
  function confirmDelete(title, text, onConfirm) {
    const overlay = document.getElementById('moneyConfirmOverlay');
    const titleEl = document.getElementById('moneyConfirmTitle');
    const textEl = document.getElementById('moneyConfirmText');
    const okBtn = document.getElementById('moneyConfirmOk');
    const cancelBtn = document.getElementById('moneyConfirmCancel');

    if (titleEl) titleEl.textContent = title;
    if (textEl) textEl.textContent = text;

    overlay?.classList.add('open');

    const handleOk = async () => {
      cleanup();
      await onConfirm();
    };

    const handleCancel = () => {
      cleanup();
    };

    function cleanup() {
      overlay?.classList.remove('open');
      okBtn?.removeEventListener('click', handleOk);
      cancelBtn?.removeEventListener('click', handleCancel);
    }

    okBtn?.addEventListener('click', handleOk);
    cancelBtn?.addEventListener('click', handleCancel);
  }

  function refreshCurrentView() {
    switchView(state.currentView);
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();
