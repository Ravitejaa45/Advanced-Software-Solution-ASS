const API_BASE = '/api';
const USER_HEADER = { 'X-User-Id': 'demo_user' };

function tryParseJSON(text) {
  try { return JSON.parse(text); } catch (e) { return null; }
}

function addConditionRow(groupId, keyOptions) {
  const row = document.createElement('div');
  row.className = 'row g-2 align-items-center mb-1 condition-row';
  row.dataset.group = groupId;

  const keySel = document.createElement('select');
  keySel.className = 'form-select form-select-sm';
  keyOptions.forEach(k => {
    const opt = document.createElement('option');
    opt.value = k; opt.textContent = k;
    keySel.appendChild(opt);
  });

  const opSel = document.createElement('select');
  opSel.className = 'form-select form-select-sm';
  ['=','!=','<','>','<=','>='].forEach(op => {
    const opt = document.createElement('option');
    opt.value = op; opt.textContent = op;
    opSel.appendChild(opt);
  });

  const valInput = document.createElement('input');
  valInput.className = 'form-control form-control-sm';
  valInput.placeholder = 'Value (JSON literal)';

  const col1 = document.createElement('div'); col1.className = 'col-6'; col1.appendChild(keySel);
  const col2 = document.createElement('div'); col2.className = 'col-2'; col2.appendChild(opSel);
  const col3 = document.createElement('div'); col3.className = 'col-3'; col3.appendChild(valInput);
  const col4 = document.createElement('div'); col4.className = 'col-1';
  const delBtn = document.createElement('button'); delBtn.className = 'btn btn-outline-danger btn-sm'; delBtn.textContent = 'X';
  delBtn.onclick = () => row.remove();
  col4.appendChild(delBtn);

  row.appendChild(col1); row.appendChild(col2); row.appendChild(col3); row.appendChild(col4);
  document.getElementById('conditions').appendChild(row);
}

async function extractKeys() {
  const txt = document.getElementById('sample-json').value.trim();
  const obj = tryParseJSON(txt);
  const status = document.getElementById('extract-status');
  status.textContent = '';
  const sel = document.getElementById('available-keys');
  sel.innerHTML = '';

  if (!obj || typeof obj !== 'object') {
    status.textContent = 'Invalid JSON';
    return;
  }
  const res = await fetch(`${API_BASE}/keys/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...USER_HEADER },
    body: JSON.stringify(obj)
  });
  const data = await res.json();
  (data.keys || []).forEach(k => {
    const opt = document.createElement('option');
    opt.value = k; opt.textContent = k;
    sel.appendChild(opt);
  });
  status.textContent = `${(data.keys||[]).length} keys extracted`;
}

function readConditionsFromUI() {
  const rows = document.querySelectorAll('.condition-row');
  const conditions = [];
  rows.forEach(r => {
    const group = parseInt(r.dataset.group || '1', 10);
    const key_path = r.querySelector('select').value;
    const op = r.querySelectorAll('select')[1].value;
    const valText = r.querySelector('input').value.trim();
    let value;
    try { value = JSON.parse(valText); } catch { value = valText; }
    conditions.push({ group, key_path, operator: op, value });
  });
  return conditions;
}

async function saveRule() {
  const name = document.getElementById('rule-name').value.trim();
  const label = document.getElementById('rule-label').value.trim();
  const priority = parseInt(document.getElementById('rule-priority').value || '100', 10);
  const active = document.getElementById('rule-active').checked;
  const conditions = readConditionsFromUI();
  const status = document.getElementById('save-status');
  status.textContent = '';

  if (!name || !label || conditions.length === 0) {
    status.textContent = 'Fill name, label, and at least one condition';
    return;
  }

  const res = await fetch(`${API_BASE}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...USER_HEADER },
    body: JSON.stringify({ name, label, priority, active, conditions })
  });
  if (!res.ok) {
    const err = await res.json();
    status.textContent = `Error: ${err.error||res.statusText}`;
  } else {
    status.textContent = 'Saved!';
    await loadRules();
  }
}

async function loadRules() {
  const list = document.getElementById('rules-list');
  list.innerHTML = '';
  const res = await fetch(`${API_BASE}/rules`, { headers: USER_HEADER });
  const rules = await res.json();
  rules.forEach(r => {
    const item = document.createElement('div');
    item.className = 'list-group-item d-flex justify-content-between align-items-start';
    const info = document.createElement('div');
    info.innerHTML = `<div><b>${r.name}</b> — <span class="badge bg-secondary">${r.label}</span> <small>(p:${r.priority})</small> ${r.active ? '' : '<span class="badge bg-warning text-dark">disabled</span>'}</div>
                      <div class="text-muted">${r.conditions.length} condition(s), ${new Set(r.conditions.map(c=>c.group)).size} group(s)</div>`;
    const actions = document.createElement('div');
    const toggle = document.createElement('button'); toggle.className='btn btn-sm btn-outline-secondary me-1'; toggle.textContent='Toggle';
    toggle.onclick = async () => { await fetch(`${API_BASE}/rules/${r.id}/toggle`, { method:'POST', headers: USER_HEADER }); loadRules(); };
    const del = document.createElement('button'); del.className='btn btn-sm btn-outline-danger'; del.textContent='Delete';
    del.onclick = async () => { await fetch(`${API_BASE}/rules/${r.id}`, { method:'DELETE', headers: USER_HEADER }); loadRules(); };
    actions.appendChild(toggle); actions.appendChild(del);
    item.appendChild(info); item.appendChild(actions);
    list.appendChild(item);
  });
}

async function processNow() {
  const txt = document.getElementById('process-json').value.trim();
  const obj = tryParseJSON(txt);
  const out = document.getElementById('process-result');
  out.textContent = '';
  if (!obj) { out.textContent = 'Invalid JSON'; return; }

  const singleLabel = document.getElementById('singleLabelChk')?.checked;
  const url = `${API_BASE}/process${singleLabel ? '?single_label=true' : ''}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...USER_HEADER },
    body: JSON.stringify(obj)
  });
  const data = await res.json();
  out.textContent = JSON.stringify(data, null, 2);
}

document.getElementById('btn-extract').onclick = extractKeys;
document.getElementById('btn-save-rule').onclick = saveRule;
document.getElementById('btn-process').onclick = processNow;
document.getElementById('btn-add-condition').onclick = () => {
  const keys = Array.from(document.getElementById('available-keys').options).map(o=>o.value);
  addConditionRow(1, keys);
};
document.getElementById('btn-add-group').onclick = () => {
  const keys = Array.from(document.getElementById('available-keys').options).map(o=>o.value);
  const rows = document.querySelectorAll('.condition-row');
  let maxg = 0; rows.forEach(r => { maxg = Math.max(maxg, parseInt(r.dataset.group||'1',10)); });
  addConditionRow(maxg+1, keys);
};
window.addEventListener('load', async () => {
  await loadRules();
});
