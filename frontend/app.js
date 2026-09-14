const API = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
const STATUS_TOKEN_KEY = 'salon_queue_status_token';
const serviceList = document.querySelector('#service-list');
const serviceSelect = document.querySelector('#service');
const result = document.querySelector('#result');
const statusInput = document.querySelector('#entry-id');
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
async function request(path, options = {}, retries = 3) {
  try {
    const response = await fetch(`${API}${path}`, options);
    if (retries > 0 && [502, 503, 504].includes(response.status)) { await response.body?.cancel(); await sleep([1500, 3500, 7000][3 - retries] || 7000); return request(path, options, retries - 1); }
    return response;
  } catch (error) {
    if (retries > 0) { await sleep([1500, 3500, 7000][3 - retries] || 7000); return request(path, options, retries - 1); }
    throw new Error('Unable to reach the server. Please try again.');
  }
}
async function readResponse(response) {
  const type = response.headers.get('content-type') || '';
  if (!type.includes('application/json')) throw new Error(response.status >= 500 ? 'Server temporarily unavailable. Please try again.' : `Unexpected server response (HTTP ${response.status}).`);
  const data = await response.json();
  if (!response.ok) throw new Error(data?.detail || 'Request failed');
  return data;
}
async function loadServices() { const response = await request('/api/services'); const services = await readResponse(response); serviceList.innerHTML = services.length ? services.map(s => `<article class="card"><h3>${escapeHtml(s.name)}</h3><p class="muted">${s.duration_minutes} minutes</p><p>${escapeHtml(s.description || 'Premium salon service')}</p></article>`).join('') : '<p class="muted">Services will appear here.</p>'; serviceSelect.innerHTML = services.map(s => `<option value="${s.id}">${escapeHtml(s.name)} · ${s.duration_minutes} min</option>`).join(''); }
async function loadGallery() { try { const items = await readResponse(await request('/api/gallery')); document.querySelector('#gallery-list').innerHTML = items.length ? items.map(x => `<article class="gallery-item"><img src="${escapeAttr(x.image_url)}" alt="${escapeAttr(x.title)}"><h3>${escapeHtml(x.title)}</h3><p class="muted">${escapeHtml(x.description || '')}</p></article>`).join('') : '<p class="muted">Our latest work will appear here.</p>'; } catch (error) { document.querySelector('#gallery-list').innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`; } }
document.querySelector('#queue-form').addEventListener('submit', async (event) => { event.preventDefault(); result.hidden = false; result.innerHTML = '<span class="muted">Joining the queue…</span>'; try { const data = await readResponse(await request('/api/queue/join', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ customer_name: document.querySelector('#name').value, phone: document.querySelector('#phone').value, service_id: Number(serviceSelect.value) }) })); result.innerHTML = `<strong>Your token is #${data.token_number}</strong><br>We have added you to the ${escapeHtml(data.service_name)} queue.<br><span class="muted">Your private queue status is saved in this browser for this session.</span>`; if (data.status_token) { sessionStorage.setItem(STATUS_TOKEN_KEY, data.status_token); statusInput.value = ''; document.querySelector('#status-form').scrollIntoView({ behavior: 'smooth', block: 'center' }); } } catch (error) { result.innerHTML = `<strong>Could not join the queue.</strong><br>${escapeHtml(error.message)}`; } });
document.querySelector('#status-form').addEventListener('submit', async (event) => { event.preventDefault(); const box = document.querySelector('#status-result'); const enteredValue = statusInput.value.trim(); const isManualToken = /^\d+$/.test(enteredValue); const savedStatusToken = sessionStorage.getItem(STATUS_TOKEN_KEY); try { let url; if (isManualToken) url = `${API}/api/queue/status/token/${encodeURIComponent(enteredValue)}`; else if (savedStatusToken) url = `${API}/api/queue/status/${encodeURIComponent(savedStatusToken)}`; else throw new Error('Enter your queue token number, such as 7 or 8.'); const data = await readResponse(await request(url, { cache: 'no-store' })); box.hidden = false; box.innerHTML = `<strong>Token #${data.token_number}</strong><br>${escapeHtml(data.service_name)} · <span class="status ${data.status}">${escapeHtml(data.status)}</span><br><span class="muted">Queue status updated successfully.</span>`; } catch (error) { box.hidden = false; box.innerHTML = `<strong>Unable to check status.</strong><br>${escapeHtml(error.message)}`; } });
function escapeHtml(value) { return String(value).replace(/[&<>'\"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '\"':'&quot;' }[c])); }
function escapeAttr(value) { return escapeHtml(value); }
statusInput.value = '';
Promise.all([loadServices(), loadGallery()]).catch((error) => { serviceList.innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`; });
