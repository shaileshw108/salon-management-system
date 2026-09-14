const API = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
const STATUS_TOKEN_KEY = 'salon_queue_status_token';
const serviceList = document.querySelector('#service-list');
const serviceSelect = document.querySelector('#service');
const result = document.querySelector('#result');
const statusInput = document.querySelector('#entry-id');

async function loadServices() {
  const response = await fetch(`${API}/api/services`);
  if (!response.ok) throw new Error('Unable to load services');
  const services = await response.json();
  serviceList.innerHTML = services.length ? services.map(s => `<article class="card"><h3>${escapeHtml(s.name)}</h3><p class="muted">${s.duration_minutes} minutes</p><p>${escapeHtml(s.description || 'Premium salon service')}</p></article>`).join('') : '<p class="muted">Services will appear here.</p>';
  serviceSelect.innerHTML = services.map(s => `<option value="${s.id}">${escapeHtml(s.name)} · ${s.duration_minutes} min</option>`).join('');
}

async function loadGallery() {
  const response = await fetch(`${API}/api/gallery`);
  if (!response.ok) return;
  const items = await response.json();
  document.querySelector('#gallery-list').innerHTML = items.length ? items.map(x => `<article class="gallery-item"><img src="${escapeAttr(x.image_url)}" alt="${escapeAttr(x.title)}"><h3>${escapeHtml(x.title)}</h3><p class="muted">${escapeHtml(x.description || '')}</p></article>`).join('') : '<p class="muted">Our latest work will appear here.</p>';
}

document.querySelector('#queue-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const response = await fetch(`${API}/api/queue/join`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ customer_name: document.querySelector('#name').value, phone: document.querySelector('#phone').value, service_id: Number(serviceSelect.value) }) });
  const data = await response.json();
  result.hidden = false;
  result.innerHTML = response.ok
    ? `<strong>Your token is #${data.token_number}</strong><br>We have added you to the ${escapeHtml(data.service_name)} queue.<br><span class="muted">Your private queue status is saved in this browser for this session.</span>`
    : `<strong>Could not join the queue.</strong><br>${escapeHtml(data.detail || 'Please try again.')}`;
  if (response.ok && data.status_token) {
    sessionStorage.setItem(STATUS_TOKEN_KEY, data.status_token);
    statusInput.value = '';
    document.querySelector('#status-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});

document.querySelector('#status-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const box = document.querySelector('#status-result');
  const enteredValue = statusInput.value.trim();
  const isManualToken = /^\d+$/.test(enteredValue);
  const savedStatusToken = sessionStorage.getItem(STATUS_TOKEN_KEY);

  try {
    let url;
    if (isManualToken) {
      url = `${API}/api/queue/status/token/${encodeURIComponent(enteredValue)}`;
    } else if (savedStatusToken) {
      url = `${API}/api/queue/status/${encodeURIComponent(savedStatusToken)}`;
    } else {
      throw new Error('Enter your queue token number, such as 7 or 8.');
    }

    const response = await fetch(url, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Queue status not found');
    box.hidden = false;
    box.innerHTML = `<strong>Token #${data.token_number}</strong><br>${escapeHtml(data.service_name)} · <span class="status ${data.status}">${escapeHtml(data.status)}</span><br><span class="muted">Queue status updated successfully.</span>`;
  } catch (error) {
    box.hidden = false;
    box.innerHTML = `<strong>Unable to check status.</strong><br>${escapeHtml(error.message)}`;
  }
});

function escapeHtml(value) { return String(value).replace(/[&<>'\"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '\"': '&quot;' }[c])); }
function escapeAttr(value) { return escapeHtml(value); }

statusInput.value = '';
Promise.all([loadServices(), loadGallery()]).catch(() => { serviceList.innerHTML = '<p class="muted">Unable to load live services. Please refresh the page.</p>'; });
