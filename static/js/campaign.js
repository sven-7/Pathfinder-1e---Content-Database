/* ═══════════════════════════════════════════════════════
   CAMPAIGN MANAGER — PF1e Campaign Dashboard
   ═══════════════════════════════════════════════════════ */

const API = '/api';

// ── Auth helpers (same pattern as creator.js) ─────────────────────────── //

function getAuthHeader() {
  const token = localStorage.getItem('pf1e_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function handleUnauth() {
  localStorage.removeItem('pf1e_token');
  window.location.href = '/login';
}

window.signOut = function() {
  localStorage.removeItem('pf1e_token');
  window.location.href = '/login';
};

async function apiFetch(path) {
  const r = await fetch(API + path, { headers: getAuthHeader() });
  if (r.status === 401) { handleUnauth(); return null; }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${r.status}`);
  }
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
    body: JSON.stringify(body),
  });
  if (r.status === 401) { handleUnauth(); return null; }
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${r.status}`);
  }
  return r.json();
}

async function apiPut(path, body) {
  const r = await fetch(API + path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
    body: JSON.stringify(body),
  });
  if (r.status === 401) { handleUnauth(); return null; }
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${r.status}`);
  }
  return r.json();
}

async function apiDelete(path) {
  const r = await fetch(API + path, {
    method: 'DELETE',
    headers: getAuthHeader(),
  });
  if (r.status === 401) { handleUnauth(); return null; }
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.detail || `API error ${r.status}`);
  }
  return true;
}

// ── State ─────────────────────────────────────────────────────────────── //

let currentView = 'list';      // 'list' or 'detail'
let currentCampaignId = null;

// ── Render: Campaign List ─────────────────────────────────────────────── //

async function showCampaignList() {
  currentView = 'list';
  currentCampaignId = null;
  const el = document.getElementById('app-content');
  el.innerHTML = '<div class="loading-msg"><div class="spinner"></div><br>Loading campaigns...</div>';

  try {
    const campaigns = await apiFetch('/campaigns');
    if (!campaigns) return;
    renderCampaignList(campaigns);
  } catch (err) {
    el.innerHTML = `<div class="empty-state">Error loading campaigns: ${err.message}</div>`;
  }
}

function renderCampaignList(campaigns) {
  const el = document.getElementById('app-content');

  let html = `
    <div class="panel" style="margin-top:20px;">
      <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>Your Campaigns</span>
        <button class="btn btn-primary btn-sm" onclick="showCreateForm()">+ New Campaign</button>
      </div>
      <div id="create-form-area"></div>`;

  if (campaigns.length === 0) {
    html += `<div class="empty-state">No campaigns yet. Create one to get started.</div>`;
  } else {
    for (const c of campaigns) {
      const memberText = c.member_count === 1 ? '1 member' : `${c.member_count} members`;
      html += `
        <div class="campaign-card" onclick="showCampaignDetail('${c.id}')">
          <div class="campaign-card-name">${esc(c.name)}</div>
          <div class="campaign-card-meta">
            GM: ${esc(c.gm_username || 'Unknown')} &middot; ${memberText}
          </div>
        </div>`;
    }
  }

  html += `</div>`;
  el.innerHTML = html;
}

function showCreateForm() {
  const area = document.getElementById('create-form-area');
  if (!area) return;
  area.innerHTML = `
    <div style="margin:12px 0;">
      <div class="add-form">
        <input type="text" id="new-campaign-name" class="field-input" placeholder="Campaign name" maxlength="255">
        <button class="btn btn-primary btn-sm" onclick="doCreateCampaign()">Create</button>
        <button class="btn btn-sm" onclick="document.getElementById('create-form-area').innerHTML=''">Cancel</button>
      </div>
      <div id="create-error"></div>
    </div>`;
  document.getElementById('new-campaign-name').focus();
}

async function doCreateCampaign() {
  const name = document.getElementById('new-campaign-name').value.trim();
  if (!name) {
    document.getElementById('create-error').innerHTML = '<span class="error-msg">Name is required</span>';
    return;
  }
  try {
    await apiPost('/campaigns', { name });
    showCampaignList();
  } catch (err) {
    document.getElementById('create-error').innerHTML = `<span class="error-msg">${esc(err.message)}</span>`;
  }
}

// ── Render: Campaign Detail ───────────────────────────────────────────── //

async function showCampaignDetail(campaignId) {
  currentView = 'detail';
  currentCampaignId = campaignId;
  const el = document.getElementById('app-content');
  el.innerHTML = '<div class="loading-msg"><div class="spinner"></div><br>Loading campaign...</div>';

  try {
    const [campaign, party, campaignSources, allSources] = await Promise.all([
      apiFetch(`/campaigns/${campaignId}`),
      apiFetch(`/campaigns/${campaignId}/party`),
      apiFetch(`/campaigns/${campaignId}/sources`),
      apiFetch('/sources'),
    ]);
    if (!campaign || !party) return;
    renderCampaignDetail(campaign, party, campaignSources, allSources);
  } catch (err) {
    el.innerHTML = `<div class="empty-state">Error: ${esc(err.message)}</div>`;
  }
}

// Source grouping for UI display
const SOURCE_GROUPS = [
  { label: 'Core Rules', ids: [1] },
  { label: 'Core Supplements', ids: [2, 4, 5, 3, 6, 7, 18, 22] },
  { label: 'Extended', ids: [19, 20, 21, 24, 23, 27] },
  { label: 'Bestiaries', ids: [8, 9, 10, 11] },
  { label: 'Companion / Setting', ids: [29, 28, 30, 31, 32] },
  { label: 'Other', ids: [13, 15, 14, 25, 26, 12, 16] },
];

function renderCampaignDetail(campaign, party, campaignSources, allSources) {
  const el = document.getElementById('app-content');
  const isGm = campaign.is_gm;

  let html = `
    <div style="margin-top:16px;">
      <button class="back-link" onclick="showCampaignList()">&#x2190; All Campaigns</button>
    </div>

    <div class="panel">
      <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>${esc(campaign.name)}</span>
        ${isGm ? `<button class="btn btn-danger btn-sm" onclick="doDeleteCampaign('${campaign.id}')">Delete Campaign</button>` : ''}
      </div>
      <div style="font-family:var(--font-label);font-size:10px;color:var(--fade);letter-spacing:.04em;">
        GM: ${esc(campaign.gm_username)} &middot; ${campaign.members.length} member${campaign.members.length !== 1 ? 's' : ''}
      </div>
    </div>`;

  // ── Members panel ──
  html += `
    <div class="panel">
      <div class="panel-title">Members</div>
      <div>`;

  for (const m of campaign.members) {
    const isGmMember = m.role === 'gm';
    html += `
      <div class="member-row">
        <div>
          <span class="member-name">${esc(m.username)}</span>
          <span class="member-role">${m.role}</span>
        </div>
        ${isGm && !isGmMember ? `<button class="btn btn-danger btn-sm" onclick="doRemoveMember('${campaign.id}','${m.user_id}','${esc(m.username)}')">Remove</button>` : ''}
      </div>`;
  }

  html += `</div>`;

  if (isGm) {
    html += `
      <div class="add-form">
        <input type="text" id="add-member-username" class="field-input" placeholder="Username to invite">
        <button class="btn btn-primary btn-sm" onclick="doAddMember('${campaign.id}')">Add</button>
      </div>
      <div id="member-msg"></div>`;
  }

  html += `</div>`;

  // ── Party overview ──
  html += `
    <div class="panel">
      <div class="panel-title">Party Overview</div>`;

  if (party.length === 0) {
    html += `<div class="empty-state">No characters yet. Members need to create characters first.</div>`;
  } else {
    html += `<div class="party-grid">`;
    for (const pc of party) {
      const sign = v => v >= 0 ? `+${v}` : `${v}`;
      html += `
        <div class="party-card">
          <div class="party-card-player">Player: ${esc(pc.player_username)}</div>
          <div class="party-card-name">${esc(pc.name)}</div>
          <div class="party-card-class">${esc(pc.race)} ${esc(pc.class_str)} (Lv ${pc.total_level})</div>
          <div class="party-stats">
            <div class="party-stat">
              <div class="party-stat-label">HP</div>
              <div class="party-stat-value">${pc.hp_max || '?'}</div>
            </div>
            <div class="party-stat">
              <div class="party-stat-label">AC</div>
              <div class="party-stat-value">${pc.ac ?? '?'}</div>
            </div>
            <div class="party-stat">
              <div class="party-stat-label">Fort</div>
              <div class="party-stat-value">${sign(pc.saves?.fort ?? 0)}</div>
            </div>
            <div class="party-stat">
              <div class="party-stat-label">Ref</div>
              <div class="party-stat-value">${sign(pc.saves?.ref ?? 0)}</div>
            </div>
            <div class="party-stat">
              <div class="party-stat-label">Will</div>
              <div class="party-stat-value">${sign(pc.saves?.will ?? 0)}</div>
            </div>
          </div>
          <div class="party-card-actions">
            <button class="btn btn-sm" onclick="viewSheet('${campaign.id}','${pc.id}')">View Sheet</button>
          </div>
        </div>`;
    }
    html += `</div>`;
  }

  html += `</div>`;

  // ── Allowed Sources panel (GM only) ──
  if (isGm && allSources) {
    const selectedSet = new Set(campaignSources?.source_ids || []);
    const isRestricted = campaignSources?.restricted || false;
    const sourceMap = {};
    for (const s of allSources) sourceMap[s.id] = s;

    html += `
    <div class="panel">
      <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>Allowed Sources</span>
        <span style="font-size:10px;color:var(--fade);font-family:var(--font-label);">
          ${isRestricted ? `${selectedSet.size} of ${allSources.length} sources` : 'All sources allowed (no restriction)'}
        </span>
      </div>
      <div style="font-size:11px;color:var(--fade);margin-bottom:8px;">
        Check sources to restrict content for this campaign. Leave all unchecked to allow everything.
      </div>
      <div id="source-config">`;

    for (const group of SOURCE_GROUPS) {
      const groupSources = group.ids.map(id => sourceMap[id]).filter(Boolean);
      if (groupSources.length === 0) continue;
      html += `<div style="margin-bottom:8px;">
        <div style="font-family:var(--font-label);font-size:10px;letter-spacing:.04em;color:var(--fade);margin-bottom:4px;">${group.label}</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px 12px;">`;
      for (const s of groupSources) {
        const checked = selectedSet.has(s.id) ? 'checked' : '';
        html += `<label style="font-size:12px;display:flex;align-items:center;gap:4px;cursor:pointer;">
          <input type="checkbox" class="source-cb" data-sid="${s.id}" ${checked}>
          <span>${esc(s.abbreviation || s.name)}</span>
          <span style="color:var(--fade);font-size:10px;">${esc(s.name)}</span>
        </label>`;
      }
      html += `</div></div>`;
    }

    html += `</div>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center;">
        <button class="btn btn-primary btn-sm" onclick="doSaveSources('${campaign.id}')">Save Sources</button>
        <button class="btn btn-sm" onclick="doClearSources('${campaign.id}')">Allow All</button>
        <button class="btn btn-sm" onclick="doSelectCoreSources()">Core Only</button>
        <span id="source-msg" style="font-size:11px;"></span>
      </div>
    </div>`;
  }

  el.innerHTML = html;
}

// ── Actions ───────────────────────────────────────────────────────────── //

async function doAddMember(campaignId) {
  const input = document.getElementById('add-member-username');
  const msgEl = document.getElementById('member-msg');
  const username = input.value.trim();
  if (!username) {
    msgEl.innerHTML = '<span class="error-msg">Enter a username</span>';
    return;
  }
  try {
    await apiPost(`/campaigns/${campaignId}/members`, { username });
    msgEl.innerHTML = `<span class="success-msg">Added ${esc(username)}</span>`;
    input.value = '';
    // Refresh the detail view
    setTimeout(() => showCampaignDetail(campaignId), 600);
  } catch (err) {
    msgEl.innerHTML = `<span class="error-msg">${esc(err.message)}</span>`;
  }
}

async function doRemoveMember(campaignId, userId, username) {
  if (!confirm(`Remove ${username} from this campaign?`)) return;
  try {
    await apiDelete(`/campaigns/${campaignId}/members/${userId}`);
    showCampaignDetail(campaignId);
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function doDeleteCampaign(campaignId) {
  if (!confirm('Delete this campaign? This cannot be undone.')) return;
  try {
    await apiDelete(`/campaigns/${campaignId}`);
    showCampaignList();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

async function viewSheet(campaignId, charId) {
  // Fetch sheet HTML via authenticated request, then open in new tab
  try {
    const r = await fetch(`${API}/campaigns/${campaignId}/characters/${charId}/sheet`, {
      headers: getAuthHeader(),
    });
    if (r.status === 401) { handleUnauth(); return; }
    if (!r.ok) throw new Error(`Error ${r.status}`);
    const html = await r.text();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (err) {
    alert(`Could not load sheet: ${err.message}`);
  }
}

// ── Source config actions ─────────────────────────────────────────────── //

async function doSaveSources(campaignId) {
  const checkboxes = document.querySelectorAll('.source-cb');
  const selected = [];
  checkboxes.forEach(cb => { if (cb.checked) selected.push(parseInt(cb.dataset.sid)); });

  const msgEl = document.getElementById('source-msg');
  try {
    await apiPut(`/campaigns/${campaignId}/sources`, { source_ids: selected });
    if (selected.length === 0) {
      msgEl.innerHTML = '<span class="success-msg">Restrictions removed — all sources allowed</span>';
    } else {
      msgEl.innerHTML = `<span class="success-msg">Saved — ${selected.length} sources allowed</span>`;
    }
    setTimeout(() => showCampaignDetail(campaignId), 1200);
  } catch (err) {
    msgEl.innerHTML = `<span class="error-msg">${esc(err.message)}</span>`;
  }
}

async function doClearSources(campaignId) {
  // Uncheck all and save empty list
  document.querySelectorAll('.source-cb').forEach(cb => { cb.checked = false; });
  await doSaveSources(campaignId);
}

function doSelectCoreSources() {
  // Core Rules + Core Supplements: ids 1,2,3,4,5,6,7,18,22
  const coreIds = new Set([1, 2, 3, 4, 5, 6, 7, 18, 22]);
  document.querySelectorAll('.source-cb').forEach(cb => {
    cb.checked = coreIds.has(parseInt(cb.dataset.sid));
  });
}

// ── Util ──────────────────────────────────────────────────────────────── //

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

// ── Init ──────────────────────────────────────────────────────────────── //

(async function init() {
  // Verify auth
  const token = localStorage.getItem('pf1e_token');
  if (!token) { handleUnauth(); return; }
  try {
    const r = await fetch(`${API}/auth/me`, { headers: getAuthHeader() });
    if (!r.ok) { handleUnauth(); return; }
  } catch (_) {
    handleUnauth();
    return;
  }
  showCampaignList();
})();
