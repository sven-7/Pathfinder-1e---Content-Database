// ═══════════════════════════════════════════════════════════════════════
// PF1e Character Creator — Wizard State Machine
// ═══════════════════════════════════════════════════════════════════════

const API = '/api';

const STEPS = [
  { id: 'identity',  label: 'Identity' },
  { id: 'abilities', label: 'Abilities' },
  { id: 'class',     label: 'Class' },
  { id: 'feats',     label: 'Feats & Traits' },
  { id: 'skills',    label: 'Skills' },
  { id: 'review',    label: 'Review' },
];

const ALIGNMENTS = [
  'Lawful Good','Neutral Good','Chaotic Good',
  'Lawful Neutral','True Neutral','Chaotic Neutral',
  'Lawful Evil','Neutral Evil','Chaotic Evil',
];

const ABILITIES_ORDER = ['str','dex','con','int','wis','cha'];
const ABILITY_LABELS  = { str:'STR', dex:'DEX', con:'CON', int:'INT', wis:'WIS', cha:'CHA' };

const STANDARD_ARRAY = [15,14,13,12,10,8];
const PB_COSTS = {7:-4,8:-2,9:-1,10:0,11:1,12:2,13:3,14:5,15:7,16:10,17:13,18:17};
const PB_BUDGET = 25;

// ── Application state ────────────────────────────────────────────────────
const state = {
  currentStep: 0,
  maxReached:  0,

  // Step 1
  name:        '',
  playerName:  '',
  alignment:   'True Neutral',
  race:        null,         // {name, ability_modifiers, flexible_bonus, ...}
  flexBonus:   null,         // chosen ability for flexible +2

  // Step 2
  abilityMethod: 'standard', // 'standard' | 'pointbuy' | 'roll' | 'manual'
  baseScores:  { str:10, dex:10, con:10, int:10, wis:10, cha:10 },
  saAssign:    {},           // standard array: {str:'15', ...}
  rollValues:  null,         // [16, 14, ...] six values
  rollAssign:  {},           // {str: 0, ...} index into rollValues

  // Step 3
  className:   null,
  classRow:    null,
  archetypeName: null,

  // Step 4
  feats:       [],
  traits:      [],

  // Step 5
  skillRanks:  {},

  // Cache
  _races:     null,
  _classes:   null,
  _feats:     null,
  _traits:    null,
  _skills:    null,
  _classSkills: null,        // set of class skill names
};

// ── API helpers ──────────────────────────────────────────────────────────
async function apiFetch(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`API error ${r.status}: ${path}`);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

async function apiPut(path, body) {
  const r = await fetch(API + path, {
    method: 'PUT',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json();
}

// ── Derived helpers ──────────────────────────────────────────────────────
function mod(score) { return Math.floor((score - 10) / 2); }
function modStr(score) {
  const m = mod(score);
  return m >= 0 ? `+${m}` : `${m}`;
}

function getFinalScores() {
  const base = { ...state.baseScores };
  const raceMods = state.race ? (state.race.ability_modifiers || {}) : {};
  const result = { ...base };
  for (const [ab, val] of Object.entries(raceMods)) {
    if (ab in result) result[ab] += val;
  }
  if (state.race?.flexible_bonus && state.flexBonus && state.flexBonus in result) {
    result[state.flexBonus] += 2;
  }
  return result;
}

function computeBaseScores() {
  // Resolve baseScores from current method/assignments
  if (state.abilityMethod === 'standard') {
    const scores = { str:10,dex:10,con:10,int:10,wis:10,cha:10 };
    for (const ab of ABILITIES_ORDER) {
      const val = parseInt(state.saAssign[ab]);
      if (!isNaN(val)) scores[ab] = val;
    }
    state.baseScores = scores;
  } else if (state.abilityMethod === 'pointbuy') {
    // Already maintained live in state.baseScores
  } else if (state.abilityMethod === 'roll') {
    const scores = { str:10,dex:10,con:10,int:10,wis:10,cha:10 };
    for (const ab of ABILITIES_ORDER) {
      const idx = state.rollAssign[ab];
      if (idx !== undefined && state.rollValues) scores[ab] = state.rollValues[idx];
    }
    state.baseScores = scores;
  }
  // 'manual': baseScores is already set directly
}

function skillBudget() {
  if (!state.classRow) return 0;
  const ranksPerLevel = state.classRow.skill_ranks_per_level || 2;
  const intMod = mod(getFinalScores().int);
  let budget = Math.max(1, ranksPerLevel + intMod);
  if (state.race?.name === 'Humans') budget += 1;
  return budget;
}

function usedSkillRanks() {
  return Object.values(state.skillRanks).reduce((s, v) => s + (v || 0), 0);
}

function featBudget() {
  let budget = 1;
  if (state.className === 'Fighter') budget += 1;
  if (state.race?.name === 'Humans' || state.race?.name === 'Half-Elves') budget += 1;
  return budget;
}

// ── Step tracker ─────────────────────────────────────────────────────────
function renderTracker() {
  const el = document.getElementById('step-tracker');
  let html = '';
  STEPS.forEach((step, i) => {
    const isDone   = i < state.currentStep;
    const isActive = i === state.currentStep;
    const isDisabled = i > state.maxReached;
    let cls = 'step-node';
    if (isDone)     cls += ' done';
    if (isActive)   cls += ' active';
    if (isDisabled) cls += ' disabled';

    if (i > 0) {
      const lineCls = 'step-line' + (isDone ? ' done' : isActive ? ' active' : '');
      html += `<div class="${lineCls}"></div>`;
    }
    html += `<div class="${cls}" onclick="goToStep(${i})">
      <div class="step-dot">${isDone ? '✓' : i + 1}</div>
      <div class="step-label">${step.label}</div>
    </div>`;
  });
  el.innerHTML = html;
}

function goToStep(i) {
  if (i > state.maxReached) return;
  // Validate forward navigation
  if (i > state.currentStep) {
    const errors = validateCurrentStep();
    if (errors.length) { showErrors(errors); return; }
    syncCurrentStepState();
  }
  state.currentStep = i;
  state.maxReached = Math.max(state.maxReached, i);
  renderTracker();
  renderStep();
}

function showErrors(errs) {
  const el = document.getElementById('nav-error');
  if (el) {
    el.textContent = errs.join(' · ');
    setTimeout(() => { if (el) el.textContent = ''; }, 4000);
  }
}

// ── Step rendering dispatcher ────────────────────────────────────────────
async function renderStep() {
  const container = document.getElementById('step-content');
  container.innerHTML = '<div class="loading-msg"><div class="spinner"></div></div>';
  try {
    switch (state.currentStep) {
      case 0: await renderIdentityStep(container); break;
      case 1: await renderAbilitiesStep(container); break;
      case 2: await renderClassStep(container); break;
      case 3: await renderFeatsTraitsStep(container); break;
      case 4: await renderSkillsStep(container); break;
      case 5: await renderReviewStep(container); break;
    }
  } catch(e) {
    container.innerHTML = `<div class="panel"><p class="text-red">Error: ${e.message}</p></div>`;
  }
}

// ── Step 0: Identity + Race ──────────────────────────────────────────────
async function renderIdentityStep(c) {
  if (!state._races) state._races = await apiFetch('/races');
  const races = state._races;

  // Group by type
  const coreRaces = races.filter(r => r.race_type === 'core');
  const otherRaces = races.filter(r => r.race_type !== 'core');

  c.innerHTML = `
  <div class="row">
    <div class="col-2">
      <div class="panel">
        <div class="panel-title">Identity</div>
        <div class="row gap-sm">
          <div class="col">
            <div class="field-group">
              <label class="field-label">Character Name *</label>
              <input class="field-input" id="inp-name" value="${esc(state.name)}" placeholder="Enter character name…">
            </div>
          </div>
          <div class="col">
            <div class="field-group">
              <label class="field-label">Player Name</label>
              <input class="field-input" id="inp-player" value="${esc(state.playerName)}" placeholder="Optional">
            </div>
          </div>
        </div>
        <div class="field-group">
          <label class="field-label">Alignment</label>
          <select class="field-select" id="inp-alignment">
            ${ALIGNMENTS.map(a => `<option ${a===state.alignment?'selected':''}>${a}</option>`).join('')}
          </select>
        </div>
      </div>

      <div class="panel">
        <div class="panel-title">Race</div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="race-search" placeholder="Search races…" oninput="filterRaces()">
        </div>

        <div style="margin-bottom:8px;">
          <span class="field-label" style="display:inline;">Core Races: </span>
          ${coreRaces.map(r => `
            <span class="tag${state.race?.name===r.name?' selected':''}"
              style="${state.race?.name===r.name?'background:var(--gold-bg);border-color:var(--gold);':''}"
              onclick="selectRace(${JSON.stringify(r.name)})">
              ${r.name}
            </span>`).join('')}
        </div>

        <div class="scroll-list" style="max-height:200px;" id="race-list">
          ${races.map(r => `
            <div class="list-item${state.race?.name===r.name?' selected':''}"
                 data-name="${esc(r.name)}"
                 onclick="selectRace(${JSON.stringify(r.name)})">
              <div>
                <div class="list-item-name">${r.name}</div>
                <div class="list-item-detail">${r.size} · Speed ${r.base_speed}ft</div>
              </div>
              <div class="list-item-type">${r.race_type || ''}</div>
            </div>`).join('')}
        </div>
      </div>
    </div>

    <div class="col-sm">
      <div class="panel" style="min-height:200px;" id="race-preview">
        ${state.race ? racePreviewHtml(state.race) : '<p class="text-muted" style="font-size:12px;">Select a race to see details.</p>'}
      </div>
    </div>
  </div>

  <div class="nav-bar">
    <div></div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Ability Scores →</button>
    </div>
  </div>`;
}

function racePreviewHtml(race) {
  const mods = race.ability_modifiers || {};
  const modChips = Object.entries(mods).map(([ab, v]) =>
    `<span class="race-mod-chip ${v>0?'positive':'negative'}">${v>0?'+':''}${v} ${ab.toUpperCase()}</span>`
  ).join('');
  const flexHtml = race.flexible_bonus
    ? `<span class="race-mod-chip positive">+2 Any (choice)</span>` : '';

  return `<div class="race-detail">
    <h4>${race.name}</h4>
    <div class="race-mods">${modChips}${flexHtml}</div>
    <div><b>Size:</b> ${race.size || 'Medium'} &nbsp;|&nbsp; <b>Speed:</b> ${race.base_speed || 30}ft</div>
    ${race.flexible_bonus ? flexBonusSelector(race) : ''}
    <p class="text-muted mt-sm" style="font-size:11px;">${(race.description||'').slice(0,200)}${race.description?.length>200?'…':''}</p>
  </div>`;
}

function flexBonusSelector(race) {
  return `<div class="field-group mt-sm">
    <label class="field-label">+2 Ability Score Bonus</label>
    <select class="field-select" id="flex-bonus" onchange="state.flexBonus=this.value">
      <option value="">— Choose ability —</option>
      ${ABILITIES_ORDER.map(ab =>
        `<option value="${ab}" ${state.flexBonus===ab?'selected':''}>${ABILITY_LABELS[ab]}</option>`
      ).join('')}
    </select>
  </div>`;
}

window.selectRace = async function(name) {
  const race = state._races.find(r => r.name === name);
  state.race = race;
  if (!race?.flexible_bonus) state.flexBonus = null;
  document.getElementById('race-preview').innerHTML = race ? racePreviewHtml(race) : '';
  // Update list selection
  document.querySelectorAll('#race-list .list-item').forEach(el => {
    el.classList.toggle('selected', el.dataset.name === name);
  });
};

window.filterRaces = function() {
  const q = document.getElementById('race-search').value.toLowerCase();
  document.querySelectorAll('#race-list .list-item').forEach(el => {
    el.style.display = el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
};

// ── Step 1: Ability Scores ───────────────────────────────────────────────
async function renderAbilitiesStep(c) {
  c.innerHTML = `
  <div class="panel">
    <div class="panel-title">Ability Score Generation</div>
    <div class="method-tabs">
      <div class="method-tab${state.abilityMethod==='standard'?' active':''}" onclick="setAbilityMethod('standard')">Standard Array</div>
      <div class="method-tab${state.abilityMethod==='pointbuy'?' active':''}" onclick="setAbilityMethod('pointbuy')">Point Buy</div>
      <div class="method-tab${state.abilityMethod==='roll'?' active':''}" onclick="setAbilityMethod('roll')">Roll 4d6</div>
      <div class="method-tab${state.abilityMethod==='manual'?' active':''}" onclick="setAbilityMethod('manual')">Manual</div>
    </div>
    <div id="ability-method-panel"></div>
  </div>

  <div class="panel" id="ability-preview">
    ${abilityPreviewHtml()}
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Class →</button>
    </div>
  </div>`;

  renderAbilityMethodPanel();
}

window.setAbilityMethod = function(method) {
  state.abilityMethod = method;
  document.querySelectorAll('.method-tab').forEach((t, i) => {
    t.classList.toggle('active', ['standard','pointbuy','roll','manual'][i] === method);
  });
  renderAbilityMethodPanel();
};

function renderAbilityMethodPanel() {
  const panel = document.getElementById('ability-method-panel');
  if (!panel) return;
  switch(state.abilityMethod) {
    case 'standard': panel.innerHTML = renderStandardArray(); break;
    case 'pointbuy': panel.innerHTML = renderPointBuy(); break;
    case 'roll':     panel.innerHTML = renderRoll(); break;
    case 'manual':   panel.innerHTML = renderManual(); break;
  }
}

function renderStandardArray() {
  // Check for duplicate assignments
  const used = {};
  for (const [ab, val] of Object.entries(state.saAssign)) {
    if (val) used[val] = (used[val] || 0) + 1;
  }
  const hasDup = Object.values(used).some(c => c > 1);

  return `<p class="text-muted" style="font-size:12px;margin-bottom:12px;">
    Assign each value from [${STANDARD_ARRAY.join(', ')}] to one ability score.
  </p>
  ${ABILITIES_ORDER.map(ab => {
    const v = state.saAssign[ab] || '';
    return `<div class="ability-assign-row">
      <div class="ability-assign-label">${ABILITY_LABELS[ab]}</div>
      <select class="ability-assign-select" onchange="setSA('${ab}',this.value)">
        <option value="">—</option>
        ${STANDARD_ARRAY.map(s => `<option value="${s}" ${v==s?'selected':''}>${s}</option>`).join('')}
      </select>
      <div class="ability-assign-mod" id="sa-mod-${ab}">${v ? modStr(+v) : '—'}</div>
    </div>`;
  }).join('')}
  ${hasDup ? '<p class="text-red mt-sm" style="font-size:11px;">⚠ Each value may only be assigned once.</p>' : ''}`;
}

window.setSA = function(ab, val) {
  state.saAssign[ab] = val;
  computeBaseScores();
  document.getElementById('ability-preview').innerHTML = abilityPreviewHtml();
  renderAbilityMethodPanel();
};

function renderPointBuy() {
  const scores = state.baseScores;
  const totalCost = Object.values(scores).reduce((s, v) => s + (PB_COSTS[v] || 0), 0);
  const remaining = PB_BUDGET - totalCost;

  return `<div class="pb-budget">
    <div class="pb-budget-label">Points Remaining</div>
    <div class="pb-budget-number ${remaining < 0 ? 'over' : ''}">${remaining}</div>
    <div class="text-muted" style="font-size:10px;">of ${PB_BUDGET}</div>
  </div>
  ${ABILITIES_ORDER.map(ab => {
    const v = scores[ab] || 10;
    const cost = PB_COSTS[v] || 0;
    return `<div class="pb-row">
      <div class="pb-label">${ABILITY_LABELS[ab]}</div>
      <div class="pb-stepper">
        <button class="pb-btn" onclick="pbChange('${ab}',-1)" ${v<=7?'disabled':''}>−</button>
        <div class="pb-score">${v}</div>
        <button class="pb-btn" onclick="pbChange('${ab}',+1)" ${v>=18||remaining<=0?'disabled':''}>+</button>
      </div>
      <div class="pb-cost">Cost: ${cost >= 0 ? cost : cost}</div>
      <div class="pb-mod ${mod(v)>0?'positive':mod(v)<0?'negative':''}">${modStr(v)}</div>
    </div>`;
  }).join('')}`;
}

window.pbChange = function(ab, delta) {
  const current = state.baseScores[ab] || 10;
  const next = current + delta;
  if (next < 7 || next > 18) return;
  const totalCost = Object.values(state.baseScores).reduce((s,v) => s + (PB_COSTS[v]||0), 0);
  if (delta > 0 && totalCost >= PB_BUDGET) return;
  state.baseScores[ab] = next;
  renderAbilityMethodPanel();
  document.getElementById('ability-preview').innerHTML = abilityPreviewHtml();
};

function renderRoll() {
  if (!state.rollValues) {
    return `<div style="text-align:center;padding:20px;">
      <button class="btn btn-primary" onclick="doRoll()">🎲 Roll 4d6 Drop Lowest</button>
    </div>`;
  }
  return `<div style="text-align:center;padding:8px 0 16px;">
    <button class="btn" onclick="doRoll()">🎲 Re-roll</button>
  </div>
  <p class="text-muted" style="font-size:12px;margin-bottom:12px;">Assign each rolled value to an ability score.</p>
  ${ABILITIES_ORDER.map(ab => {
    const assigned = state.rollAssign[ab];
    return `<div class="ability-assign-row">
      <div class="ability-assign-label">${ABILITY_LABELS[ab]}</div>
      <select class="ability-assign-select" onchange="setRollAssign('${ab}',this.value)">
        <option value="">—</option>
        ${state.rollValues.map((v,i) => `<option value="${i}" ${assigned===i?'selected':''}>${v}</option>`).join('')}
      </select>
      <div class="ability-assign-mod">${assigned !== undefined ? modStr(state.rollValues[assigned]) : '—'}</div>
    </div>`;
  }).join('')}`;
}

window.doRoll = async function() {
  const r = await apiFetch('/feats?search=__none__');  // dummy call to warm connection
  // Roll client-side (same logic as server)
  state.rollValues = Array.from({length:6}, () => {
    const d = Array.from({length:4}, () => 1 + Math.floor(Math.random()*6));
    d.sort((a,b)=>a-b); return d[1]+d[2]+d[3];
  });
  state.rollAssign = {};
  renderAbilityMethodPanel();
};

window.setRollAssign = function(ab, idx) {
  state.rollAssign[ab] = idx === '' ? undefined : parseInt(idx);
  computeBaseScores();
  document.getElementById('ability-preview').innerHTML = abilityPreviewHtml();
};

function renderManual() {
  return `<p class="text-muted" style="font-size:12px;margin-bottom:12px;">Enter scores directly (before racial modifiers).</p>
  ${ABILITIES_ORDER.map(ab => {
    const v = state.baseScores[ab] || 10;
    return `<div class="ability-assign-row">
      <div class="ability-assign-label">${ABILITY_LABELS[ab]}</div>
      <input type="number" class="ability-assign-select" style="width:80px;" min="3" max="20"
             value="${v}" onchange="setManual('${ab}',this.value)">
      <div class="ability-assign-mod">${modStr(v)}</div>
    </div>`;
  }).join('')}`;
}

window.setManual = function(ab, val) {
  state.baseScores[ab] = Math.max(3, Math.min(20, parseInt(val)||10));
  document.getElementById('ability-preview').innerHTML = abilityPreviewHtml();
};

function abilityPreviewHtml() {
  computeBaseScores();
  const final = getFinalScores();
  const raceMods = state.race?.ability_modifiers || {};

  return `<div class="panel-title">Final Ability Scores
    ${state.race ? `<span class="text-muted" style="font-size:10px;font-weight:400;">(after ${state.race.name} racial modifiers)</span>` : ''}
  </div>
  <div class="ability-grid">
    ${ABILITIES_ORDER.map(ab => {
      const score = final[ab] || 10;
      const m = mod(score);
      const racial = (raceMods[ab] || 0) + (state.race?.flexible_bonus && state.flexBonus===ab ? 2 : 0);
      const mCls = m > 0 ? 'positive' : m < 0 ? 'negative' : '';
      return `<div class="ability-cell">
        <div class="ability-name">${ABILITY_LABELS[ab]}</div>
        <div class="ability-score">${score}</div>
        <div class="ability-mod ${mCls}">${modStr(score)}</div>
        ${racial ? `<div class="text-muted" style="font-size:9px;">(${racial>0?'+':''}${racial} racial)</div>` : ''}
      </div>`;
    }).join('')}
  </div>`;
}

// ── Step 2: Class + Archetype ────────────────────────────────────────────
async function renderClassStep(c) {
  if (!state._classes) state._classes = await apiFetch('/classes');
  const classes = state._classes;

  const groups = {};
  classes.forEach(cls => {
    const g = cls.class_type || 'other';
    if (!groups[g]) groups[g] = [];
    groups[g].push(cls);
  });

  const typeLabels = {
    base:'Base Classes', hybrid:'Hybrid Classes', unchained:'Unchained',
    occult:'Occult Adventures', prestige:'Prestige Classes', alternate:'Alternate Classes',
  };

  c.innerHTML = `
  <div class="row">
    <div class="col-2">
      <div class="panel">
        <div class="panel-title">Class</div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="class-search" placeholder="Search classes…" oninput="filterClasses()">
        </div>
        <div class="scroll-list" style="max-height:320px;" id="class-list">
          ${Object.entries(groups).map(([type, clsList]) => `
            <div style="padding:4px 12px;background:var(--paper-dark);border-bottom:1px solid var(--gold-border);">
              <span style="font-family:var(--font-label);font-size:8px;color:var(--gold);letter-spacing:.08em;">${typeLabels[type]||type.toUpperCase()}</span>
            </div>
            ${clsList.map(cls => `
              <div class="list-item${state.className===cls.name?' selected':''}"
                   data-name="${esc(cls.name)}"
                   onclick="selectClass(${JSON.stringify(cls.name)})">
                <div>
                  <div class="list-item-name">${cls.name}</div>
                  <div class="list-item-detail">${cls.hit_die} · ${cls.skill_ranks_per_level} skills/lvl · BAB ${cls.bab_progression}</div>
                </div>
                ${cls.spellcasting_type ? `<div class="list-item-type">${cls.spellcasting_type}</div>` : ''}
              </div>`).join('')}
          `).join('')}
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel" id="class-preview">
        ${state.classRow ? classPreviewHtml(state.classRow) : '<p class="text-muted" style="font-size:12px;">Select a class.</p>'}
      </div>
    </div>
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Feats & Traits →</button>
    </div>
  </div>`;
}

function classPreviewHtml(cls) {
  const saves = [];
  if (cls.fort_progression === 'good') saves.push('Fort');
  if (cls.ref_progression === 'good')  saves.push('Ref');
  if (cls.will_progression === 'good') saves.push('Will');

  return `<div class="panel-title">${cls.name}</div>
  <div class="row gap-sm" style="margin-bottom:12px;flex-wrap:wrap;">
    <div class="stat-box"><div class="stat-box-label">Hit Die</div><div class="stat-box-value">${cls.hit_die||'d8'}</div></div>
    <div class="stat-box"><div class="stat-box-label">BAB</div><div class="stat-box-value" style="font-size:14px;">${cls.bab_progression||'—'}</div></div>
    <div class="stat-box"><div class="stat-box-label">Skills/Lvl</div><div class="stat-box-value">${cls.skill_ranks_per_level||2}</div></div>
    <div class="stat-box"><div class="stat-box-label">Good Saves</div><div class="stat-box-value" style="font-size:12px;">${saves.join(', ')||'—'}</div></div>
  </div>
  ${cls.spellcasting_type ? `<div class="text-muted" style="font-size:11px;margin-bottom:8px;">
    <b>Spellcasting:</b> ${cls.spellcasting_type} (${cls.spellcasting_style||'—'})
  </div>` : ''}
  ${cls.alignment_restriction ? `<div class="text-muted" style="font-size:11px;margin-bottom:8px;">
    <b>Alignment:</b> ${cls.alignment_restriction}
  </div>` : ''}
  <div id="archetype-section"></div>`;
}

window.selectClass = async function(name) {
  const cls = state._classes.find(c => c.name === name);
  state.className = name;
  state.classRow = cls;
  state.archetypeName = null;
  state._classSkills = null;

  document.querySelectorAll('#class-list .list-item').forEach(el => {
    el.classList.toggle('selected', el.dataset.name === name);
  });
  document.getElementById('class-preview').innerHTML = classPreviewHtml(cls);

  // Load archetypes
  const archetypes = await apiFetch(`/classes/${encodeURIComponent(name)}/archetypes`);
  const archSection = document.getElementById('archetype-section');
  if (!archSection) return;
  if (archetypes.length === 0) {
    archSection.innerHTML = '<p class="text-muted" style="font-size:11px;">No archetypes available.</p>';
    return;
  }
  archSection.innerHTML = `
    <div class="panel-title" style="margin-top:12px;">Archetype (Optional)</div>
    <select class="field-select" id="archetype-select" onchange="state.archetypeName=this.value||null">
      <option value="">— None (base class) —</option>
      ${archetypes.map(a => `<option value="${esc(a.name)}" ${state.archetypeName===a.name?'selected':''}>${a.name}</option>`).join('')}
    </select>`;
};

window.filterClasses = function() {
  const q = document.getElementById('class-search').value.toLowerCase();
  document.querySelectorAll('#class-list .list-item').forEach(el => {
    el.style.display = el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
};

// ── Step 3: Feats + Traits ───────────────────────────────────────────────
async function renderFeatsTraitsStep(c) {
  if (!state._feats) state._feats = await apiFetch('/feats');
  if (!state._traits) state._traits = await apiFetch('/traits');

  const budget = featBudget();

  c.innerHTML = `
  <div class="row">
    <div class="col-2">
      <div class="panel">
        <div class="panel-title">Feats
          <span class="text-muted" style="font-weight:400;font-size:10px;"> — ${state.feats.length}/${budget} selected</span>
        </div>
        <div style="margin-bottom:10px;">
          ${state.feats.map(f => `<span class="tag">${f}<button class="tag-remove" onclick="removeFeat(${JSON.stringify(f)})">✕</button></span>`).join('')}
          ${state.feats.length === 0 ? '<span class="text-muted" style="font-size:12px;">No feats selected.</span>' : ''}
        </div>

        <div class="field-group">
          <label class="field-label">Filter by Type</label>
          <select class="field-select" id="feat-type-filter" onchange="filterFeats()">
            <option value="">All Types</option>
            ${[...new Set(state._feats.map(f=>f.feat_type))].sort()
              .map(t => `<option>${t}</option>`).join('')}
          </select>
        </div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="feat-search" placeholder="Search feats…" oninput="filterFeats()">
        </div>
        <div class="scroll-list" style="max-height:260px;" id="feat-list">
          ${featListHtml(state._feats)}
        </div>
      </div>
    </div>

    <div class="col">
      <div class="panel">
        <div class="panel-title">Traits
          <span class="text-muted" style="font-weight:400;font-size:10px;"> — ${state.traits.length}/2</span>
        </div>
        <div style="margin-bottom:10px;">
          ${state.traits.map(t => `<span class="tag">${t}<button class="tag-remove" onclick="removeTrait(${JSON.stringify(t)})">✕</button></span>`).join('')}
          ${state.traits.length === 0 ? '<span class="text-muted" style="font-size:12px;">No traits selected.</span>' : ''}
        </div>
        <div class="field-group">
          <label class="field-label">Filter by Type</label>
          <select class="field-select" id="trait-type-filter" onchange="filterTraits()">
            <option value="">All Types</option>
            ${[...new Set(state._traits.map(t=>t.trait_type))].sort()
              .map(t => `<option>${t}</option>`).join('')}
          </select>
        </div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="trait-search" placeholder="Search traits…" oninput="filterTraits()">
        </div>
        <div class="scroll-list" style="max-height:260px;" id="trait-list">
          ${traitListHtml(state._traits)}
        </div>
      </div>
    </div>
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Skills →</button>
    </div>
  </div>`;
}

function featListHtml(feats) {
  return feats.slice(0, 300).map(f => `
    <div class="list-item${state.feats.includes(f.name)?' selected':''}"
         data-name="${esc(f.name)}" data-type="${esc(f.feat_type)}"
         onclick="toggleFeat(${JSON.stringify(f.name)})">
      <div>
        <div class="list-item-name">${f.name}</div>
        ${f.prerequisites ? `<div class="list-item-detail">Req: ${f.prerequisites.slice(0,80)}${f.prerequisites.length>80?'…':''}</div>` : ''}
      </div>
      <div class="list-item-type">${f.feat_type}</div>
    </div>`).join('');
}

function traitListHtml(traits) {
  return traits.slice(0, 200).map(t => `
    <div class="list-item${state.traits.includes(t.name)?' selected':''}"
         data-name="${esc(t.name)}" data-type="${esc(t.trait_type)}"
         onclick="toggleTrait(${JSON.stringify(t.name)})">
      <div>
        <div class="list-item-name">${t.name}</div>
        ${t.benefit ? `<div class="list-item-detail">${t.benefit.slice(0,80)}${t.benefit.length>80?'…':''}</div>` : ''}
      </div>
      <div class="list-item-type">${t.trait_type}</div>
    </div>`).join('');
}

window.toggleFeat = function(name) {
  if (state.feats.includes(name)) {
    state.feats = state.feats.filter(f => f !== name);
  } else {
    if (state.feats.length >= featBudget()) {
      showErrors([`Maximum ${featBudget()} feats allowed at level 1.`]);
      return;
    }
    state.feats.push(name);
  }
  // Re-render feats step
  renderFeatsTraitsStep(document.getElementById('step-content'));
};

window.removeFeat = function(name) {
  state.feats = state.feats.filter(f => f !== name);
  renderFeatsTraitsStep(document.getElementById('step-content'));
};

window.toggleTrait = function(name) {
  if (state.traits.includes(name)) {
    state.traits = state.traits.filter(t => t !== name);
  } else {
    if (state.traits.length >= 2) {
      showErrors(['Maximum 2 traits allowed.']);
      return;
    }
    state.traits.push(name);
  }
  renderFeatsTraitsStep(document.getElementById('step-content'));
};

window.removeTrait = function(name) {
  state.traits = state.traits.filter(t => t !== name);
  renderFeatsTraitsStep(document.getElementById('step-content'));
};

window.filterFeats = function() {
  const q = (document.getElementById('feat-search')?.value || '').toLowerCase();
  const t = document.getElementById('feat-type-filter')?.value || '';
  document.querySelectorAll('#feat-list .list-item').forEach(el => {
    const nameMatch = !q || el.dataset.name.toLowerCase().includes(q);
    const typeMatch = !t || el.dataset.type === t;
    el.style.display = (nameMatch && typeMatch) ? '' : 'none';
  });
};

window.filterTraits = function() {
  const q = (document.getElementById('trait-search')?.value || '').toLowerCase();
  const t = document.getElementById('trait-type-filter')?.value || '';
  document.querySelectorAll('#trait-list .list-item').forEach(el => {
    const nameMatch = !q || el.dataset.name.toLowerCase().includes(q);
    const typeMatch = !t || el.dataset.type === t;
    el.style.display = (nameMatch && typeMatch) ? '' : 'none';
  });
};

// ── Step 4: Skills ───────────────────────────────────────────────────────
async function renderSkillsStep(c) {
  if (!state._skills) state._skills = await apiFetch('/skills');
  if (!state._classSkills && state.className) {
    const names = await apiFetch(`/skills/class/${encodeURIComponent(state.className)}`);
    state._classSkills = new Set(names.map(n => n.toLowerCase()));
  } else if (!state._classSkills) {
    state._classSkills = new Set();
  }

  const budget = skillBudget();
  const used = usedSkillRanks();
  const remaining = budget - used;
  const finalScores = getFinalScores();

  c.innerHTML = `
  <div class="panel">
    <div class="panel-title">Skill Ranks</div>
    <div class="skill-budget-bar">
      <span>Available ranks at level 1</span>
      <span class="skill-budget-count ${remaining < 0 ? 'depleted' : ''}">${remaining} / ${budget}</span>
    </div>
    <p class="text-muted" style="font-size:11px;margin-bottom:10px;">
      <b style="color:var(--green);">Bold green</b> = class skill (gains +3 bonus when ranked)
    </p>
    <div style="overflow-x:auto;">
    <table class="skill-list-table">
      <thead>
        <tr>
          <th>Skill</th>
          <th>Ability</th>
          <th>Ranks</th>
          <th>Mod</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        ${state._skills.map(sk => {
          const isCS = state._classSkills.has(sk.name.toLowerCase());
          const ranks = state.skillRanks[sk.name] || 0;
          const abilMod = mod(finalScores[sk.ability] || 10);
          const trained = ranks > 0 && isCS ? 3 : 0;
          const total = ranks + abilMod + trained;
          return `<tr class="${isCS?'class-skill':''}">
            <td class="${isCS?'skill-cs':''}">${sk.name}${sk.trained_only?'*':''}</td>
            <td>${sk.ability.toUpperCase()}</td>
            <td>
              <div class="rank-stepper">
                <button class="rank-btn" onclick="changeRank('${esc(sk.name)}',-1)" ${ranks<=0?'disabled':''}>−</button>
                <span class="rank-val">${ranks}</span>
                <button class="rank-btn" onclick="changeRank('${esc(sk.name)}',1)" ${remaining<=0||ranks>=1?'disabled':''}>+</button>
              </div>
            </td>
            <td style="text-align:center">${modStr(finalScores[sk.ability]||10)}</td>
            <td class="skill-total-val" style="color:${total>0?'var(--green)':total<0?'var(--red-wax)':'var(--ink)'}">
              ${total >= 0 ? '+' : ''}${total}
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
    </div>
    <p class="text-muted" style="font-size:10px;margin-top:6px;">* Trained only</p>
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Review →</button>
    </div>
  </div>`;
}

window.changeRank = function(skillName, delta) {
  const current = state.skillRanks[skillName] || 0;
  const budget = skillBudget();
  const used = usedSkillRanks();
  if (delta > 0 && used >= budget) return;
  if (delta < 0 && current <= 0) return;
  if (delta > 0 && current >= 1) return; // max 1 rank at level 1
  state.skillRanks[skillName] = Math.max(0, current + delta);
  renderSkillsStep(document.getElementById('step-content'));
};

// ── Step 5: Review ───────────────────────────────────────────────────────
async function renderReviewStep(c) {
  computeBaseScores();
  const final = getFinalScores();
  const classRow = state.classRow;

  // Compute derived stats client-side
  const intMod = mod(final.int);
  const wisMod = mod(final.wis);
  const conMod = mod(final.con);
  const dexMod = mod(final.dex);
  const strMod = mod(final.str);

  let bab = 0, fort_base = 0, ref_base = 0, will_base = 0;
  const hitDie = classRow?.hit_die || 'd8';
  const avgMap = {d6:4,d8:5,d10:6,d12:7};
  const hp = Math.max(1, (avgMap[hitDie]||5) + conMod);
  // Simple BAB calc from classRow
  if (classRow) {
    bab = classRow.bab_progression === 'full' ? 1 : classRow.bab_progression === 'three_quarter' ? 0 : 0;
    fort_base = classRow.fort_progression === 'good' ? 2 : 0;
    ref_base  = classRow.ref_progression === 'good' ? 2 : 0;
    will_base = classRow.will_progression === 'good' ? 2 : 0;
  }
  const fort = fort_base + conMod;
  const ref  = ref_base  + dexMod;
  const will = will_base + wisMod;
  const ac   = 10 + dexMod;
  const initiative = dexMod;

  c.innerHTML = `
  <div class="panel">
    <div class="panel-title">Character Summary</div>
    <div class="review-grid">
      <div>
        <div class="review-section">
          <div class="review-section-title">Identity</div>
          <div class="review-row"><span class="review-key">Name</span><span class="review-val">${esc(state.name||'—')}</span></div>
          <div class="review-row"><span class="review-key">Player</span><span class="review-val">${esc(state.playerName||'—')}</span></div>
          <div class="review-row"><span class="review-key">Alignment</span><span class="review-val">${state.alignment}</span></div>
          <div class="review-row"><span class="review-key">Race</span><span class="review-val">${state.race?.name||'—'}</span></div>
          <div class="review-row"><span class="review-key">Class</span><span class="review-val">${state.className||'—'}${state.archetypeName?' ('+state.archetypeName+')':''}</span></div>
          <div class="review-row"><span class="review-key">Level</span><span class="review-val">1</span></div>
        </div>

        <div class="review-section">
          <div class="review-section-title">Ability Scores</div>
          ${ABILITIES_ORDER.map(ab => `
            <div class="review-row">
              <span class="review-key">${ABILITY_LABELS[ab]}</span>
              <span class="review-val">${final[ab]} (${modStr(final[ab])})</span>
            </div>`).join('')}
        </div>

        <div class="review-section">
          <div class="review-section-title">Feats (${state.feats.length})</div>
          ${state.feats.length ? state.feats.map(f => `<div class="review-row"><span class="review-val">${f}</span></div>`).join('') : '<div class="text-muted" style="font-size:11px;">None selected</div>'}
        </div>

        <div class="review-section">
          <div class="review-section-title">Traits (${state.traits.length})</div>
          ${state.traits.length ? state.traits.map(t => `<div class="review-row"><span class="review-val">${t}</span></div>`).join('') : '<div class="text-muted" style="font-size:11px;">None selected</div>'}
        </div>
      </div>

      <div>
        <div class="review-section">
          <div class="review-section-title">Combat Stats</div>
          <div class="review-row"><span class="review-key">HP (avg)</span><span class="review-val">${hp}</span></div>
          <div class="review-row"><span class="review-key">AC</span><span class="review-val">${ac} (touch ${ac}, FF ${10})</span></div>
          <div class="review-row"><span class="review-key">BAB</span><span class="review-val">${bab >= 0 ? '+'+bab : bab}</span></div>
          <div class="review-row"><span class="review-key">Initiative</span><span class="review-val">${initiative >= 0 ? '+'+initiative : initiative}</span></div>
          <div class="review-row"><span class="review-key">Fort Save</span><span class="review-val">${fort >= 0 ? '+'+fort : fort}</span></div>
          <div class="review-row"><span class="review-key">Ref Save</span><span class="review-val">${ref >= 0 ? '+'+ref : ref}</span></div>
          <div class="review-row"><span class="review-key">Will Save</span><span class="review-val">${will >= 0 ? '+'+will : will}</span></div>
          <div class="review-row"><span class="review-key">CMB</span><span class="review-val">${bab+strMod >= 0 ? '+'+(bab+strMod) : bab+strMod}</span></div>
          <div class="review-row"><span class="review-key">CMD</span><span class="review-val">${10+bab+strMod+dexMod}</span></div>
        </div>

        <div class="review-section">
          <div class="review-section-title">Skill Ranks (${usedSkillRanks()} / ${skillBudget()})</div>
          ${Object.entries(state.skillRanks).filter(([,v])=>v>0).map(([sk,r]) =>
            `<div class="review-row"><span class="review-key">${sk}</span><span class="review-val">${r} rank</span></div>`
          ).join('') || '<div class="text-muted" style="font-size:11px;">No ranks allocated</div>'}
        </div>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-title">Export</div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      <button class="btn btn-primary" onclick="saveAndViewSheet()">💾 Save & View Sheet</button>
      <button class="btn" onclick="downloadJSON()">⬇ Download JSON</button>
      <button class="btn" onclick="saveCharacter()">📁 Save to Library</button>
    </div>
    <p class="text-muted mt-sm" style="font-size:11px;">
      "Save & View Sheet" generates a complete character sheet in a new tab.
    </p>
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div></div>
  </div>`;
}

// ── Navigation ───────────────────────────────────────────────────────────
function validateCurrentStep() {
  switch(state.currentStep) {
    case 0:
      if (!state.name.trim()) return ['Character name is required.'];
      if (!state.race) return ['Please select a race.'];
      if (state.race.flexible_bonus && !state.flexBonus)
        return ['Please choose your +2 ability score bonus.'];
      return [];
    case 1:
      const final = getFinalScores();
      if (Object.values(final).some(v => v < 3)) return ['Ability scores cannot be below 3.'];
      if (state.abilityMethod === 'pointbuy') {
        const cost = Object.values(state.baseScores).reduce((s,v)=>s+(PB_COSTS[v]||0),0);
        if (cost > PB_BUDGET) return [`Point buy over budget by ${cost - PB_BUDGET} points.`];
      }
      if (state.abilityMethod === 'standard') {
        const assigned = Object.values(state.saAssign).filter(Boolean).map(Number);
        if (assigned.length < 6) return ['Assign all 6 ability scores.'];
        const dups = assigned.filter((v,i) => assigned.indexOf(v) !== i);
        if (dups.length) return ['Each value can only be assigned once.'];
      }
      return [];
    case 2:
      if (!state.className) return ['Please select a class.'];
      return [];
    case 3: return [];
    case 4:
      if (usedSkillRanks() > skillBudget()) return ['Too many skill ranks allocated.'];
      return [];
    case 5: return [];
  }
  return [];
}

function syncCurrentStepState() {
  if (state.currentStep === 0) {
    state.name       = document.getElementById('inp-name')?.value?.trim() || state.name;
    state.playerName = document.getElementById('inp-player')?.value?.trim() || state.playerName;
    state.alignment  = document.getElementById('inp-alignment')?.value || state.alignment;
    const flex = document.getElementById('flex-bonus');
    if (flex) state.flexBonus = flex.value || null;
  }
}

window.nextStep = function() {
  syncCurrentStepState();
  const errors = validateCurrentStep();
  if (errors.length) { showErrors(errors); return; }
  if (state.currentStep < STEPS.length - 1) {
    state.currentStep++;
    state.maxReached = Math.max(state.maxReached, state.currentStep);
    renderTracker();
    renderStep();
  }
};

window.prevStep = function() {
  syncCurrentStepState();
  if (state.currentStep > 0) {
    state.currentStep--;
    renderTracker();
    renderStep();
  }
};

// ── Build character dict ─────────────────────────────────────────────────
function buildCharDict() {
  computeBaseScores();
  const final = getFinalScores();
  const classRow = state.classRow;
  const hitDie = classRow?.hit_die || 'd8';
  const avgMap = {d6:4,d8:5,d10:6,d12:7};
  const hp = Math.max(1, (avgMap[hitDie]||5) + mod(final.con));

  return {
    id: null,
    name: state.name,
    player_name: state.playerName,
    alignment: state.alignment,
    race: state.race?.name || '',
    ability_scores: final,
    class_levels: state.className ? [{
      class_name: state.className,
      level: 1,
      archetype_name: state.archetypeName || null,
    }] : [],
    feats: [...state.feats],
    traits: [...state.traits],
    skills: { ...state.skillRanks },
    equipment: [],
    conditions: [],
    hp_max: hp,
    hp_current: hp,
    notes: '',
  };
}

// ── Export actions ───────────────────────────────────────────────────────
window.saveCharacter = async function() {
  const char = buildCharDict();
  try {
    const result = await apiPost('/characters', char);
    alert(`Character saved! ID: ${result.id}`);
  } catch(e) {
    alert('Error saving character: ' + e.message);
  }
};

window.downloadJSON = function() {
  const char = buildCharDict();
  const blob = new Blob([JSON.stringify(char, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${char.name.replace(/\s+/g,'_') || 'character'}.json`;
  a.click();
};

window.saveAndViewSheet = async function() {
  const char = buildCharDict();
  try {
    const result = await apiPost('/characters', char);
    window.open(`/api/characters/${result.id}/sheet`, '_blank');
  } catch(e) {
    alert('Error: ' + e.message);
  }
};

// ── Character library ────────────────────────────────────────────────────
window.openCharList = async function() {
  const modal = document.getElementById('char-list-modal');
  const content = document.getElementById('char-list-content');
  modal.classList.remove('hidden');
  modal.style.display = 'flex';
  content.innerHTML = '<div class="loading-msg">Loading…</div>';
  try {
    const chars = await apiFetch('/characters');
    if (chars.length === 0) {
      content.innerHTML = '<p class="text-muted" style="padding:16px;">No saved characters yet.</p>';
      return;
    }
    content.innerHTML = chars.map(c => `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--gold-border);">
        <div>
          <div style="font-family:var(--font-head);font-size:14px;">${esc(c.name)}</div>
          <div class="text-muted" style="font-size:11px;">${c.race} · ${c.class_str} · ${c.player_name||'—'}</div>
        </div>
        <div style="display:flex;gap:8px;">
          <a class="btn btn-sm" href="/api/characters/${c.id}/sheet" target="_blank">View Sheet</a>
          <button class="btn btn-sm" onclick="loadChar('${c.id}')">Load</button>
        </div>
      </div>`).join('');
  } catch(e) {
    content.innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
};

window.loadChar = async function(id) {
  const char = await apiFetch(`/characters/${id}`);
  // Restore state from saved character
  state.name = char.name || '';
  state.playerName = char.player_name || '';
  state.alignment = char.alignment || 'True Neutral';

  if (char.race && state._races) {
    state.race = state._races.find(r => r.name === char.race) || null;
  }
  if (char.ability_scores) state.baseScores = { ...char.ability_scores };
  if (char.class_levels?.[0]) {
    state.className = char.class_levels[0].class_name;
    state.archetypeName = char.class_levels[0].archetype_name || null;
    if (state._classes) {
      state.classRow = state._classes.find(c => c.name === state.className) || null;
    }
  }
  state.feats = char.feats || [];
  state.traits = char.traits || [];
  state.skillRanks = char.skills || {};
  state.abilityMethod = 'manual';

  document.getElementById('char-list-modal').style.display = 'none';
  state.currentStep = 5;
  state.maxReached = 5;
  renderTracker();
  renderStep();
};

// ── Utilities ────────────────────────────────────────────────────────────
function esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Init ─────────────────────────────────────────────────────────────────
renderTracker();
renderStep();
