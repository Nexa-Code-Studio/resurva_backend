// Backend Base URL
const API_BASE_URL = 'http://localhost:8080/api/v1';

// App State
const state = {
  activeTable: 'stores',
  activeTab: 'data-viewer-tab',
  storeId: '',
  userId: '',
  userRole: '',
  username: '',
  authToken: '',
  page: 1,
  pageSize: 20,
  sortBy: '',
  sortOrder: 'asc',
  searchQuery: '',
  conversationId: '',
  conversations: []
};

// Table definitions mapping HTML keys to official API endpoints
const tableEndpoints = {
  stores: '/stores/',
  products: '/products/',
  inventory_batches: '/inventory/batches',
  expiry_alerts: '/inventory/expiry-alerts',
  orders: '/orders/',
  discounts: '/discounts/',
  wallets: '/wallets/',
  wallet_transactions: '/wallets/transactions/all',
  transactions: '/transactions/',
  carbon_logs: '/carbon/carbon-logs',
  reviews: '/reviews/',
  daily_summaries: '/reports/daily',
  monthly_summaries: '/reports/monthly',
  users: '/users/',
  businesses: '/businesses/'
};

// Initialize the Application
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupTableNavigation();
  setupToolbar();
  setupChatbotTester();
  
  // Load initial dropdowns
  loadStoresDropdown();
  loadSellersDropdown();
  
  // Initial Table Load
  loadTableData();
});

// ==========================================
// 1. DROPDOWNS LOADER
// ==========================================

async function loadStoresDropdown() {
  const select = document.getElementById('store-select');
  try {
    const res = await fetch(`${API_BASE_URL}/stores/?page=1&page_size=100`);
    if (res.ok) {
      const data = await res.json();
      const stores = data.items || [];
      stores.forEach(store => {
        const option = document.createElement('option');
        option.value = store.id;
        option.textContent = `${store.name} (${store.city})`;
        select.appendChild(option);
      });
    }
  } catch (err) {
    console.error('Gagal memuat daftar toko:', err);
  }
}

async function loadSellersDropdown() {
  const select = document.getElementById('user-select');
  try {
    const res = await fetch(`${API_BASE_URL}/users/?page=1&page_size=100&role=seller`);
    if (res.ok) {
      const data = await res.json();
      const sellers = data.items || [];
      sellers.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = `${user.username} (${user.email})`;
        option.dataset.username = user.username;
        select.appendChild(option);
      });
    }
  } catch (err) {
    console.error('Gagal memuat daftar seller:', err);
  }
}

// ==========================================
// 2. TAB SWITCHER SETUP
// ==========================================

function setupTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      state.activeTab = tabId;
      
      tabButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(tabId).classList.add('active');
      
      if (tabId === 'chatbot-tab' && state.authToken) {
        loadConversations();
      }
    });
  });
}

// ==========================================
// 3. TABLE NAVIGATION & LOADER
// ==========================================

function setupTableNavigation() {
  const listItems = document.querySelectorAll('#table-list li');
  listItems.forEach(item => {
    item.addEventListener('click', () => {
      listItems.forEach(li => li.classList.remove('active'));
      item.classList.add('active');
      
      state.activeTable = item.getAttribute('data-table');
      state.page = 1; // Reset page on table switch
      state.sortBy = ''; // Reset sorting
      state.sortOrder = 'asc';
      
      document.getElementById('current-view-title').textContent = `Tabel: ${item.textContent.trim().substring(3)}`;
      document.getElementById('api-endpoint-badge').textContent = `API: ${tableEndpoints[state.activeTable]}`;
      
      loadTableData();
    });
  });
}

async function loadTableData() {
  const table = document.getElementById('data-table');
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  const loading = document.getElementById('loading-overlay');
  const noData = document.getElementById('no-data-msg');
  
  loading.classList.remove('hidden');
  noData.classList.add('hidden');
  thead.innerHTML = '';
  tbody.innerHTML = '';
  
  // Build API URL query params
  const endpoint = tableEndpoints[state.activeTable];
  let url = `${API_BASE_URL}${endpoint}?page=${state.page}&page_size=${state.pageSize}`;
  
  // Apply store filtering if selected and the table supports it
  if (state.storeId) {
    if (state.activeTable === 'stores') {
      // For stores list, we don't apply store_id query param unless we want specifically that store
      // But we can filter client side or handle as specific query. Let's just bypass it.
    } else if (state.activeTable === 'users' || state.activeTable === 'businesses') {
      // Users and businesses do not directly filter by store_id
    } else {
      url += `&store_id=${state.storeId}`;
    }
  }
  
  // Apply sorting parameters
  if (state.sortBy) {
    url += `&sort_by=${state.sortBy}&sort_order=${state.sortOrder}`;
  }
  
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Status error: ${res.status}`);
    const result = await res.json();
    
    const items = result.items || [];
    const pagination = result.pagination || { page: 1, page_size: 20, total: 0, total_pages: 0 };
    
    if (items.length === 0) {
      noData.classList.remove('hidden');
      updatePaginationControls(pagination);
      return;
    }
    
    // Extract headers dynamically from the first item keys
    const columns = Object.keys(items[0]);
    
    // Render headers
    const trHead = document.createElement('tr');
    columns.forEach(col => {
      const th = document.createElement('th');
      th.textContent = col;
      
      // Add sorting indicator
      if (state.sortBy === col) {
        const arrow = state.sortOrder === 'asc' ? ' ▲' : ' ▼';
        th.textContent += arrow;
      }
      
      th.addEventListener('click', () => {
        if (state.sortBy === col) {
          state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
          state.sortBy = col;
          state.sortOrder = 'asc';
        }
        loadTableData();
      });
      
      trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    
    // Render rows
    items.forEach(item => {
      const trRow = document.createElement('tr');
      columns.forEach(col => {
        const td = document.createElement('td');
        const val = item[col];
        
        td.innerHTML = formatCellValue(col, val);
        td.title = val !== null && typeof val === 'object' ? JSON.stringify(val) : String(val);
        trRow.appendChild(td);
      });
      tbody.appendChild(trRow);
    });
    
    updatePaginationControls(pagination);
  } catch (err) {
    console.error('Error fetching table data:', err);
    tbody.innerHTML = `<tr><td colspan="100%" class="error-text">Gagal memuat data: ${err.message}</td></tr>`;
  } finally {
    loading.classList.add('hidden');
  }
}

// Format database cell values beautifully
function formatCellValue(column, val) {
  if (val === null || val === undefined) {
    return `<span class="cell-badge">null</span>`;
  }
  
  if (typeof val === 'boolean') {
    return val 
      ? `<span class="cell-badge success">True</span>` 
      : `<span class="cell-badge danger">False</span>`;
  }
  
  // Format prices as Indonesian Rupiah
  if (['original_price', 'discounted_price', 'total_price', 'total_discount', 'final_price', 'balance', 'amount', 'balance_after', 'gross_amount', 'net_amount', 'platform_fee', 'unit_price', 'subtotal', 'total_revenue', 'total_discount_given'].includes(column) && typeof val === 'number') {
    return `Rp ${val.toLocaleString('id-ID')}`;
  }
  
  // Format carbon logs
  if (column === 'carbon_saved_kg' || column === 'carbon_per_unit') {
    return `${val} kg`;
  }
  
  // Shorten long IDs (UUIDs)
  if (typeof val === 'string' && val.length === 36 && val.includes('-')) {
    return `<span class="cell-badge" style="cursor: pointer;" onclick="navigator.clipboard.writeText('${val}'); alert('ID disalin ke clipboard!')">${val.substring(0, 8)}...</span>`;
  }
  
  // Format Dates
  if (['created_at', 'updated_at', 'expired_at', 'alerted_at', 'paid_at', 'start_time', 'end_time'].includes(column)) {
    const d = new Date(val);
    if (!isNaN(d)) {
      return d.toLocaleString('id-ID');
    }
  }
  
  if (typeof val === 'object') {
    return `<span class="cell-badge" style="cursor: pointer;" onclick="console.log(this.title)">JSON Object</span>`;
  }
  
  return String(val);
}

// Render pagination info and buttons
function updatePaginationControls(pag) {
  const footerInfo = document.getElementById('pagination-info');
  const footerCtrls = document.getElementById('pagination-controls');
  
  const startItem = (pag.page - 1) * pag.page_size + 1;
  const endItem = Math.min(pag.page * pag.page_size, pag.total);
  
  if (pag.total === 0) {
    footerInfo.textContent = 'Menampilkan 0 - 0 dari 0 baris';
  } else {
    footerInfo.textContent = `Menampilkan ${startItem} - ${endItem} dari ${pag.total} baris`;
  }
  
  footerCtrls.innerHTML = '';
  
  // First Page & Prev Page buttons
  const firstBtn = document.createElement('button');
  firstBtn.className = 'page-btn';
  firstBtn.innerHTML = '«';
  firstBtn.disabled = pag.page === 1;
  firstBtn.addEventListener('click', () => { state.page = 1; loadTableData(); });
  footerCtrls.appendChild(firstBtn);
  
  const prevBtn = document.createElement('button');
  prevBtn.className = 'page-btn';
  prevBtn.innerHTML = '‹';
  prevBtn.disabled = pag.page === 1;
  prevBtn.addEventListener('click', () => { state.page--; loadTableData(); });
  footerCtrls.appendChild(prevBtn);
  
  // Show page indicators
  const pageSpan = document.createElement('button');
  pageSpan.className = 'page-btn active';
  pageSpan.textContent = pag.page;
  footerCtrls.appendChild(pageSpan);
  
  const totalPagesSpan = document.createElement('span');
  totalPagesSpan.className = 'pagination-info';
  totalPagesSpan.textContent = ` dari ${pag.total_pages}`;
  totalPagesSpan.style.margin = '0 8px';
  footerCtrls.appendChild(totalPagesSpan);
  
  // Next Page & Last Page buttons
  const nextBtn = document.createElement('button');
  nextBtn.className = 'page-btn';
  nextBtn.innerHTML = '›';
  nextBtn.disabled = pag.page >= pag.total_pages;
  nextBtn.addEventListener('click', () => { state.page++; loadTableData(); });
  footerCtrls.appendChild(nextBtn);
  
  const lastBtn = document.createElement('button');
  lastBtn.className = 'page-btn';
  lastBtn.innerHTML = '»';
  lastBtn.disabled = pag.page >= pag.total_pages;
  lastBtn.addEventListener('click', () => { state.page = pag.total_pages; loadTableData(); });
  footerCtrls.appendChild(lastBtn);
}

// ==========================================
// 4. TOOLBAR CONTROLS SETUP
// ==========================================

function setupToolbar() {
  // Store selector change
  document.getElementById('store-select').addEventListener('change', (e) => {
    state.storeId = e.target.value;
    state.page = 1;
    loadTableData();
    
    // If chatbot is active, let chatbot know we changed the store context!
    if (state.conversationId) {
      // Optionally reset conversation or start new conversation for this store
    }
  });
  
  // Refresh button
  document.getElementById('btn-refresh').addEventListener('click', () => {
    loadTableData();
  });
  
  // Page size change
  document.getElementById('page-size').addEventListener('change', (e) => {
    state.pageSize = parseInt(e.target.value);
    state.page = 1;
    loadTableData();
  });
  
  // Client side row filter search
  document.getElementById('data-search').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#data-table tbody tr');
    
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      if (text.includes(query)) {
        row.classList.remove('hidden');
      } else {
        row.classList.add('hidden');
      }
    });
  });
}

// ==========================================
// 5. CHATBOT TEST PANEL LOGIC
// ==========================================

function setupChatbotTester() {
  const userSelect = document.getElementById('user-select');
  const chatInput = document.getElementById('chat-input');
  const chatForm = document.getElementById('chat-input-form');
  const btnSend = document.getElementById('btn-send-chat');
  const btnNewChat = document.getElementById('btn-new-chat');
  
  userSelect.addEventListener('change', async (e) => {
    const userId = e.target.value;
    const selectedOption = e.target.options[e.target.selectedIndex];
    
    if (!userId) {
      // Disconnect
      state.userId = '';
      state.username = '';
      state.authToken = '';
      state.conversationId = '';
      updateChatUIState(false);
      return;
    }
    
    state.userId = userId;
    state.username = selectedOption.dataset.username;
    state.conversationId = ''; // Reset conversation ID to prevent sending messages to the old conversation
    
    // Auto login
    const email = `${state.username}@example.com`;
    // Admin user has admin@resurva.com
    const loginEmail = state.username === 'super_admin' ? 'admin@resurva.com' : email;
    
    updateChatStatus(`Sedang login sebagai ${state.username}...`, 'offline');
    
    try {
      const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username_or_email: loginEmail,
          password: 'password123'
        })
      });
      
      if (!loginRes.ok) throw new Error('Gagal login. Periksa seeder database.');
      const loginData = await loginRes.json();
      state.authToken = loginData.access_token;
      
      updateChatStatus(`Aktif: ${state.username}`, 'active');
      updateChatUIState(true);
      
      // Load current user conversations
      await loadConversations();
    } catch (err) {
      console.error(err);
      updateChatStatus(`Error: ${err.message}`, 'offline');
      updateChatUIState(false);
    }
  });
  
  // Create New Chat Session
  btnNewChat.addEventListener('click', async () => {
    if (!state.authToken) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.authToken}`
        },
        body: JSON.stringify({
          store_id: state.storeId || null,
          title: `Chat ${new Date().toLocaleTimeString('id-ID')}`
        })
      });
      
      if (!res.ok) throw new Error('Gagal memulai chat baru');
      const conv = await res.json();
      state.conversationId = conv.id;
      
      await loadConversations();
      await loadConversationMessages(conv.id);
    } catch (err) {
      alert(err.message);
    }
  });
  
  // Submit chat prompt
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || !state.conversationId || !state.authToken) return;
    
    // Add user bubble instantly
    appendMessageBubble('user', text);
    chatInput.value = '';
    chatInput.disabled = true;
    btnSend.disabled = true;
    
    // Append dummy typing bubble
    const typingBubble = appendMessageBubble('assistant', '🤖 Mengetik...');
    
    try {
      // POST message using query params as defined in FastAPI backend route
      const res = await fetch(`${API_BASE_URL}/chat/conversations/${state.conversationId}/messages?user_message=${encodeURIComponent(text)}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${state.authToken}`
        }
      });
      
      if (!res.ok) throw new Error('Gagal mengirim pesan');
      const messages = await res.json();
      
      // Remove typing indicator and append actual answer
      typingBubble.remove();
      
      // Render the messages list directly (user message, tool calls, and bot reply)
      renderMessagesList(messages);
      
      // Re-enable inputs
      chatInput.disabled = false;
      btnSend.disabled = false;
      chatInput.focus();
      
      // Proactively refresh tables in background to reflect any model changes
      loadTableData();
    } catch (err) {
      console.error(err);
      const contentDiv = typingBubble.querySelector('.message-content');
      if (contentDiv) {
        contentDiv.innerHTML = marked.parse(`Error: ${err.message}`);
      } else {
        typingBubble.innerHTML = marked.parse(`Error: ${err.message}`);
      }
      chatInput.disabled = false;
      btnSend.disabled = false;
    }
  });
}

function updateChatUIState(connected) {
  const chatInput = document.getElementById('chat-input');
  const btnSend = document.getElementById('btn-send-chat');
  const btnNewChat = document.getElementById('btn-new-chat');
  const messageArea = document.getElementById('chat-messages');
  const conversationList = document.getElementById('conversation-list');
  
  if (connected) {
    btnNewChat.disabled = false;
    conversationList.innerHTML = '';
  } else {
    chatInput.disabled = true;
    btnSend.disabled = true;
    btnNewChat.disabled = true;
    conversationList.innerHTML = '';
    messageArea.innerHTML = `
      <div class="chat-placeholder">
        <span class="placeholder-icon">🤖</span>
        <p>Pilih user seller dari panel sidebar kiri, lalu mulai chat untuk menguji asisten AI.</p>
      </div>
    `;
    state.conversationId = '';
  }
}

function updateChatStatus(text, statusClass) {
  const indicator = document.getElementById('chat-status-indicator');
  const textEl = document.getElementById('chat-status-text');
  
  indicator.className = `status-indicator ${statusClass}`;
  textEl.textContent = text;
}

async function loadConversations() {
  const list = document.getElementById('conversation-list');
  list.innerHTML = '';
  
  try {
    const res = await fetch(`${API_BASE_URL}/chat/conversations`, {
      headers: { 'Authorization': `Bearer ${state.authToken}` }
    });
    
    if (res.ok) {
      const conversations = await res.json();
      state.conversations = conversations;
      
      if (conversations.length === 0) {
        list.innerHTML = `<li class="conversation-item">Tidak ada riwayat chat</li>`;
        return;
      }
      
      conversations.forEach(c => {
        const li = document.createElement('li');
        li.className = `conversation-item ${state.conversationId === c.id ? 'active' : ''}`;
        
        const title = document.createElement('span');
        title.className = 'conversation-title';
        title.textContent = c.title || `Percakapan #${c.id.substring(0, 6)}`;
        
        const date = document.createElement('span');
        date.className = 'conversation-date';
        date.textContent = new Date(c.updated_at).toLocaleString('id-ID');
        
        li.appendChild(title);
        li.appendChild(date);
        
        li.addEventListener('click', () => {
          document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
          li.classList.add('active');
          state.conversationId = c.id;
          loadConversationMessages(c.id);
        });
        
        list.appendChild(li);
      });
      
      // Auto-select first conversation if none selected
      if (!state.conversationId && conversations.length > 0) {
        state.conversationId = conversations[0].id;
        list.firstChild.classList.add('active');
        loadConversationMessages(conversations[0].id);
      }
    }
  } catch (err) {
    console.error('Error loading conversations:', err);
  }
}

async function loadConversationMessages(convId) {
  const chatInput = document.getElementById('chat-input');
  const btnSend = document.getElementById('btn-send-chat');
  
  chatInput.disabled = false;
  btnSend.disabled = false;
  chatInput.focus();
  
  try {
    const res = await fetch(`${API_BASE_URL}/chat/conversations/${convId}/messages`, {
      headers: { 'Authorization': `Bearer ${state.authToken}` }
    });
    
    if (res.ok) {
      const messages = await res.json();
      renderMessagesList(messages);
    }
  } catch (err) {
    console.error('Error loading messages:', err);
  }
}

function renderMessagesList(messages) {
  const messageArea = document.getElementById('chat-messages');
  messageArea.innerHTML = '';

  if (messages.length === 0) {
    messageArea.innerHTML = `
      <div class="chat-placeholder">
        <span class="placeholder-icon">💬</span>
        <p>Percakapan kosong. Ketik pesan Anda di bawah untuk mengobrol.</p>
      </div>
    `;
    return;
  }

  messages.forEach(msg => {
    // Skip system prompt to avoid clutter
    if (msg.role === 'system') return;

    const bubble = appendMessageBubble(msg.role, msg.content, msg.created_at);

    // Render tool calls inside assistant bubble if available
    if (msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0) {
      const tcContainer = document.createElement('div');
      tcContainer.className = 'tool-calls-container';

      msg.tool_calls.forEach(tc => {
        const card = document.createElement('div');
        card.className = 'tool-call-card';

        const header = document.createElement('div');
        header.className = 'tool-call-header';
        header.innerHTML = `<span>🔧 Tool Call: <b>${tc.tool_name}</b></span><span>▼</span>`;

        const body = document.createElement('div');
        body.className = 'tool-call-body';
        body.innerHTML = `
          <div><span class="tool-label">Input Parameters:</span></div>
          <pre>${formatJSONString(tc.tool_input)}</pre>
          <div class="tool-call-divider"></div>
          <div><span class="tool-label">Output Result:</span></div>
          <pre>${formatJSONString(tc.tool_output)}</pre>
        `;

        // Toggle body expand/collapse
        header.addEventListener('click', () => {
          body.style.display = body.style.display === 'none' ? 'block' : 'none';
        });

        card.appendChild(header);
        card.appendChild(body);
        tcContainer.appendChild(card);
      });

      bubble.appendChild(tcContainer);
    }
  });

  // Auto-scroll chat area
  messageArea.scrollTop = messageArea.scrollHeight;
}

function appendMessageBubble(role, content, timeStr) {
  const messageArea = document.getElementById('chat-messages');
  
  // Remove placeholder if present
  const placeholder = messageArea.querySelector('.chat-placeholder');
  if (placeholder) placeholder.remove();
  
  const bubble = document.createElement('div');
  bubble.className = `message-bubble ${role}`;
  
  const text = document.createElement('div');
  text.className = 'message-content';
  text.innerHTML = marked.parse(content);
  bubble.appendChild(text);
  
  const time = document.createElement('span');
  time.className = 'message-time';
  
  const date = timeStr ? new Date(timeStr) : new Date();
  time.textContent = date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  bubble.appendChild(time);
  
  messageArea.appendChild(bubble);
  messageArea.scrollTop = messageArea.scrollHeight;
  
  return bubble;
}

// Utility to parse and format JSON string nicely
function formatJSONString(str) {
  if (!str) return 'null';
  try {
    const obj = JSON.parse(str);
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return str;
  }
}
