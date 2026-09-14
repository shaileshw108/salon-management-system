const API = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
const serviceList = document.querySelector('#service-list');
const serviceSelect = document.querySelector('#service');
const result = document.querySelector('#result');

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
    ? `<strong>Your token is #${data.token_number}</strong><br>We have added you to the ${escapeHtml(data.service_name)} queue.<br><span class="muted">Use the same browser to check your status below.</span>`
    : `<strong>Could not join the queue.</strong><br>${escapeHtml(data.detail || 'Please try again.')}`;
  if (response.ok) {
    document.querySelector('#entry-id').value = data.status_token;
    document.querySelector('#status-form').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
});

document.querySelector('#status-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const box = document.querySelector('#status-result');
  const statusToken = document.querySelector('#entry-id').value.trim();
  try {
    const response = await fetch(`${API}/api/queue/status/${encodeURIComponent(statusToken)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Queue status not found');
    box.hidden = false;
    box.innerHTML = `<strong>Token #${data.token_number}</strong><br>${escapeHtml(data.service_name)} · <span class="status ${data.status}">${escapeHtml(data.status)}</span><br><span class="muted">Your private status link expires after 24 hours.</span>`;
  } catch (error) { box.hidden = false; box.innerHTML = `<strong>Unable to check status.</strong><br>${escapeHtml(error.message)}`; }
});

function escapeHtml(value) { return String(value).replace(/[&<>'\"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '\"': '&quot;' }[c])); }
function escapeAttr(value) { return escapeHtml(value); }
Promise.all([loadServices(), loadGallery()]).catch(() => { serviceList.innerHTML = '<p class="muted">Unable to load live services. Please refresh the page.</p>'; });
