// ═══════════════════════════════════════════════════════════════════════
// PF1e Character Creator — Wizard State Machine
// ═══════════════════════════════════════════════════════════════════════

const API = '/api';

// 6 steps: Origins, Abilities, Feats & Traits, Extras, Skills, Review
const STEPS = [
  { id: 'origins',   label: 'Origins' },
  { id: 'abilities', label: 'Abilities' },
  { id: 'feats',     label: 'Feats & Traits' },
  { id: 'extras',    label: 'Extras' },
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

  // Step 0: Origins
  name:          '',
  playerName:    '',
  alignment:     'True Neutral',
  startLevel:    1,
  race:          null,   // full race object from API
  flexBonus:     null,   // chosen ability key for flexible +2
  className:     null,
  classRow:      null,
  archetypeName: null,

  // Step 1: Abilities
  abilityMethod: 'standard',
  baseScores:  { str:10, dex:10, con:10, int:10, wis:10, cha:10 },
  saAssign:    {},
  rollValues:  null,
  rollAssign:  {},

  // Step 2: Feats & Traits
  feats:  [],   // [{name, level, method}, ...]
  traits: [],

  // Step 3: Extras
  classTalents: [],    // selected class talent names
  spells: {},          // {0: ['...'], 1: ['...']}
  equipment: [],       // misc string items (freeform)
  equippedArmor: null, // full armor object from API, or null
  equippedShield: null,// full shield object from API, or null
  weapons: [],         // list of full weapon objects from API

  // Step 4: Skills
  skillRanks: {},
  favClassChoice: 'hp',   // 'hp' or 'skill'

  // Cached API data
  _races:      null,
  _classes:    null,
  _feats:      null,
  _traits:     null,
  _skills:     null,
  _classSkills: null,
  _weapons:    null,
  _armor:      null,
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
  if (state.abilityMethod === 'standard') {
    const scores = { str:10,dex:10,con:10,int:10,wis:10,cha:10 };
    for (const ab of ABILITIES_ORDER) {
      const val = parseInt(state.saAssign[ab]);
      if (!isNaN(val)) scores[ab] = val;
    }
    state.baseScores = scores;
  } else if (state.abilityMethod === 'roll') {
    const scores = { str:10,dex:10,con:10,int:10,wis:10,cha:10 };
    for (const ab of ABILITIES_ORDER) {
      const idx = state.rollAssign[ab];
      if (idx !== undefined && state.rollValues) scores[ab] = state.rollValues[idx];
    }
    state.baseScores = scores;
  }
  // pointbuy and manual: baseScores is maintained directly
}

// ── Budget helpers ────────────────────────────────────────────────────────
function skillBudget() {
  if (!state.classRow) return 0;
  const ranksPerLevel = state.classRow.skill_ranks_per_level || 2;
  const intMod = mod(getFinalScores().int);
  const perLevel = Math.max(1, ranksPerLevel + intMod);
  const humanBonus = (state.race?.name === 'Human') ? state.startLevel : 0;
  const fcSkillBonus = (state.favClassChoice === 'skill') ? state.startLevel : 0;
  return perLevel * state.startLevel + humanBonus + fcSkillBonus;
}

function usedSkillRanks() {
  return Object.values(state.skillRanks).reduce((s, v) => s + (v || 0), 0);
}

function featBudget() {
  const level = state.startLevel;
  // General feats at levels 1, 3, 5, 7... = ceil(level/2)
  let budget = Math.ceil(level / 2);
  // Fighter bonus combat feats at levels 1, 2, 4, 6, 8... = floor((level+2)/2)
  if (state.className === 'Fighter') budget += Math.floor((level + 2) / 2);
  // Human / Half-Elf: +1 bonus feat at level 1
  const race = state.race?.name || '';
  if (race === 'Human' || race === 'Half-Elf') budget += 1;
  return budget;
}

// ── Step tracker ─────────────────────────────────────────────────────────
function renderTracker() {
  const el = document.getElementById('step-tracker');
  let html = '';
  STEPS.forEach((step, i) => {
    const isDone     = i < state.currentStep;
    const isActive   = i === state.currentStep;
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

// ── Step rendering dispatcher ─────────────────────────────────────────────
async function renderStep() {
  const container = document.getElementById('step-content');
  container.innerHTML = '<div class="loading-msg"><div class="spinner"></div></div>';
  try {
    switch (state.currentStep) {
      case 0: await renderOriginsStep(container); break;
      case 1: await renderAbilitiesStep(container); break;
      case 2: await renderFeatsTraitsStep(container); break;
      case 3: await renderExtrasStep(container); break;
      case 4: await renderSkillsStep(container); break;
      case 5: await renderReviewStep(container); break;
    }
  } catch(e) {
    container.innerHTML = `<div class="panel"><p class="text-red">Error: ${e.message}</p></div>`;
  }
}

// ── Step 0: Origins (Identity + Race + Class) ─────────────────────────────
async function renderOriginsStep(c) {
  if (!state._races)   state._races   = await apiFetch('/races');
  if (!state._classes) state._classes = await apiFetch('/classes');

  const races = state._races;
  const coreRaces = races.filter(r => r.race_type === 'core');

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
  <div class="panel">
    <div class="panel-title">Identity</div>
    <div class="row gap-sm" style="flex-wrap:wrap;">
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
      <div class="col">
        <div class="field-group">
          <label class="field-label">Alignment</label>
          <select class="field-select" id="inp-alignment">
            ${ALIGNMENTS.map(a => `<option ${a===state.alignment?'selected':''}>${a}</option>`).join('')}
          </select>
        </div>
      </div>
      <div style="width:120px;">
        <div class="field-group">
          <label class="field-label">Starting Level</label>
          <input type="number" class="field-input" id="inp-level" min="1" max="20" value="${state.startLevel}"
                 title="For mid-campaign characters — sets feat/skill budgets and HP">
        </div>
      </div>
    </div>
  </div>

  <div class="row">
    <!-- Race column -->
    <div class="col">
      <div class="panel">
        <div class="panel-title">Race</div>
        <div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:4px;" id="core-race-tags">
          ${coreRaces.map(r => `
            <span class="tag race-tag${state.race?.name===r.name?' selected':''}"
                  data-race="${esc(r.name)}"
                  onclick="selectRace(${jsAttr(r.name)})">${r.name}</span>`).join('')}
        </div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="race-search" placeholder="Search races…" oninput="filterRaces()">
        </div>
        <div class="scroll-list" style="max-height:200px;" id="race-list">
          ${buildRaceListHtml(races)}
        </div>
        <div id="race-preview" style="margin-top:8px;">
          ${state.race ? racePreviewHtml(state.race) : '<p class="text-muted" style="font-size:12px;">Select a race above.</p>'}
        </div>
      </div>
    </div>

    <!-- Class column -->
    <div class="col">
      <div class="panel">
        <div class="panel-title">Class</div>
        <div class="search-wrap">
          <span class="search-icon">🔍</span>
          <input class="search-input" id="class-search" placeholder="Search classes…" oninput="filterClasses()">
        </div>
        <div class="scroll-list" style="max-height:200px;" id="class-list">
          ${buildClassListHtml(groups, typeLabels)}
        </div>
        <div id="class-preview" style="margin-top:8px;">
          ${state.classRow ? classPreviewHtml(state.classRow) : '<p class="text-muted" style="font-size:12px;">Select a class above.</p>'}
        </div>
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

  // If class already chosen (returning to this step), reload archetypes
  if (state.classRow) loadArchetypes(state.className);
}

function buildRaceListHtml(races) {
  const grouped = {};
  races.forEach(r => {
    const t = r.race_type || 'other';
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(r);
  });
  const order  = ['core','featured','uncommon'];
  const labels = { core:'CORE', featured:'FEATURED', uncommon:'UNCOMMON' };
  return order.filter(t => grouped[t]?.length).map(type => `
    <div style="padding:2px 12px;background:var(--paper-dark);border-bottom:1px solid var(--gold-border);">
      <span style="font-family:var(--font-label);font-size:8px;color:var(--gold);">${labels[type]}</span>
    </div>
    ${grouped[type].map(r => `
      <div class="list-item${state.race?.name===r.name?' selected':''}"
           data-name="${esc(r.name)}"
           onclick="selectRace(${jsAttr(r.name)})">
        <div>
          <div class="list-item-name">${r.name}</div>
          <div class="list-item-detail">${r.size} · Speed ${r.base_speed}ft</div>
        </div>
        <div class="list-item-type">${r.race_type}</div>
      </div>`).join('')}
  `).join('');
}

function buildClassListHtml(groups, typeLabels) {
  const order = ['base','hybrid','unchained','occult','prestige','alternate'];
  return order.filter(t => groups[t]?.length).map(type => `
    <div style="padding:2px 12px;background:var(--paper-dark);border-bottom:1px solid var(--gold-border);">
      <span style="font-family:var(--font-label);font-size:8px;color:var(--gold);">${typeLabels[type]||type.toUpperCase()}</span>
    </div>
    ${groups[type].map(cls => `
      <div class="list-item${state.className===cls.name?' selected':''}"
           data-name="${esc(cls.name)}"
           onclick="selectClass(${jsAttr(cls.name)})">
        <div>
          <div class="list-item-name">${cls.name}</div>
          <div class="list-item-detail">${cls.hit_die} · ${cls.skill_ranks_per_level} skills/lvl</div>
        </div>
        ${cls.spellcasting_type ? `<div class="list-item-type">${cls.spellcasting_type}</div>` : ''}
      </div>`).join('')}
  `).join('');
}

function racePreviewHtml(race) {
  const mods = race.ability_modifiers || {};
  const modChips = Object.entries(mods).map(([ab, v]) =>
    `<span class="race-mod-chip ${v>0?'positive':'negative'}">${v>0?'+':''}${v} ${ab.toUpperCase()}</span>`
  ).join('');
  const flexHtml = race.flexible_bonus
    ? `<span class="race-mod-chip positive">+2 Any (choice)</span>` : '';

  return `<div class="race-detail">
    <b style="font-family:var(--font-head);font-size:13px;">${race.name}</b>
    <div class="race-mods" style="margin:4px 0;">${modChips}${flexHtml}</div>
    <div style="font-size:11px;"><b>Size:</b> ${race.size||'Medium'} &nbsp;|&nbsp; <b>Speed:</b> ${race.base_speed||30}ft</div>
    ${race.flexible_bonus ? flexBonusSelector() : ''}
  </div>`;
}

function flexBonusSelector() {
  return `<div class="field-group mt-sm">
    <label class="field-label">+2 Ability Score Bonus</label>
    <select class="field-select" id="flex-bonus" onchange="state.flexBonus=this.value||null">
      <option value="">— Choose ability —</option>
      ${ABILITIES_ORDER.map(ab =>
        `<option value="${ab}" ${state.flexBonus===ab?'selected':''}>${ABILITY_LABELS[ab]}</option>`
      ).join('')}
    </select>
  </div>`;
}

function classPreviewHtml(cls) {
  const saves = [];
  if (cls.fort_progression === 'good') saves.push('Fort');
  if (cls.ref_progression  === 'good') saves.push('Ref');
  if (cls.will_progression === 'good') saves.push('Will');
  return `<div style="margin-bottom:6px;">
    <b style="font-family:var(--font-head);font-size:13px;">${cls.name}</b>
    ${cls.alignment_restriction ? `<span class="text-muted" style="font-size:10px;margin-left:6px;">${cls.alignment_restriction}</span>` : ''}
  </div>
  <div class="row gap-sm" style="flex-wrap:wrap;margin-bottom:6px;">
    <div class="stat-box"><div class="stat-box-label">Hit Die</div><div class="stat-box-value">${cls.hit_die||'d8'}</div></div>
    <div class="stat-box"><div class="stat-box-label">BAB</div><div class="stat-box-value" style="font-size:12px;">${cls.bab_progression||'—'}</div></div>
    <div class="stat-box"><div class="stat-box-label">Skills/Lvl</div><div class="stat-box-value">${cls.skill_ranks_per_level||2}</div></div>
    <div class="stat-box"><div class="stat-box-label">Good Saves</div><div class="stat-box-value" style="font-size:10px;">${saves.join('/')||'—'}</div></div>
  </div>
  ${cls.spellcasting_type ? `<div class="text-muted" style="font-size:10px;margin-bottom:4px;"><b>Spellcasting:</b> ${cls.spellcasting_type} (${cls.spellcasting_style||'—'})</div>` : ''}
  <div id="archetype-section"></div>`;
}

window.selectRace = function(name) {
  const race = (state._races || []).find(r => r.name === name);
  if (!race) return;
  state.race = race;
  if (!race.flexible_bonus) state.flexBonus = null;
  // Highlight quick-select tags
  document.querySelectorAll('.race-tag').forEach(el => {
    const match = el.dataset.race === name;
    el.classList.toggle('selected', match);
    el.style.background   = match ? 'var(--gold-bg)' : '';
    el.style.borderColor  = match ? 'var(--gold)'    : '';
  });
  // Highlight scrollable list
  document.querySelectorAll('#race-list .list-item').forEach(el => {
    el.classList.toggle('selected', el.dataset.name === name);
  });
  // Show preview
  document.getElementById('race-preview').innerHTML = racePreviewHtml(race);
};

window.filterRaces = function() {
  const q = document.getElementById('race-search').value.toLowerCase();
  document.querySelectorAll('#race-list .list-item').forEach(el => {
    el.style.display = el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
};

window.selectClass = async function(name) {
  const cls = (state._classes || []).find(c => c.name === name);
  if (!cls) return;
  state.className = name;
  state.classRow = cls;
  state.archetypeName = null;
  state._classSkills = null;
  document.querySelectorAll('#class-list .list-item').forEach(el => {
    el.classList.toggle('selected', el.dataset.name === name);
  });
  document.getElementById('class-preview').innerHTML = classPreviewHtml(cls);
  await loadArchetypes(name);
};

async function loadArchetypes(name) {
  const archSection = document.getElementById('archetype-section');
  if (!archSection) return;
  archSection.innerHTML = '<span class="text-muted" style="font-size:11px;">Loading…</span>';
  try {
    const archetypes = await apiFetch(`/classes/${encodeURIComponent(name)}/archetypes`);
    if (archetypes.length === 0) {
      archSection.innerHTML = '<p class="text-muted" style="font-size:11px;">No archetypes available.</p>';
    } else {
      archSection.innerHTML = `
        <div class="field-group" style="margin-top:6px;">
          <label class="field-label">Archetype (Optional)</label>
          <select class="field-select" id="archetype-select" onchange="state.archetypeName=this.value||null">
            <option value="">— None (base class) —</option>
            ${archetypes.map(a => `<option value="${esc(a.name)}" ${state.archetypeName===a.name?'selected':''}>${a.name}</option>`).join('')}
          </select>
        </div>`;
    }
  } catch(e) {
    archSection.innerHTML = '<p class="text-muted" style="font-size:11px;">Could not load archetypes.</p>';
  }
}

window.filterClasses = function() {
  const q = document.getElementById('class-search').value.toLowerCase();
  document.querySelectorAll('#class-list .list-item').forEach(el => {
    el.style.display = el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
};

// ── Step 1: Ability Scores ────────────────────────────────────────────────
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
      <button class="btn btn-primary" onclick="nextStep()">Next: Feats &amp; Traits →</button>
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
      <div class="ability-assign-mod">${v ? modStr(+v) : '—'}</div>
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
      <div class="pb-cost">Cost: ${cost}</div>
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

window.doRoll = function() {
  state.rollValues = Array.from({length:6}, () => {
    const d = Array.from({length:4}, () => 1 + Math.floor(Math.random()*6));
    d.sort((a,b) => a-b);
    return d[1]+d[2]+d[3];
  });
  state.rollAssign = {};
  renderAbilityMethodPanel();
};

window.setRollAssign = function(ab, idx) {
  const parsed = idx === '' ? undefined : parseInt(idx);
  // Clear any other ability that was already using this index
  if (parsed !== undefined) {
    for (const other of ABILITIES_ORDER) {
      if (other !== ab && state.rollAssign[other] === parsed) {
        state.rollAssign[other] = undefined;
      }
    }
  }
  state.rollAssign[ab] = parsed;
  computeBaseScores();
  document.getElementById('ability-preview').innerHTML = abilityPreviewHtml();
  renderAbilityMethodPanel();
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

// ── Step 2: Feats + Traits ────────────────────────────────────────────────
async function renderFeatsTraitsStep(c) {
  if (!state._feats)  state._feats  = await apiFetch('/feats');
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
          ${state.feats.map(f => `<span class="tag">${f.name}<span class="feat-method-tag">${f.method}</span><button class="tag-remove" onclick="removeFeat(${jsAttr(f.name)})">✕</button></span>`).join('')}
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
          ${state.traits.map(t => `<span class="tag">${t}<button class="tag-remove" onclick="removeTrait(${jsAttr(t)})">✕</button></span>`).join('')}
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
      <button class="btn btn-primary" onclick="nextStep()">Next: Extras →</button>
    </div>
  </div>`;
}

function featListHtml(feats) {
  return feats.slice(0, 300).map(f => {
    const prereq  = f.prerequisites ? `<div class="list-item-detail"><em>Req:</em> ${esc(f.prerequisites.slice(0,90))}${f.prerequisites.length>90?'…':''}</div>` : '';
    const benefit = f.benefit       ? `<div class="list-item-detail">${esc(f.benefit.slice(0,110))}${f.benefit.length>110?'…':''}</div>` : '';
    return `
    <div class="list-item${state.feats.some(sf => sf.name === f.name)?' selected':''}"
         data-name="${esc(f.name)}" data-type="${esc(f.feat_type)}"
         data-prereq="${esc(f.prerequisites)}" data-benefit="${esc(f.benefit.slice(0,200))}"
         onclick="toggleFeat(${jsAttr(f.name)})">
      <div style="flex:1;min-width:0;">
        <div class="list-item-name">${f.name}</div>
        ${prereq}${benefit}
      </div>
      <div class="list-item-type" style="white-space:nowrap;">${f.feat_type}</div>
    </div>`;
  }).join('');
}

function traitListHtml(traits) {
  return traits.slice(0, 200).map(t => `
    <div class="list-item${state.traits.includes(t.name)?' selected':''}"
         data-name="${esc(t.name)}" data-type="${esc(t.trait_type)}"
         onclick="toggleTrait(${jsAttr(t.name)})">
      <div>
        <div class="list-item-name">${t.name}</div>
        ${t.benefit ? `<div class="list-item-detail">${t.benefit.slice(0,80)}${t.benefit.length>80?'…':''}</div>` : ''}
      </div>
      <div class="list-item-type">${t.trait_type}</div>
    </div>`).join('');
}

window.toggleFeat = function(name) {
  if (state.feats.some(f => f.name === name)) {
    state.feats = state.feats.filter(f => f.name !== name);
  } else {
    if (state.feats.length >= featBudget()) {
      showErrors([`Maximum ${featBudget()} feats at level ${state.startLevel}.`]);
      return;
    }
    state.feats.push({ name, level: state.startLevel, method: 'general' });
  }
  renderFeatsTraitsStep(document.getElementById('step-content'));
};

window.removeFeat = function(name) {
  state.feats = state.feats.filter(f => f.name !== name);
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
    const nameMatch = !q || el.dataset.name.toLowerCase().includes(q)
                         || (el.dataset.prereq || '').toLowerCase().includes(q)
                         || (el.dataset.benefit || '').toLowerCase().includes(q);
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

// ── Step 3: Extras (class talents, spells, equipment) ─────────────────────

// Maps class names to their selectable talent feature_type in class_features table
const CLASS_TALENT_MAP = {
  'Barbarian':     'Rage Power',
  'Rogue':         'Rogue Talent',
  'Alchemist':     'Discovery',
  'Witch':         'Hex',
  'Magus':         'Magus Arcana',
  'Ninja':         'Ninja Trick',
  'Inquisitor':    'Inquisition',
  'Slayer':        'Slayer Talent',
  'Investigator':  'Investigator Talent',
  'Arcanist':      'Exploit',
  'Skald':         'Rage Power',
  'Shaman':        'Hex',
  'Kineticist':    'Wild Talent',
};

async function renderExtrasStep(c) {
  const className    = state.className || '';
  const classRow     = state.classRow;
  const talentType   = CLASS_TALENT_MAP[className] || null;
  const isSpellcaster = !!classRow?.spellcasting_type;

  // Load class talents if applicable
  let talents = [];
  if (talentType) {
    try {
      talents = await apiFetch(`/classes/${encodeURIComponent(className)}/features?feature_type=${encodeURIComponent(talentType)}`);
    } catch(e) { talents = []; }
  }

  // Build available spell levels at current level (simplified: use class progression data from classRow)
  // For now show level 0 (cantrips) and level 1 spells if spellcaster
  let spellLevels = [];
  if (isSpellcaster) {
    // Assume all spellcasters get cantrips + level 1 at level 1; extend for higher levels
    const maxSpellLevel = Math.min(9, Math.ceil(state.startLevel / 2));
    for (let lvl = 0; lvl <= maxSpellLevel; lvl++) spellLevels.push(lvl);
  }

  const talentSection = talentType ? `
    <div class="panel">
      <div class="panel-title">${talentType}s
        <span class="text-muted" style="font-weight:400;font-size:10px;"> — ${state.classTalents.length} selected</span>
      </div>
      <div style="margin-bottom:10px;" id="talent-selected">
        ${state.classTalents.map(t => `<span class="tag">${t}<button class="tag-remove" onclick="removeTalent(${jsAttr(t)})">✕</button></span>`).join('')}
        ${state.classTalents.length === 0 ? '<span class="text-muted" style="font-size:12px;">None selected.</span>' : ''}
      </div>
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input class="search-input" id="talent-search" placeholder="Search ${talentType}s…" oninput="filterTalents()">
      </div>
      <div class="scroll-list" style="max-height:220px;" id="talent-list">
        ${talents.length > 0 ? talents.map(t => `
          <div class="list-item${state.classTalents.includes(t.name)?' selected':''}"
               data-name="${esc(t.name)}"
               onclick="toggleTalent(${jsAttr(t.name)})">
            <div>
              <div class="list-item-name">${t.name}</div>
              ${t.description ? `<div class="list-item-detail">${(t.description||'').slice(0,80)}${(t.description||'').length>80?'…':''}</div>` : ''}
            </div>
          </div>`).join('') : '<div class="text-muted" style="padding:8px;font-size:12px;">No ${talentType}s found in database.</div>'}
      </div>
    </div>` : '';

  const spellSection = isSpellcaster ? `
    <div class="panel">
      <div class="panel-title">Spells Known / Prepared</div>
      <p class="text-muted" style="font-size:11px;margin-bottom:10px;">
        Select spells for your ${className}. Use the spell level tabs below.
      </p>
      <div class="method-tabs" id="spell-level-tabs">
        ${spellLevels.map(lvl => `<div class="method-tab${lvl===0?' active':''}" onclick="setSpellTab(${lvl})">${lvl === 0 ? 'Cantrips' : 'Level '+lvl}</div>`).join('')}
      </div>
      <div id="spell-tab-content">
        ${spellTabHtml(0, className)}
      </div>
    </div>` : '';

  // Load weapons and armor from API (cached)
  if (!state._weapons) {
    try { state._weapons = await apiFetch('/equipment/weapons'); } catch(e) { state._weapons = []; }
  }
  if (!state._armor) {
    try { state._armor = await apiFetch('/equipment/armor'); } catch(e) { state._armor = []; }
  }

  const armorList  = (state._armor || []).filter(a => a.armor_type !== 'shield');
  const shieldList = (state._armor || []).filter(a => a.armor_type === 'shield');
  const weaponList = state._weapons || [];

  // ── Armor dropdown ────────────────────────────────────────────────────
  function armorOption(item, selectedName) {
    const sel = (selectedName === item.name) ? ' selected' : '';
    const label = `${item.name} (AC+${item.armor_bonus}, MaxDex ${item.max_dex ?? '—'}, ACP ${item.armor_check_penalty})`;
    return `<option value="${esc(item.name)}"${sel}>${esc(label)}</option>`;
  }
  const currentArmorName  = state.equippedArmor?.name || '';
  const currentShieldName = state.equippedShield?.name || '';

  // Group armor by type for optgroups
  function armorOptgroups(list, selectedName) {
    const groups = { 'light': [], 'medium': [], 'heavy': [] };
    for (const a of list) {
      const t = a.armor_type;
      if (groups[t]) groups[t].push(a);
    }
    return Object.entries(groups).map(([type, items]) =>
      items.length ? `<optgroup label="${type.charAt(0).toUpperCase()+type.slice(1)} Armor">${items.map(a => armorOption(a, selectedName)).join('')}</optgroup>` : ''
    ).join('');
  }

  const armorSection = `
  <div class="panel">
    <div class="panel-title">Armor &amp; Shield</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
      <div>
        <label class="field-label">Armor</label>
        <select class="field-input" id="armor-select" onchange="onArmorChange()">
          <option value="">— None —</option>
          ${armorOptgroups(armorList, currentArmorName)}
        </select>
        ${state.equippedArmor ? `<div class="text-muted" style="font-size:10px;margin-top:4px;">
          AC+${state.equippedArmor.armor_bonus} · MaxDex ${state.equippedArmor.max_dex ?? '—'} · ACP ${state.equippedArmor.armor_check_penalty} · ASF ${state.equippedArmor.arcane_spell_failure}%
          · Speed ${state.equippedArmor.speed_30}
        </div>` : ''}
      </div>
      <div>
        <label class="field-label">Shield</label>
        <select class="field-input" id="shield-select" onchange="onShieldChange()">
          <option value="">— None —</option>
          ${shieldList.map(a => `<option value="${esc(a.name)}"${a.name===currentShieldName?' selected':''}>${esc(a.name)} (AC+${a.armor_bonus}, ACP ${a.armor_check_penalty})</option>`).join('')}
        </select>
        ${state.equippedShield ? `<div class="text-muted" style="font-size:10px;margin-top:4px;">
          AC+${state.equippedShield.armor_bonus} · ACP ${state.equippedShield.armor_check_penalty} · ASF ${state.equippedShield.arcane_spell_failure}%
        </div>` : ''}
      </div>
    </div>
  </div>`;

  // ── Weapon picker ──────────────────────────────────────────────────────
  const weaponSection = `
  <div class="panel">
    <div class="panel-title">Weapons
      <span class="text-muted" style="font-weight:400;font-size:10px;"> — ${state.weapons.length} selected</span>
    </div>
    <div style="margin-bottom:8px;" id="weapon-selected">
      ${state.weapons.map(w => `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;background:var(--parchment-dark);padding:4px 8px;border-radius:3px;">
          <span style="flex:1;font-size:12px;"><strong>${esc(w.name)}</strong>
            ${w.damage_medium ? ` ${esc(w.damage_medium)}` : ''}
            ${w.critical ? ` ${esc(w.critical)}` : ''}
            ${w.damage_type ? ` <em>${esc(w.damage_type)}</em>` : ''}
            ${w.range_increment ? ` · ${esc(w.range_increment)}` : ''}
          </span>
          <button class="tag-remove" onclick="removeWeapon(${jsAttr(w.name)})">✕</button>
        </div>`).join('')}
      ${state.weapons.length === 0 ? '<span class="text-muted" style="font-size:12px;">No weapons selected.</span>' : ''}
    </div>
    <div class="search-wrap">
      <span class="search-icon">🔍</span>
      <input class="search-input" id="weapon-search" placeholder="Search weapons…" oninput="filterWeapons()">
    </div>
    <div style="margin-bottom:6px;display:flex;gap:6px;flex-wrap:wrap;">
      ${['simple','martial','exotic'].map(p => `<button class="method-tab" id="wprof-${p}" onclick="setWeaponProf('${p}')">${p.charAt(0).toUpperCase()+p.slice(1)}</button>`).join('')}
      ${['melee','ranged'].map(t => `<button class="method-tab" id="wtype-${t}" onclick="setWeaponType('${t}')">${t.charAt(0).toUpperCase()+t.slice(1)}</button>`).join('')}
      <button class="method-tab method-tab-clear" onclick="clearWeaponFilters()">All</button>
    </div>
    <div class="scroll-list" style="max-height:200px;" id="weapon-list">
      ${weaponListHtml(weaponList)}
    </div>
    <p class="text-muted" style="font-size:10px;margin-top:6px;">Click a weapon to add/remove. Up to 4 weapons.</p>
  </div>`;

  // ── Misc equipment textarea ────────────────────────────────────────────
  const miscSection = `
  <div class="panel">
    <div class="panel-title">Other Equipment</div>
    <p class="text-muted" style="font-size:11px;margin-bottom:8px;">Adventuring gear, magic items, etc. — one item per line.</p>
    <textarea class="field-input" id="equipment-input" rows="4" style="width:100%;resize:vertical;"
              placeholder="Backpack&#10;Rope, silk (50 ft.)&#10;Potion of Cure Light Wounds">${state.equipment.join('\n')}</textarea>
  </div>`;

  const noExtras = !talentSection && !spellSection;
  c.innerHTML = `
  ${talentSection}
  ${spellSection}
  ${noExtras ? `<div class="panel"><p class="text-muted" style="font-size:12px;">No class-specific options for <b>${esc(className || 'this class')}</b>.</p></div>` : ''}
  ${armorSection}
  ${weaponSection}
  ${miscSection}

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="nav-error" id="nav-error"></span>
      <button class="btn btn-primary" onclick="nextStep()">Next: Skills →</button>
    </div>
  </div>`;

  // Kick off loading spell list for level 0 if spellcaster
  if (isSpellcaster) loadSpellList(0);
}

function weaponListHtml(weapons) {
  const q      = (document.getElementById('weapon-search')?.value || '').toLowerCase();
  const prof   = window._weaponProfFilter || '';
  const wtype  = window._weaponTypeFilter || '';
  return weapons
    .filter(w => {
      if (q    && !w.name.toLowerCase().includes(q)) return false;
      if (prof  && w.proficiency !== prof) return false;
      if (wtype && w.weapon_type !== wtype) return false;
      return true;
    })
    .slice(0, 200)
    .map(w => {
      const sel = state.weapons.some(sw => sw.name === w.name);
      return `<div class="list-item${sel?' selected':''}" data-name="${esc(w.name)}"
               onclick="toggleWeapon(${jsAttr(w.name)})">
        <div style="flex:1;min-width:0;">
          <div class="list-item-name">${esc(w.name)}</div>
          <div class="list-item-detail">
            ${w.damage_medium ? esc(w.damage_medium)+' ' : ''}${w.critical ? esc(w.critical) : ''}${w.damage_type ? ' · '+esc(w.damage_type) : ''}${w.range_increment ? ' · '+esc(w.range_increment) : ''}${w.special ? ' · '+esc(w.special) : ''}
          </div>
        </div>
        <div class="list-item-type" style="white-space:nowrap;">${w.proficiency}</div>
      </div>`;
    }).join('') || '<div class="text-muted" style="padding:8px;font-size:12px;">No weapons match.</div>';
}

window.onArmorChange = function() {
  const name = document.getElementById('armor-select')?.value || '';
  state.equippedArmor = (state._armor || []).find(a => a.name === name) || null;
  renderExtrasStep(document.getElementById('step-content'));
};

window.onShieldChange = function() {
  const name = document.getElementById('shield-select')?.value || '';
  state.equippedShield = (state._armor || []).find(a => a.name === name) || null;
  renderExtrasStep(document.getElementById('step-content'));
};

window.toggleWeapon = function(name) {
  if (state.weapons.some(w => w.name === name)) {
    state.weapons = state.weapons.filter(w => w.name !== name);
  } else {
    if (state.weapons.length >= 4) return;
    const w = (state._weapons || []).find(w => w.name === name);
    if (w) state.weapons.push(w);
  }
  // Refresh just the selected list and weapon list (don't re-render whole step)
  const sel = document.getElementById('weapon-selected');
  const list = document.getElementById('weapon-list');
  if (sel) sel.outerHTML = weaponSelectedHtml();
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
  // re-query after outerHTML replacement
  document.getElementById('weapon-selected')?.querySelectorAll('.tag-remove').forEach(() => {});
};

function weaponSelectedHtml() {
  return `<div style="margin-bottom:8px;" id="weapon-selected">
    ${state.weapons.map(w => `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;background:var(--parchment-dark);padding:4px 8px;border-radius:3px;">
        <span style="flex:1;font-size:12px;"><strong>${esc(w.name)}</strong>
          ${w.damage_medium ? ` ${esc(w.damage_medium)}` : ''}
          ${w.critical ? ` ${esc(w.critical)}` : ''}
          ${w.damage_type ? ` <em>${esc(w.damage_type)}</em>` : ''}
          ${w.range_increment ? ` · ${esc(w.range_increment)}` : ''}
        </span>
        <button class="tag-remove" onclick="removeWeapon(${jsAttr(w.name)})">✕</button>
      </div>`).join('')}
    ${state.weapons.length === 0 ? '<span class="text-muted" style="font-size:12px;">No weapons selected.</span>' : ''}
  </div>`;
}

window.removeWeapon = function(name) {
  state.weapons = state.weapons.filter(w => w.name !== name);
  const sel  = document.getElementById('weapon-selected');
  const list = document.getElementById('weapon-list');
  if (sel)  sel.outerHTML = weaponSelectedHtml();
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
};

window._weaponProfFilter = '';
window._weaponTypeFilter = '';

window.setWeaponProf = function(prof) {
  window._weaponProfFilter = (window._weaponProfFilter === prof) ? '' : prof;
  window._weaponTypeFilter = '';
  const list = document.getElementById('weapon-list');
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
};

window.setWeaponType = function(wtype) {
  window._weaponTypeFilter = (window._weaponTypeFilter === wtype) ? '' : wtype;
  window._weaponProfFilter = '';
  const list = document.getElementById('weapon-list');
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
};

window.clearWeaponFilters = function() {
  window._weaponProfFilter = '';
  window._weaponTypeFilter = '';
  const list = document.getElementById('weapon-list');
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
};

window.filterWeapons = function() {
  const list = document.getElementById('weapon-list');
  if (list) list.innerHTML = weaponListHtml(state._weapons || []);
};

window.toggleTalent = function(name) {
  if (state.classTalents.includes(name)) {
    state.classTalents = state.classTalents.filter(t => t !== name);
  } else {
    state.classTalents.push(name);
  }
  // Re-render selected area without full step re-render
  const selEl = document.getElementById('talent-selected');
  if (selEl) {
    selEl.innerHTML = state.classTalents.length
      ? state.classTalents.map(t => `<span class="tag">${t}<button class="tag-remove" onclick="removeTalent(${jsAttr(t)})">✕</button></span>`).join('')
      : '<span class="text-muted" style="font-size:12px;">None selected.</span>';
  }
  document.querySelectorAll('#talent-list .list-item').forEach(el => {
    el.classList.toggle('selected', state.classTalents.includes(el.dataset.name));
  });
};

window.removeTalent = function(name) {
  state.classTalents = state.classTalents.filter(t => t !== name);
  const selEl = document.getElementById('talent-selected');
  if (selEl) {
    selEl.innerHTML = state.classTalents.length
      ? state.classTalents.map(t => `<span class="tag">${t}<button class="tag-remove" onclick="removeTalent(${jsAttr(t)})">✕</button></span>`).join('')
      : '<span class="text-muted" style="font-size:12px;">None selected.</span>';
  }
  document.querySelectorAll('#talent-list .list-item').forEach(el => {
    el.classList.toggle('selected', state.classTalents.includes(el.dataset.name));
  });
};

window.filterTalents = function() {
  const q = (document.getElementById('talent-search')?.value || '').toLowerCase();
  document.querySelectorAll('#talent-list .list-item').forEach(el => {
    el.style.display = !q || el.dataset.name.toLowerCase().includes(q) ? '' : 'none';
  });
};

// ── Spell tab helpers ─────────────────────────────────────────────────────
let _currentSpellTab = 0;
let _spellListCache = {};

function spellTabHtml(level, className) {
  const selected = (state.spells[level] || []);
  return `
    <div style="margin:8px 0;font-size:11px;color:var(--fade);">
      Selected: ${selected.length > 0 ? selected.map(s => `<span class="tag" style="font-size:10px;">${s}<button class="tag-remove" onclick="removeSpell(${level},${jsAttr(s)})">✕</button></span>`).join('') : '<em>None</em>'}
    </div>
    <div id="spell-list-${level}"><span class="text-muted">Loading spells…</span></div>`;
}

window.setSpellTab = function(level) {
  _currentSpellTab = level;
  document.querySelectorAll('#spell-level-tabs .method-tab').forEach((tt, ii) => {
    tt.classList.toggle('active', ii === level);
  });
  const contentEl = document.getElementById('spell-tab-content');
  if (contentEl) contentEl.innerHTML = spellTabHtml(level, state.className || '');
  loadSpellList(level);
};

async function loadSpellList(level) {
  const listEl = document.getElementById(`spell-list-${level}`);
  if (!listEl) return;
  if (_spellListCache[level]) {
    renderSpellList(level, _spellListCache[level]);
    return;
  }
  try {
    const spells = await apiFetch(`/spells?class_name=${encodeURIComponent(state.className || '')}&level=${level}&limit=200`);
    _spellListCache[level] = spells;
    renderSpellList(level, spells);
  } catch(e) {
    listEl.innerHTML = `<div class="text-muted" style="padding:8px;font-size:12px;">Could not load spells: ${e.message}</div>`;
  }
}

function renderSpellList(level, spells) {
  const listEl = document.getElementById(`spell-list-${level}`);
  if (!listEl) return;
  const selected = state.spells[level] || [];
  if (!spells.length) {
    listEl.innerHTML = '<div class="text-muted" style="padding:8px;font-size:12px;">No spells found for this level.</div>';
    return;
  }
  listEl.innerHTML = `<div class="scroll-list" style="max-height:200px;">
    ${spells.slice(0, 200).map(s => `
      <div class="list-item${selected.includes(s.name)?' selected':''}"
           data-name="${esc(s.name)}"
           onclick="toggleSpell(${level},${jsAttr(s.name)})">
        <div class="list-item-name">${s.name}</div>
        ${s.school ? `<div class="list-item-detail">${s.school}</div>` : ''}
      </div>`).join('')}
  </div>`;
}

window.toggleSpell = function(level, name) {
  if (!state.spells[level]) state.spells[level] = [];
  if (state.spells[level].includes(name)) {
    state.spells[level] = state.spells[level].filter(s => s !== name);
  } else {
    state.spells[level].push(name);
  }
  // Re-render just the selected line and list highlight
  const contentEl = document.getElementById('spell-tab-content');
  if (contentEl) {
    // Update selected summary line
    const sel = state.spells[level] || [];
    const selDiv = contentEl.querySelector('div[style*="margin:8px"]');
    if (selDiv) {
      selDiv.innerHTML = `Selected: ${sel.length > 0 ? sel.map(s => `<span class="tag" style="font-size:10px;">${s}<button class="tag-remove" onclick="removeSpell(${level},${jsAttr(s)})">✕</button></span>`).join('') : '<em>None</em>'}`;
    }
  }
  document.querySelectorAll(`#spell-list-${level} .list-item`).forEach(el => {
    el.classList.toggle('selected', (state.spells[level] || []).includes(el.dataset.name));
  });
};

window.removeSpell = function(level, name) {
  if (state.spells[level]) {
    state.spells[level] = state.spells[level].filter(s => s !== name);
  }
  window.setSpellTab(level);
};

/// ── Step 4: Skills ────────────────────────────────────────────────────────
async function renderSkillsStep(c) {
  if (!state._skills) state._skills = await apiFetch('/skills');
  if (!state._classSkills && state.className) {
    const names = await apiFetch(`/skills/class/${encodeURIComponent(state.className)}`);
    state._classSkills = new Set(names.map(n => n.toLowerCase()));
  } else if (!state._classSkills) {
    state._classSkills = new Set();
  }

  const budget    = skillBudget();
  const used      = usedSkillRanks();
  const remaining = budget - used;
  const final     = getFinalScores();
  const maxRanks  = state.startLevel;

  const ranksPerLevel = state.classRow?.skill_ranks_per_level || 2;
  const intMod = mod(final.int);
  const perLvl = Math.max(1, ranksPerLevel + intMod);

  c.innerHTML = `
  <div class="panel">
    <div class="panel-title">Skill Ranks</div>

    <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-bottom:10px;">
      <div class="skill-budget-bar" style="flex:1;min-width:200px;">
        <span>Available ranks${state.startLevel > 1 ? ` (level ${state.startLevel})` : ''}</span>
        <span class="skill-budget-count ${remaining < 0 ? 'depleted' : ''}">${remaining} / ${budget}</span>
      </div>
      <div style="display:flex;gap:8px;align-items:center;font-size:12px;">
        <span style="font-family:var(--font-label);font-size:9px;color:var(--fade);">FAVORED CLASS BONUS:</span>
        <label style="cursor:pointer;display:flex;gap:4px;align-items:center;">
          <input type="radio" name="fcb" value="hp" ${state.favClassChoice==='hp'?'checked':''} onchange="setFavClass('hp')"> +HP/lvl
        </label>
        <label style="cursor:pointer;display:flex;gap:4px;align-items:center;">
          <input type="radio" name="fcb" value="skill" ${state.favClassChoice==='skill'?'checked':''} onchange="setFavClass('skill')"> +Skill Rank/lvl
        </label>
      </div>
    </div>

    <p class="text-muted" style="font-size:11px;margin-bottom:10px;">
      <b style="color:var(--green);">Bold green</b> = class skill (+3 when ranked) · Max ${maxRanks} rank${maxRanks>1?'s':''} per skill
      · Base: ${perLvl}/lvl (${ranksPerLevel} class${intMod>=0?'+':''}${intMod} INT)
    </p>
    <div style="overflow-x:auto;">
    <table class="skill-list-table">
      <thead><tr><th>Skill</th><th>Ability</th><th>Ranks</th><th>Mod</th><th>Total</th><th style="font-size:9px;color:var(--fade);">Breakdown</th></tr></thead>
      <tbody>
        ${state._skills.map(sk => {
          const isCS  = state._classSkills.has(sk.name.toLowerCase());
          const ranks = state.skillRanks[sk.name] || 0;
          const abilMod = mod(final[sk.ability] || 10);
          const trained = ranks > 0 && isCS ? 3 : 0;
          const total = ranks + abilMod + trained;
          const breakdown = ranks > 0
            ? `${ranks}rk ${abilMod>=0?'+':''}${abilMod}${sk.ability.toUpperCase()}${trained?' +3cs':''} = ${total>=0?'+':''}${total}`
            : `${abilMod>=0?'+':''}${abilMod} ${sk.ability.toUpperCase()}`;
          return `<tr class="${isCS?'class-skill':''}">
            <td class="${isCS?'skill-cs':''}">${sk.name}${sk.trained_only?'*':''}</td>
            <td>${sk.ability.toUpperCase()}</td>
            <td>
              <div class="rank-stepper">
                <button class="rank-btn" onclick="changeRank('${esc(sk.name)}',-1)" ${ranks<=0?'disabled':''}>−</button>
                <span class="rank-val">${ranks}</span>
                <button class="rank-btn" onclick="changeRank('${esc(sk.name)}',1)" ${remaining<=0||ranks>=maxRanks?'disabled':''}>+</button>
              </div>
            </td>
            <td style="text-align:center">${modStr(final[sk.ability]||10)}</td>
            <td class="skill-total-val" style="color:${total>0?'var(--green)':total<0?'var(--red-wax)':'var(--ink)'}">
              ${total >= 0 ? '+' : ''}${total}
            </td>
            <td style="font-size:9px;color:var(--fade);white-space:nowrap;">${breakdown}</td>
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
  const current  = state.skillRanks[skillName] || 0;
  const budget   = skillBudget();
  const used     = usedSkillRanks();
  if (delta > 0 && used >= budget) return;
  if (delta < 0 && current <= 0) return;
  if (delta > 0 && current >= state.startLevel) return;
  state.skillRanks[skillName] = Math.max(0, current + delta);
  renderSkillsStep(document.getElementById('step-content'));
};

window.setFavClass = function(choice) {
  state.favClassChoice = choice;
  renderSkillsStep(document.getElementById('step-content'));
};

// ── Step 5: Review ────────────────────────────────────────────────────────
async function renderReviewStep(c) {
  computeBaseScores();
  const final    = getFinalScores();
  const classRow = state.classRow;
  const level    = state.startLevel;

  const conMod = mod(final.con);
  const dexMod = mod(final.dex);
  const strMod = mod(final.str);
  const wisMod = mod(final.wis);

  // HP: max die at level 1, average for subsequent levels
  const hitDie = classRow?.hit_die || 'd8';
  const dieSize = parseInt(hitDie.slice(1)) || 8;
  const avgRoll = {d6:4,d8:5,d10:6,d12:7}[hitDie] || 5;
  const hpL1   = Math.max(1, dieSize + conMod);
  const hp     = hpL1 + (level > 1 ? Math.max(1, avgRoll + conMod) * (level - 1) : 0);

  // Saves and BAB at given level (approximate for review)
  let bab = 0, fort_base = 0, ref_base = 0, will_base = 0;
  if (classRow) {
    if      (classRow.bab_progression === 'full')         bab = level;
    else if (classRow.bab_progression === 'three_quarter') bab = Math.floor(level * 3 / 4);
    else                                                    bab = Math.floor(level / 2);
    const goodSave = n => Math.floor(n / 2) + 2;
    const poorSave = n => Math.floor(n / 3);
    fort_base = classRow.fort_progression === 'good' ? goodSave(level) : poorSave(level);
    ref_base  = classRow.ref_progression  === 'good' ? goodSave(level) : poorSave(level);
    will_base = classRow.will_progression === 'good' ? goodSave(level) : poorSave(level);
  }
  const fort = fort_base + conMod;
  const ref  = ref_base  + dexMod;
  const will = will_base + wisMod;
  const armorBonus  = state.equippedArmor?.armor_bonus  || 0;
  const shieldBonus = state.equippedShield?.armor_bonus || 0;
  const maxDexArmor = state.equippedArmor?.max_dex;
  const effDex = maxDexArmor !== undefined && maxDexArmor !== null ? Math.min(dexMod, maxDexArmor) : dexMod;
  const ac   = 10 + effDex + armorBonus + shieldBonus;
  const fm   = m => m >= 0 ? `+${m}` : `${m}`;

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
          <div class="review-row"><span class="review-key">Level</span><span class="review-val">${level}</span></div>
        </div>

        <div class="review-section">
          <div class="review-section-title">Ability Scores</div>
          ${ABILITIES_ORDER.map(ab => `
            <div class="review-row">
              <span class="review-key">${ABILITY_LABELS[ab]}</span>
              <span class="review-val">${final[ab]} (${fm(mod(final[ab]))})</span>
            </div>`).join('')}
        </div>

        <div class="review-section">
          <div class="review-section-title">Feats (${state.feats.length}/${featBudget()})</div>
          ${state.feats.length
            ? state.feats.map(f => `<div class="review-row"><span class="review-val">${f.name} <span class="feat-method-tag">${f.method} · lvl ${f.level}</span></span></div>`).join('')
            : '<div class="text-muted" style="font-size:11px;">None selected</div>'}
        </div>

        <div class="review-section">
          <div class="review-section-title">Traits (${state.traits.length})</div>
          ${state.traits.length
            ? state.traits.map(t => `<div class="review-row"><span class="review-val">${t}</span></div>`).join('')
            : '<div class="text-muted" style="font-size:11px;">None selected</div>'}
        </div>
      </div>

      <div>
        <div class="review-section">
          <div class="review-section-title">Combat Stats (Level ${level})</div>
          <div class="review-row"><span class="review-key">HP</span><span class="review-val">${hp + (state.favClassChoice === 'hp' ? level : 0)}${state.favClassChoice==='hp'?` (+${level} FCB)`:''}</span></div>
          <div class="review-row"><span class="review-key">AC</span><span class="review-val">${ac}</span></div>
          <div class="review-row"><span class="review-key">BAB</span><span class="review-val">${fm(bab)}</span></div>
          <div class="review-row"><span class="review-key">Initiative</span><span class="review-val">${fm(dexMod)}</span></div>
          <div class="review-row"><span class="review-key">Fort</span><span class="review-val">${fm(fort)}</span></div>
          <div class="review-row"><span class="review-key">Ref</span><span class="review-val">${fm(ref)}</span></div>
          <div class="review-row"><span class="review-key">Will</span><span class="review-val">${fm(will)}</span></div>
          <div class="review-row"><span class="review-key">CMB</span><span class="review-val">${fm(bab+strMod)}</span></div>
          <div class="review-row"><span class="review-key">CMD</span><span class="review-val">${10+bab+strMod+dexMod}</span></div>
          ${state.equippedArmor ? `<div class="review-row"><span class="review-key">Armor</span><span class="review-val">${esc(state.equippedArmor.name)}</span></div>` : ''}
          ${state.equippedShield ? `<div class="review-row"><span class="review-key">Shield</span><span class="review-val">${esc(state.equippedShield.name)}</span></div>` : ''}
          ${state.weapons.length ? state.weapons.map(w => `<div class="review-row"><span class="review-key">Weapon</span><span class="review-val">${esc(w.name)} ${w.damage_medium||''} ${w.critical||''}</span></div>`).join('') : ''}
        </div>

        <div class="review-section">
          <div class="review-section-title">Skill Ranks (${usedSkillRanks()} / ${skillBudget()})</div>
          ${Object.entries(state.skillRanks).filter(([,v])=>v>0).map(([sk,r]) =>
            `<div class="review-row"><span class="review-key">${sk}</span><span class="review-val">${r} rank${r>1?'s':''}</span></div>`
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
      "Save & View Sheet" saves the character and opens the sheet in a new tab.
    </p>
  </div>

  <div class="nav-bar">
    <button class="btn" onclick="prevStep()">← Back</button>
    <div></div>
  </div>`;
}

// ── Navigation ────────────────────────────────────────────────────────────
function validateCurrentStep() {
  switch(state.currentStep) {
    case 0: {  // Origins
      if (!state.name.trim()) return ['Character name is required.'];
      if (!state.race) return ['Please select a race.'];
      if (state.race.flexible_bonus && !state.flexBonus) return ['Please choose your +2 ability score bonus.'];
      if (!state.className) return ['Please select a class.'];
      return [];
    }
    case 1: {  // Abilities
      const final = getFinalScores();
      if (Object.values(final).some(v => v < 3)) return ['Ability scores cannot be below 3.'];
      if (state.abilityMethod === 'pointbuy') {
        const cost = Object.values(state.baseScores).reduce((s,v) => s+(PB_COSTS[v]||0), 0);
        if (cost > PB_BUDGET) return [`Point buy over budget by ${cost - PB_BUDGET} points.`];
      }
      if (state.abilityMethod === 'standard') {
        const assigned = Object.values(state.saAssign).filter(Boolean).map(Number);
        if (assigned.length < 6) return ['Assign all 6 ability scores.'];
        const dups = assigned.filter((v,i) => assigned.indexOf(v) !== i);
        if (dups.length) return ['Each value can only be assigned once.'];
      }
      return [];
    }
    case 2: return [];   // Feats & Traits
    case 3: return [];   // Extras
    case 4:              // Skills
      if (usedSkillRanks() > skillBudget()) return ['Too many skill ranks allocated.'];
      return [];
    case 5: return [];   // Review
  }
  return [];
}

function syncCurrentStepState() {
  if (state.currentStep === 0) {
    state.name       = document.getElementById('inp-name')?.value?.trim()  || state.name;
    state.playerName = document.getElementById('inp-player')?.value?.trim() || state.playerName;
    state.alignment  = document.getElementById('inp-alignment')?.value      || state.alignment;
    const lvl = parseInt(document.getElementById('inp-level')?.value);
    if (!isNaN(lvl) && lvl >= 1 && lvl <= 20) state.startLevel = lvl;
    const flex = document.getElementById('flex-bonus');
    if (flex) state.flexBonus = flex.value || null;
  }
  if (state.currentStep === 3) {
    // Save equipment from textarea
    const equip = document.getElementById('equipment-input');
    if (equip) {
      state.equipment = equip.value.split('\n').map(s => s.trim()).filter(Boolean);
    }
  }
}

window.nextStep = function() {
  syncCurrentStepState();
  const errors = validateCurrentStep();
  if (errors.length) { showErrors(errors); return; }

  // Fix 7: warn if skill ranks are unspent
  if (state.currentStep === 4) {  // skills step
    const remaining = skillBudget() - usedSkillRanks();
    if (remaining > 0) {
      if (!confirm(`You have ${remaining} unspent skill rank${remaining > 1 ? 's' : ''}. Continue anyway?`)) return;
    }
  }

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

// ── Build character dict ──────────────────────────────────────────────────
function buildCharDict() {
  computeBaseScores();
  const final    = getFinalScores();
  const classRow = state.classRow;
  const level    = state.startLevel;
  const hitDie   = classRow?.hit_die || 'd8';
  const dieSize  = parseInt(hitDie.slice(1)) || 8;
  const avgRoll  = {d6:4,d8:5,d10:6,d12:7}[hitDie] || 5;
  const hpL1 = Math.max(1, dieSize + mod(final.con));
  const hpBase = hpL1 + (level > 1 ? Math.max(1, avgRoll + mod(final.con)) * (level - 1) : 0);
  const hpFCB  = state.favClassChoice === 'hp' ? level : 0;
  const hp = hpBase + hpFCB;

  return {
    id: null,
    name: state.name,
    player_name: state.playerName,
    alignment: state.alignment,
    race: state.race?.name || '',
    ability_scores: final,
    class_levels: state.className ? [{
      class_name: state.className,
      level: level,
      archetype_name: state.archetypeName || null,
    }] : [],
    feats: state.feats.map(f => f.name),
    feat_details: state.feats.map(f => ({ name: f.name, level: f.level, method: f.method })),
    traits: [...state.traits],
    skills: { ...state.skillRanks },
    equipment: [...state.equipment],
    equipped_armor:  state.equippedArmor  || null,
    equipped_shield: state.equippedShield || null,
    weapons: [...state.weapons],
    conditions: [],
    hp_max: hp,
    hp_current: hp,
    fav_class_choice: state.favClassChoice,
    class_talents: [...state.classTalents],
    spells: { ...state.spells },
    notes: '',
  };
}

// ── Export actions ────────────────────────────────────────────────────────
window.saveCharacter = async function() {
  const char = buildCharDict();
  try {
    const result = await apiPost('/characters', char);
    addToHistory(result.id, char);
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
  a.download = `${(char.name||'character').replace(/\s+/g,'_')}.json`;
  a.click();
};

window.saveAndViewSheet = async function() {
  const char = buildCharDict();
  try {
    const result = await apiPost('/characters', char);
    addToHistory(result.id, char);
    renderHistory();
    window.open(`/api/characters/${result.id}/sheet`, '_blank');
  } catch(e) {
    alert('Error: ' + e.message);
  }
};

// ── Character library ─────────────────────────────────────────────────────
window.openCharList = async function() {
  const modal   = document.getElementById('char-list-modal');
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
  state.name       = char.name         || '';
  state.playerName = char.player_name  || '';
  state.alignment  = char.alignment    || 'True Neutral';
  if (char.race && state._races) {
    state.race = state._races.find(r => r.name === char.race) || null;
  }
  if (char.ability_scores) {
    state.baseScores  = { ...char.ability_scores };
    state.abilityMethod = 'manual';
  }
  if (char.class_levels?.[0]) {
    state.className    = char.class_levels[0].class_name;
    state.archetypeName = char.class_levels[0].archetype_name || null;
    state.startLevel   = char.class_levels[0].level || 1;
    if (state._classes) {
      state.classRow = state._classes.find(c => c.name === state.className) || null;
    }
  }
  // Backward-compatible feats: strings → objects
  const rawFeats = char.feats || [];
  const featDetails = char.feat_details || [];
  state.feats = rawFeats.map((f, i) => {
    if (typeof f === 'object' && f.name) return f;
    const detail = featDetails[i];
    return detail ? { name: detail.name, level: detail.level, method: detail.method }
                  : { name: String(f), level: 1, method: 'general' };
  });
  state.traits         = char.traits           || [];
  state.skillRanks     = char.skills           || {};
  state.favClassChoice = char.fav_class_choice || 'hp';
  state.classTalents   = char.class_talents    || [];
  state.spells         = char.spells           || {};
  state.equipment      = char.equipment        || [];
  state.equippedArmor  = char.equipped_armor   || null;
  state.equippedShield = char.equipped_shield  || null;
  state.weapons        = char.weapons          || [];

  document.getElementById('char-list-modal').style.display = 'none';
  state.currentStep = 5;
  state.maxReached  = 5;
  renderTracker();
  renderStep();
};

// ── Character history (localStorage) ─────────────────────────────────────
const HISTORY_KEY = 'pf1e_char_history';
const MAX_HISTORY = 8;

function addToHistory(id, char) {
  const history  = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  const classStr = (char.class_levels || []).map(cl =>
    `${cl.class_name} ${cl.level}${cl.archetype_name ? ' ('+cl.archetype_name+')' : ''}`
  ).join(', ');
  const entry = { id, name: char.name||'?', race: char.race||'—', class_str: classStr, saved: Date.now() };
  const deduped = history.filter(h => h.id !== id);
  deduped.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(deduped.slice(0, MAX_HISTORY)));
}

function renderHistory() {
  const el = document.getElementById('recent-chars');
  if (!el) return;
  const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  if (!history.length) { el.innerHTML = ''; return; }

  el.innerHTML = `
    <div class="panel" style="max-width:800px;margin:16px auto 0;">
      <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">
        Recent Characters
        <button class="btn btn-sm" onclick="clearHistory()">Clear</button>
      </div>
      ${history.map(c => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--gold-border);">
          <div>
            <span style="font-family:var(--font-head);font-size:13px;">${esc(c.name)}</span>
            <span class="text-muted" style="font-size:11px;margin-left:8px;">${esc(c.race)} · ${esc(c.class_str)}</span>
          </div>
          <div style="display:flex;gap:6px;">
            <a class="btn btn-sm" href="/api/characters/${c.id}/sheet" target="_blank">Sheet</a>
            <a class="btn btn-sm" href="/levelup#char=${c.id}">Level Up</a>
          </div>
        </div>`).join('')}
    </div>`;
}

window.clearHistory = function() {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
};

// ── Utilities ─────────────────────────────────────────────────────────────
function esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Encode a JS value for use inside a double-quoted HTML onclick attribute.
// JSON.stringify uses double-quotes which would break attribute parsing.
function jsAttr(val) {
  return JSON.stringify(val).replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────────────────
renderTracker();
renderStep();
renderHistory();
