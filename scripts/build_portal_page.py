import argparse
import json
import os

from dashboard_ui import REPO_ROOT, base_css, build_command_page_payload, load_project_state

DEFAULT_CONTROL_URL = 'http://127.0.0.1:8765'
CONTROL_URL_CANDIDATES = [
    DEFAULT_CONTROL_URL,
    'http://127.0.0.1:8766',
]

HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Phase 7 Command Cockpit</title>
    <style>
__BASE_CSS__
      :root {
        --page-width: 1180px;
      }
      body { background: linear-gradient(180deg, #091016 0%, #0d141b 100%); }
      .page { max-width: var(--page-width); padding-top: 26px; }
      .cockpit { display: grid; gap: 18px; margin-top: 22px; }
      .hero,
      .panel,
      .decision-card,
      .mini-panel {
        border-radius: 22px;
        border: 1px solid var(--line);
        background: linear-gradient(180deg, rgba(18, 28, 38, 0.96) 0%, rgba(15, 24, 34, 0.96) 100%);
        box-shadow: 0 22px 40px rgba(0,0,0,0.2);
      }
      .hero {
        padding: 24px;
        display: grid;
        gap: 18px;
        grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
        align-items: start;
      }
      .hero h1 { margin: 0; font-size: clamp(1.7rem, 3vw, 2.6rem); line-height: 1.02; text-wrap: balance; }
      .hero-main { display: grid; gap: 14px; }
      .hero-side { display: grid; gap: 12px; }
      .status-strip { display: flex; gap: 8px; flex-wrap: wrap; }
      .pill { display: inline-flex; align-items: center; padding: 6px 11px; border-radius: 999px; font-size: 0.76rem; font-weight: 800; background: rgba(255,255,255,0.08); color: var(--ink); }
      .pill.supported, .pill.actionable, .pill.usable, .pill.online { background: rgba(155,227,192,0.16); color: var(--positive); }
      .pill.provisional, .pill.bounded, .pill.supporting-now { background: rgba(255,211,124,0.16); color: var(--warning); }
      .pill.weak, .pill.seeded, .pill.conflicting, .pill.background, .pill.offline { background: rgba(255,182,182,0.16); color: var(--danger); }
      .pill.driving-now, .pill.primary, .pill.selected, .pill.live { background: rgba(var(--accent-rgb), 0.16); color: var(--accent); }
      .pill.none, .pill.not-available, .pill.not-specified { background: rgba(255,255,255,0.08); color: var(--muted); }
      .hero-copy { color: var(--ink); font-size: 1rem; line-height: 1.55; font-weight: 700; }
      .hero-note { color: var(--muted); line-height: 1.55; }
      .hero-meta { padding: 14px 16px; }
      .hero-meta + .hero-meta { margin-top: 0; }
      .hero-meta span,
      .field-label,
      .subsection-label { display: block; color: var(--accent); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; font-weight: 800; }
      .hero-meta strong { display: block; color: var(--ink); line-height: 1.45; }
      .hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .hero-actions .button-link,
      .hero-actions .button-inline,
      .button-inline,
      .action-button,
      .chip-button,
      .option-button {
        appearance: none;
        font: inherit;
      }
      .button-inline,
      .action-button,
      .chip-button {
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.05);
        color: var(--ink);
        cursor: pointer;
        font-weight: 800;
      }
      .button-inline,
      .action-button { padding: 10px 14px; }
      .chip-button { padding: 8px 12px; }
      .button-inline.primary,
      .action-button.primary { background: var(--accent); color: #081118; border-color: transparent; }
      .button-inline[disabled],
      .action-button[disabled],
      .chip-button[disabled],
      .option-button[disabled],
      .ask-input[disabled],
      .write-in[disabled],
      .note-input[disabled] {
        opacity: 0.55;
        cursor: not-allowed;
      }
      .button-inline:not([disabled]):hover,
      .action-button:not([disabled]):hover,
      .chip-button:not([disabled]):hover,
      .option-button:not([disabled]):hover {
        border-color: rgba(var(--accent-rgb), 0.32);
      }
      .panel { padding: 22px; }
      .section-top { display: flex; justify-content: space-between; gap: 16px; align-items: end; flex-wrap: wrap; margin-bottom: 14px; }
      .section-top h2 { margin-bottom: 0; }
      .section-top p { max-width: 70ch; color: var(--muted); line-height: 1.5; }
      .offline-banner {
        padding: 12px 14px;
        border-radius: 16px;
        border: 1px solid rgba(255, 211, 124, 0.25);
        background: rgba(255, 211, 124, 0.1);
        color: var(--warning);
        display: none;
      }
      .offline .offline-banner { display: block; }
      .decision-card { padding: 20px; display: grid; gap: 14px; }
      .decision-card.primary { border-color: rgba(var(--accent-rgb), 0.28); }
      .decision-header { display: flex; justify-content: space-between; gap: 12px; align-items: start; flex-wrap: wrap; }
      .decision-title h3 { margin: 6px 0 0; font-size: 1.22rem; }
      .decision-question { color: var(--ink); font-weight: 800; line-height: 1.5; }
      .decision-why { color: var(--muted); line-height: 1.55; }
      .decision-meta-grid { display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .mini-panel { padding: 14px 16px; }
      .mini-panel ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; color: var(--muted); line-height: 1.5; }
      .path-list { display: grid; gap: 8px; }
      .path-step { padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); color: var(--muted); line-height: 1.45; }
      .recommendation { padding: 14px 16px; border-radius: 16px; background: rgba(var(--accent-rgb), 0.11); border: 1px solid rgba(var(--accent-rgb), 0.16); }
      .recommendation strong { display: block; color: var(--ink); margin-bottom: 6px; }
      .option-list { display: grid; gap: 10px; }
      .option-button {
        width: 100%;
        text-align: left;
        padding: 12px 14px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.04);
        color: var(--ink);
        cursor: pointer;
      }
      .option-button.recommended { background: rgba(var(--accent-rgb), 0.12); }
      .option-button.selected { border-color: rgba(var(--accent-rgb), 0.5); background: rgba(var(--accent-rgb), 0.18); }
      .option-label { display: block; font-weight: 800; margin-bottom: 6px; }
      .option-summary { color: var(--muted); line-height: 1.45; font-size: 0.92rem; }
      .card-actions { display: flex; gap: 10px; flex-wrap: wrap; }
      .secondary-grid { display: grid; gap: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .progress-grid { display: grid; gap: 14px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .progress-card { padding: 16px; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07); }
      .progress-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; margin-bottom: 10px; }
      .progress-head strong { font-size: 1.02rem; }
      .progress-head span { color: var(--accent); font-weight: 800; }
      .rail { width: 100%; height: 10px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; margin-bottom: 12px; }
      .rail-fill { height: 100%; background: linear-gradient(90deg, rgba(var(--accent-rgb), 0.92), rgba(155,227,192,0.92)); }
      .checkpoint-list { display: grid; gap: 8px; }
      .checkpoint { display: flex; gap: 8px; align-items: center; color: var(--muted); font-size: 0.92rem; }
      .checkpoint-mark { width: 8px; height: 8px; border-radius: 999px; background: rgba(255,255,255,0.18); flex: 0 0 auto; }
      .checkpoint.complete .checkpoint-mark { background: var(--accent); }
      .phase-grid { display: grid; gap: 12px; grid-template-columns: repeat(6, minmax(0, 1fr)); margin-top: 14px; }
      .phase-card { padding: 12px; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); display: grid; gap: 7px; }
      .phase-card strong { line-height: 1.4; }
      .phase-card p { color: var(--muted); font-size: 0.84rem; line-height: 1.4; }
      .discovery-grid { display: grid; gap: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .discovery-card { padding: 18px; border-radius: 18px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }
      .discovery-card ul { margin: 0; padding-left: 18px; display: grid; gap: 10px; color: var(--muted); line-height: 1.55; }
      .ask-grid,
      .action-grid,
      .timeline-grid { display: grid; gap: 14px; grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr); }
      .ask-panel,
      .answer-shell,
      .action-shell,
      .timeline-shell,
      .history-shell { display: grid; gap: 12px; }
      .ask-input,
      .write-in,
      .note-input {
        width: 100%;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(0,0,0,0.14);
        color: var(--ink);
        font: inherit;
      }
      .write-in,
      .ask-input { min-height: 110px; resize: vertical; }
      .ask-toolbar,
      .action-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
      .answer-card,
      .action-card,
      .timeline-item,
      .history-item {
        padding: 14px 16px;
        border-radius: 16px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
      }
      .answer-card h3,
      .action-card h3 { font-size: 1rem; margin: 0 0 8px; }
      .answer-card p,
      .action-card p { color: var(--muted); line-height: 1.5; }
      .action-status { min-height: 54px; }
      .timeline-item strong,
      .history-item strong { display: block; margin-bottom: 6px; }
      .item-meta { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
      .support-footer {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        padding: 2px 2px 18px;
      }
      .support-footer .muted-note { margin-right: 6px; }
      .muted-note,
      .empty-note { color: var(--muted); }
      @media (max-width: 1080px) {
        .hero,
        .ask-grid,
        .action-grid,
        .timeline-grid { grid-template-columns: 1fr; }
        .phase-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      }
      @media (max-width: 760px) {
        .decision-meta-grid,
        .progress-grid,
        .discovery-grid,
        .secondary-grid,
        .phase-grid { grid-template-columns: 1fr; }
        .page { padding-left: 16px; padding-right: 16px; }
        .hero { padding: 20px; }
      }
    </style>
  </head>
  <body>
    <main class=\"page\">
      <div class=\"cockpit\" id=\"cockpitApp\"></div>
    </main>
    <script>
      const DEFAULT_CONTROL_URL = __CONTROL_URL__;
      const CONTROL_URL_CANDIDATES = __CONTROL_URL_CANDIDATES__;
      const COMMAND_PAGE_ENDPOINT = '/api/command-page';
      const CLARIFY_ENDPOINT = '/api/clarify-question';
      const APPLY_ENDPOINT = '/api/apply-decision';
      const EMBEDDED_PAYLOAD = __SNAPSHOT__;
      const ui = {
        payload: EMBEDDED_PAYLOAD,
        online: false,
        activeDecisionId: '',
        askQuestion: '',
        selectedOptions: {},
        actionNote: '',
        actionWriteIn: '',
        actionMessage: 'Choose a decision, stage an option, and apply it from this panel.',
        aiResponse: null,
        pendingConfirmation: null,
      };
      let activeControlUrl = '';

      function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>\"']/g, (char) => ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '\"': '&quot;',
          "'": '&#39;'
        })[char]);
      }

      function slugToken(value) {
        return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'none';
      }

      function sectionHeader(eyebrow, title, detail) {
        return `
          <div class=\"section-top\">
            <div>
              <p class=\"eyebrow\">${escapeHtml(eyebrow)}</p>
              <h2>${escapeHtml(title)}</h2>
            </div>
            <p>${escapeHtml(detail)}</p>
          </div>
        `;
      }

      function uniqueValues(values) {
        const seen = new Set();
        return values.filter((value) => {
          const clean = String(value || '').trim();
          if (!clean || seen.has(clean)) return false;
          seen.add(clean);
          return true;
        });
      }

      function sameOriginControlUrl() {
        if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
          return window.location.origin;
        }
        return '';
      }

      function discoverControlUrls() {
        const params = new URLSearchParams(window.location.search);
        const queryUrl = params.get('control_url') || '';
        const storedUrl = window.localStorage ? window.localStorage.getItem('atlas-control-url') : '';
        return uniqueValues([queryUrl, storedUrl, sameOriginControlUrl()].concat(CONTROL_URL_CANDIDATES));
      }

      async function fetchControlJson(endpoint, options = {}) {
        const candidates = uniqueValues((activeControlUrl ? [activeControlUrl] : []).concat(discoverControlUrls()));
        let lastError = new Error('The local control server is unavailable.');
        for (const baseUrl of candidates) {
          try {
            const response = await fetch(`${baseUrl}${endpoint}`, options);
            const result = await response.json();
            if (!response.ok || result.ok === false) {
              lastError = new Error(result.error || `Control request failed at ${baseUrl}.`);
              continue;
            }
            activeControlUrl = baseUrl;
            if (window.localStorage) {
              window.localStorage.setItem('atlas-control-url', baseUrl);
            }
            return result;
          } catch (error) {
            lastError = error;
          }
        }
        throw lastError;
      }

      function decisionList(payload) {
        const primary = payload.primary_decision ? [payload.primary_decision] : [];
        const secondary = Array.isArray(payload.secondary_decisions) ? payload.secondary_decisions.slice(0, 2) : [];
        return primary.concat(secondary).filter((decision) => decision && decision.decision_id);
      }

      function getDecision(decisionId) {
        return decisionList(ui.payload).find((decision) => decision.decision_id === decisionId) || null;
      }

      function getActiveDecision() {
        return getDecision(ui.activeDecisionId) || decisionList(ui.payload)[0] || null;
      }

      function getSelectedOption(decisionId) {
        const decision = getDecision(decisionId);
        if (!decision) return null;
        const selectedId = ui.selectedOptions[decisionId];
        if (!selectedId) return null;
        return (decision.options || []).find((option) => option.id === selectedId) || null;
      }

      function ensureActiveDecision() {
        const decisions = decisionList(ui.payload);
        if (!decisions.length) {
          ui.activeDecisionId = '';
          return;
        }
        if (!getDecision(ui.activeDecisionId)) {
          ui.activeDecisionId = decisions[0].decision_id;
        }
      }

      function pillsForDecision(decision) {
        const noveltyPill = decision.novelty_status && decision.novelty_status !== 'tbi_established'
          ? `<span class=\"pill ${slugToken(decision.novelty_status)}\">${escapeHtml(decision.novelty_status)}</span>`
          : '';
        return `
          <div class=\"status-strip\">
            <span class=\"pill ${slugToken(decision.support_status)}\">${escapeHtml(decision.support_status || 'not specified')}</span>
            <span class=\"pill live\">${escapeHtml(decision.decision_family_label || decision.decision_family || 'Decision')}</span>
            ${noveltyPill}
          </div>
        `;
      }

      function renderHero(payload) {
        const status = payload.program_status || {};
        const direction = payload.current_direction || {};
        const manuscript = payload.goal_progress?.current_manuscript_candidate || {};
        const nextPaper = payload.goal_progress?.next_paper_opportunity || {};
        const onlinePill = `<span class=\"pill ${ui.online ? 'online' : 'offline'}\">${ui.online ? 'Live control online' : 'Offline snapshot'}</span>`;
        const statusLine = ui.online
          ? 'Live control is connected. Choices and questions post directly to the local command server.'
          : 'The cockpit is using its embedded fallback snapshot. You can review the page offline, but question and apply actions stay disabled until live control is back.';
        return `
          <div class=\"offline-banner\">Live control is offline. The cockpit is still usable as a read-only fallback snapshot, and all server actions stay disabled until /api/command-page responds again.</div>
          <section class=\"hero\">
            <div class=\"hero-main\">
              <p class=\"eyebrow\">Current Brief</p>
              <h1>Where the Project Stands</h1>
              <div class=\"status-strip\">${onlinePill}</div>
              <p class=\"hero-copy\">${escapeHtml(status.line || '')}</p>
              <p class=\"hero-note\">${escapeHtml(status.paragraph || '')}</p>
              <div class=\"mini-panel\">
                <span class=\"field-label\">Current direction</span>
                <strong>${escapeHtml(direction.label || 'Direction not emitted')}</strong>
                <p class=\"hero-note\">${escapeHtml(direction.reason || status.current_direction_line || '')}</p>
              </div>
              <div class=\"hero-actions\">
                <button class=\"button-inline primary ${ui.online ? '' : ''}\" id=\"refreshCommandButton\">Refresh live state</button>
              </div>
            </div>
            <div class=\"hero-side\">
              <div class=\"hero-meta mini-panel\">
                <span>Current paper path</span>
                <strong>${escapeHtml(manuscript.title || 'Not selected yet')}</strong>
                <p class=\"muted-note\">${escapeHtml(manuscript.story || '')}</p>
                <span style=\"margin-top:10px;\">Next paper opportunity</span>
                <strong>${escapeHtml(nextPaper.title || 'No secondary paper path emitted')}</strong>
              </div>
            </div>
          </section>
        `;
      }

      function renderMetaList(items) {
        if (!Array.isArray(items) || !items.length) {
          return '<p class=\"empty-note\">Nothing explicit is emitted in this snapshot.</p>';
        }
        return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
      }

      function optionButtonDetail(option) {
        return escapeHtml(option.paper_effect || option.future_effect || option.immediate_action || option.what_it_steers || '');
      }

      function optionDetail(option) {
        const parts = [option.what_it_steers, option.immediate_action, option.future_effect, option.paper_effect].filter(Boolean);
        return escapeHtml(parts.join(' '));
      }

      function renderDecisionCard(decision, primary = false) {
        if (!decision) {
          return `<article class=\"decision-card ${primary ? 'primary' : ''}\"><p class=\"empty-note\">No decision emitted for this slot.</p></article>`;
        }
        const selected = ui.selectedOptions[decision.decision_id] || '';
        const visibleKnow = primary ? renderMetaList(decision.what_we_know) : '';
        const visibleUncertain = primary ? renderMetaList(decision.what_is_uncertain) : '';
        const options = (decision.options || []).map((option) => `
          <button
            class=\"option-button ${selected === option.id ? 'selected' : ''} ${decision.recommended_option_id === option.id ? 'recommended' : ''}\"
            data-role=\"stage-option\"
            data-decision-id=\"${escapeHtml(decision.decision_id)}\"
            data-option-id=\"${escapeHtml(option.id)}\"
            ${ui.online ? '' : 'disabled'}>
            <span class=\"option-label\">${escapeHtml(option.label)}</span>
            <span class=\"option-summary\">${escapeHtml(optionButtonDetail(option))}</span>
          </button>
        `).join('');
        return `
          <article class=\"decision-card ${primary ? 'primary' : ''}\" id=\"${escapeHtml(decision.decision_id)}\">
            <div class=\"decision-header\">
              <div class=\"decision-title\">
                <h3>${escapeHtml(decision.decision_title || 'Decision')}</h3>
              </div>
              ${pillsForDecision(decision)}
            </div>
            <p class=\"decision-question\">${escapeHtml(decision.human_question || '')}</p>
            <p class=\"decision-why\">${escapeHtml(decision.why_now || decision.statement || '')}</p>
            <div class=\"decision-meta-grid\" style=\"display:${primary ? 'grid' : 'none'};\">
              <div class=\"mini-panel\">
                <span class=\"field-label\">What we know</span>
                ${visibleKnow}
              </div>
              <div class=\"mini-panel\">
                <span class=\"field-label\">What is uncertain</span>
                ${visibleUncertain}
              </div>
            </div>
            <div class=\"recommendation\">
              <span class=\"field-label\">Recommended path</span>
              <strong>${escapeHtml(decision.recommended_reason || 'No recommendation emitted.')}</strong>
            </div>
            ${primary ? `
              <details>
                <summary>How the engine got here</summary>
                <div class=\"mini-panel\" style=\"margin-top:10px;\">
                  <span class=\"field-label\">Phase path</span>
                  <div class=\"path-list\">${(decision.phase_path || []).map((item) => `<div class=\"path-step\">${escapeHtml(item)}</div>`).join('') || '<p class=\"empty-note\">No phase path emitted.</p>'}</div>
                </div>
              </details>
            ` : ''}
            <div class=\"option-list\">${options || '<p class=\"empty-note\">No options emitted.</p>'}</div>
            <div class=\"card-actions\">
              <button class=\"button-inline\" data-role=\"set-active-decision\" data-decision-id=\"${escapeHtml(decision.decision_id)}\">Work on this</button>
            </div>
          </article>
        `;
      }

      function renderPrimaryDecision(payload) {
        return `
          <section class=\"panel\">
            ${sectionHeader('Main Decision', 'What You Need to Decide Now', 'This choice should guide the next cycle and the current paper path.')}
            ${renderDecisionCard(payload.primary_decision, true)}
          </section>
        `;
      }

      function renderSecondaryDecisions(payload) {
        const secondary = (payload.secondary_decisions || []).slice(0, 2);
        const body = secondary.length
          ? secondary.map((decision) => renderDecisionCard(decision, false)).join('')
          : '<div class=\"decision-card\"><p class=\"empty-note\">No secondary decisions are active in this snapshot.</p></div>';
        return `
          <section class=\"panel\">
            ${sectionHeader('Keep in View', 'Other Decisions Worth Keeping Nearby', 'These may matter next, but they should not outrank the main choice.')}
            <div class=\"secondary-grid\">${body}</div>
          </section>
        `;
      }

      function renderProgress(payload) {
        const stages = payload.goal_progress?.stages || [];
        const cards = stages.map((stage) => {
          const percent = stage.percent || 0;
          const checkpoints = (stage.checkpoints || []).map((checkpoint) => `
            <div class=\"checkpoint ${checkpoint.complete ? 'complete' : ''}\">
              <span class=\"checkpoint-mark\"></span>
              <span>${escapeHtml(checkpoint.label)}</span>
            </div>
          `).join('');
          return `
            <article class=\"progress-card\">
              <div class=\"progress-head\">
                <strong>${escapeHtml(stage.label)}</strong>
                <span>${stage.completed || 0} / ${stage.total || 0}</span>
              </div>
              <div class=\"rail\"><div class=\"rail-fill\" style=\"width:${percent}%\"></div></div>
              <div class=\"checkpoint-list\">${checkpoints}</div>
            </article>
          `;
        }).join('');
        const phases = (payload.phases || []).map((phase) => `
          <article class=\"phase-card\">
            <p class=\"eyebrow\">${escapeHtml(phase.phase_label || '')}</p>
            <strong>${escapeHtml(phase.phase_title || '')}</strong>
            <p>${escapeHtml(phase.role_line || '')}</p>
            <div class=\"status-strip\">
              <span class=\"pill ${slugToken(phase.maturity)}\">${escapeHtml(phase.maturity || 'not specified')}</span>
              <span class=\"pill ${slugToken(phase.pull)}\">${escapeHtml(phase.pull || 'not specified')}</span>
            </div>
          </article>
        `).join('');
        return `
          <section class=\"panel\">
            ${sectionHeader('Progress', 'Progress to the Next Paper', 'The rails show how close the current path is to a defensible manuscript story. The phase strip shows what is pulling weight now.')}
            <div class=\"progress-grid\">${cards}</div>
            <div class=\"phase-grid\">${phases}</div>
          </section>
        `;
      }

      function renderDiscovery(payload) {
        const findings = (payload.discovery_summary?.major_findings || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('');
        const unknowns = (payload.discovery_summary?.current_unknowns || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('');
        return `
          <section class=\"panel\">
            ${sectionHeader('What We Know', 'What the Engine Has Found So Far', 'This is the shortest readout of what looks real and what is still blocking us.')}
            <div class=\"discovery-grid\">
              <article class=\"discovery-card\">
                <span class=\"field-label\">Major findings</span>
                <ul>${findings || '<li>No major findings emitted.</li>'}</ul>
              </article>
              <article class=\"discovery-card\">
                <span class=\"field-label\">Current unknowns</span>
                <ul>${unknowns || '<li>No current unknowns emitted.</li>'}</ul>
              </article>
            </div>
          </section>
        `;
      }

      function renderAskAi(payload) {
        const presets = (payload.control_state?.preset_questions || []).map((question) => `
          <button class=\"chip-button\" data-role=\"preset-question\" data-question=\"${escapeHtml(question)}\" ${ui.online ? '' : 'disabled'}>${escapeHtml(question)}</button>
        `).join('');
        const active = getActiveDecision();
        const contextLine = active
          ? `Questions are aimed at the active decision: ${active.decision_title}.`
          : 'Questions are aimed at the whole page.';
        const answer = ui.aiResponse || {
          answer: 'Ask the cockpit to explain what was discovered, why something is recommended, or what happens if you take a different path.',
          evidence_chain: ['The answer will tie back to the current phase outputs and decision payload.'],
          implication: 'This is where you check whether the recommendation is understandable enough to act on.',
          recommended_follow_up: 'If the answer changes your confidence, move straight to the action panel below.',
        };
        const evidenceText = Array.isArray(answer.evidence_chain) ? answer.evidence_chain.join(' ') : (answer.evidence_chain || '');
        return `
          <section class=\"panel\">
            ${sectionHeader('Clarify', 'Ask a Question Before You Commit', 'Use this when you want the recommendation explained in plain English.')}
            <div class=\"ask-grid\">
              <div class=\"ask-panel\">
                <div class=\"ask-toolbar\">${presets}</div>
                <label class=\"field-label\" for=\"clarifyQuestion\">Question</label>
                <textarea class=\"ask-input\" id=\"clarifyQuestion\" placeholder=\"Ask what the engine discovered, why a recommendation is leading, or what another option would change.\" ${ui.online ? '' : 'disabled'}>${escapeHtml(ui.askQuestion)}</textarea>
                <div class=\"action-buttons\">
                  <button class=\"action-button primary\" id=\"askAiButton\" ${ui.online ? '' : 'disabled'}>Ask</button>
                </div>
                <p class=\"muted-note\" id=\"askAiContext\">${escapeHtml(contextLine)}</p>
              </div>
              <div class=\"answer-shell\" id=\"aiAnswerShell\">
                <div class=\"answer-card\"><h3>Answer</h3><p>${escapeHtml(answer.answer || '')}</p></div>
                <div class=\"answer-card\"><h3>Evidence chain</h3><p>${escapeHtml(evidenceText)}</p></div>
                <div class=\"answer-card\"><h3>Implication</h3><p>${escapeHtml(answer.implication || '')}</p></div>
                <div class=\"answer-card\"><h3>Recommended follow-up</h3><p>${escapeHtml(answer.recommended_follow_up || '')}</p></div>
              </div>
            </div>
          </section>
        `;
      }

      function renderActionPanel(payload) {
        const active = getActiveDecision();
        const selected = active ? getSelectedOption(active.decision_id) : null;
        const pending = ui.pendingConfirmation;
        const selectedSummary = selected
          ? `<strong>${escapeHtml(selected.label)}</strong><p>${escapeHtml(optionDetail(selected))}</p>`
          : '<strong>No option staged yet</strong><p>Pick an option in one of the decision cards above to stage it here.</p>';
        const confirmationCard = pending ? `
          <div class=\"action-card\">
            <h3>Confirmation needed</h3>
            <p>${escapeHtml(pending.explanation || 'The cockpit needs you to confirm the interpreted instruction before it executes it.')}</p>
            <p class=\"muted-note\">${escapeHtml(pending.summary || '')}</p>
            <div class=\"action-buttons\">
              <button class=\"action-button primary\" id=\"confirmWriteInButton\" ${ui.online ? '' : 'disabled'}>Confirm and apply</button>
              <button class=\"action-button\" id=\"cancelWriteInConfirmationButton\">Cancel</button>
            </div>
          </div>
        ` : '';
        return `
          <section class=\"panel\">
            ${sectionHeader('Apply', 'Record Your Choice and Move the Engine', 'Choose an option above, then apply it here or write your own instruction.')}
            <div class=\"action-grid\">
              <div class=\"action-shell\">
                <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Working on:</strong> ${escapeHtml(active?.decision_title || 'No active decision')}.</p>
                <div class=\"action-card\">
                  <h3>Choice ready to apply</h3>
                  ${selectedSummary}
                </div>
                <label class=\"field-label\" for=\"actionNote\">Optional note</label>
                <input class=\"note-input\" id=\"actionNote\" type=\"text\" placeholder=\"Add a short note for the command log if helpful.\" ${ui.online ? '' : 'disabled'} value=\"${escapeHtml(ui.actionNote)}\" />
                <div class=\"action-buttons\">
                  <button class=\"action-button primary\" id=\"applyOptionButton\" ${ui.online && active && selected ? '' : 'disabled'}>Apply this choice</button>
                  <button class=\"action-button\" id=\"clearStagedOptionButton\">Clear</button>
                </div>
              </div>
              <div class=\"action-shell\">
                <label class=\"field-label\" for=\"writeInInstruction\">Or write your own instruction</label>
                <textarea class=\"write-in\" id=\"writeInInstruction\" placeholder=\"If none of the staged options fit, write the instruction in plain English here.\" ${ui.online ? '' : 'disabled'}>${escapeHtml(ui.actionWriteIn)}</textarea>
                <div class=\"action-buttons\">
                  <button class=\"action-button\" id=\"applyWriteInButton\" ${ui.online && active ? '' : 'disabled'}>Interpret and apply</button>
                </div>
                ${confirmationCard}
                <div class=\"action-card action-status\" id=\"actionStatus\">
                  <h3>Action status</h3>
                  <p>${escapeHtml(ui.actionMessage)}</p>
                </div>
              </div>
            </div>
          </section>
        `;
      }

      function renderTimelineHistory(payload) {
        const timeline = (payload.phase_timeline || []).map((item) => `
          <article class=\"timeline-item\">
            <div class=\"item-meta\">
              <span class=\"pill ${slugToken(item.status)}\">${escapeHtml(item.status || 'phase')}</span>
              <span class=\"pill\">${escapeHtml(item.date || '')}</span>
            </div>
            <strong>${escapeHtml(item.title || '')}</strong>
            <p>${escapeHtml(item.summary || '')}</p>
          </article>
        `).join('');
        const history = (payload.decision_history || []).map((item) => {
          const actionMessage = typeof item.triggered_action === 'object' ? (item.triggered_action.message || '') : (item.triggered_action || '');
          return `
            <article class=\"history-item\">
              <div class=\"item-meta\">
                <span class=\"pill live\">${escapeHtml(item.selected_option_id || 'recorded')}</span>
                <span class=\"pill\">${escapeHtml(item.timestamp || '')}</span>
              </div>
              <strong>${escapeHtml(item.decision_title || 'Prior decision')}</strong>
              <p>${escapeHtml(item.ai_explanation || item.interpreted_intent || 'No explanation recorded.')}</p>
              <p class=\"muted-note\">${escapeHtml(actionMessage)}</p>
            </article>
          `;
        }).join('');
        return `
          <section class=\"panel\">
            <details>
              <summary>Earlier work and prior decisions</summary>
              <p class=\"muted-note\" style=\"margin:12px 0 14px;\">Use this only when you need to trace how the stack got here or review prior choices.</p>
              <div class=\"timeline-grid\">
                <div class=\"timeline-shell\">
                  ${timeline || '<p class=\"empty-note\">No timeline entries were emitted.</p>'}
                </div>
                <div class=\"history-shell\">
                  ${history || '<div class=\"history-item\"><strong>No human steering history yet</strong><p class=\"muted-note\">Once apply-decision has been used, the cockpit will show the recorded choices here.</p></div>'}
                </div>
              </div>
            </details>
          </section>
        `;
      }

      function renderSupportLinks(payload) {
        const links = (payload.support_links || []).map((item) => `
          <a class=\"button-link\" href=\"${escapeHtml(item.href)}\">${escapeHtml(item.label)}</a>
        `).join('');
        return `
          <footer class=\"support-footer\">
            <span class=\"muted-note\">Need more detail?</span>
            ${links}
          </footer>
        `;
      }

      function renderApp() {
        ensureActiveDecision();
        const app = document.getElementById('cockpitApp');
        document.body.classList.toggle('offline', !ui.online);
        app.innerHTML = [
          renderHero(ui.payload),
          renderProgress(ui.payload),
          renderPrimaryDecision(ui.payload),
          renderDiscovery(ui.payload),
          renderSecondaryDecisions(ui.payload),
          renderAskAi(ui.payload),
          renderActionPanel(ui.payload),
          renderTimelineHistory(ui.payload),
          renderSupportLinks(ui.payload),
        ].join('');
        installHandlers();
      }

      async function fetchCommandPage() {
        try {
          const result = await fetchControlJson(COMMAND_PAGE_ENDPOINT, { headers: { 'Accept': 'application/json' } });
          ui.payload = result.payload || EMBEDDED_PAYLOAD;
          ui.online = true;
          ui.actionMessage = `Live control is connected at ${activeControlUrl}. Stage a choice above or ask the AI for clarification.`;
        } catch (error) {
          ui.payload = EMBEDDED_PAYLOAD;
          ui.online = false;
          ui.actionMessage = 'Live control is offline. Review the embedded fallback snapshot until /api/command-page comes back.';
        }
        renderApp();
      }

      function setActiveDecision(decisionId) {
        if (!decisionId) return;
        ui.activeDecisionId = decisionId;
        renderApp();
      }

      async function askAi(question) {
        if (!ui.online || !question.trim()) return;
        ui.aiResponse = {
          answer: 'Thinking through the current repo state…',
          evidence_chain: ['The cockpit is waiting for /api/clarify-question.'],
          implication: 'This answer will be attached to the current decision focus.',
          recommended_follow_up: 'If the answer changes your confidence, move to the action panel.',
        };
        renderApp();
        try {
          const result = await fetchControlJson(CLARIFY_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({
              question,
              decision_id: ui.activeDecisionId || undefined,
            }),
          });
          ui.aiResponse = result;
        } catch (error) {
          ui.aiResponse = {
            answer: error.message || 'The question could not be answered.',
            evidence_chain: ['The cockpit could not retrieve a clarification response from the local control server.'],
            implication: 'The decision state has not changed.',
            recommended_follow_up: 'Try again once the local control server is responding.',
          };
        }
        renderApp();
      }

      async function applySelectedOption() {
        const decision = getActiveDecision();
        const option = decision ? getSelectedOption(decision.decision_id) : null;
        if (!ui.online || !decision || !option) return;
        ui.actionMessage = 'Applying the staged option…';
        ui.pendingConfirmation = null;
        renderApp();
        try {
          const result = await fetchControlJson(APPLY_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({
              decision_id: decision.decision_id,
              option_id: option.id,
              note: ui.actionNote || undefined,
            }),
          });
          ui.payload = result.payload || ui.payload;
          ui.actionNote = '';
          ui.actionWriteIn = '';
          ui.aiResponse = null;
          ui.pendingConfirmation = null;
          ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The decision was applied.';
        } catch (error) {
          ui.actionMessage = error.message || 'The decision could not be applied.';
        }
        renderApp();
      }

      async function applyWriteIn() {
        const decision = getActiveDecision();
        if (!ui.online || !decision || !ui.actionWriteIn.trim()) return;
        ui.actionMessage = 'Interpreting your instruction…';
        ui.pendingConfirmation = null;
        renderApp();
        try {
          const result = await fetchControlJson(APPLY_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({
              decision_id: decision.decision_id,
              free_text: ui.actionWriteIn,
              note: ui.actionNote || undefined,
            }),
          });
          if (result.needs_confirmation) {
            const proposed = result.interpreted_decision?.matched_option_id;
            if (proposed) {
              ui.selectedOptions[decision.decision_id] = proposed;
            }
            ui.pendingConfirmation = {
              decisionId: decision.decision_id,
              freeText: ui.actionWriteIn,
              note: ui.actionNote,
              explanation: result.interpreted_decision?.explanation || 'The write-in instruction needs confirmation.',
              summary: proposed ? `The cockpit thinks you mean: ${proposed}.` : 'The cockpit could not map your instruction cleanly enough to act without confirmation.',
            };
            ui.actionMessage = result.interpreted_decision?.explanation || 'The write-in instruction needs confirmation.';
            renderApp();
            return;
          }
          ui.payload = result.payload || ui.payload;
          ui.actionNote = '';
          ui.actionWriteIn = '';
          ui.aiResponse = null;
          ui.pendingConfirmation = null;
          ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The instruction was applied.';
        } catch (error) {
          ui.actionMessage = error.message || 'The instruction could not be applied.';
        }
        renderApp();
      }

      async function confirmWriteIn() {
        const pending = ui.pendingConfirmation;
        if (!ui.online || !pending) return;
        ui.actionMessage = 'Applying the confirmed interpretation…';
        renderApp();
        try {
          const result = await fetchControlJson(APPLY_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({
              decision_id: pending.decisionId,
              free_text: pending.freeText,
              note: pending.note || undefined,
              confirmed: true,
            }),
          });
          ui.payload = result.payload || ui.payload;
          ui.actionNote = '';
          ui.actionWriteIn = '';
          ui.aiResponse = null;
          ui.pendingConfirmation = null;
          ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The confirmed instruction was applied.';
        } catch (error) {
          ui.actionMessage = error.message || 'The confirmed instruction could not be applied.';
        }
        renderApp();
      }

      function installHandlers() {
        const refreshButton = document.getElementById('refreshCommandButton');
        if (refreshButton) refreshButton.addEventListener('click', fetchCommandPage);

        document.querySelectorAll('[data-role="stage-option"]').forEach((button) => {
          button.addEventListener('click', () => {
            ui.selectedOptions[button.dataset.decisionId] = button.dataset.optionId;
            ui.activeDecisionId = button.dataset.decisionId;
            const decision = getDecision(button.dataset.decisionId);
            const option = getSelectedOption(button.dataset.decisionId);
            ui.actionMessage = option
              ? `Staged “${option.label}” for ${decision?.decision_title || 'the current decision'}. Apply it from the action panel below when ready.`
              : 'Option staged.';
            renderApp();
          });
        });

        document.querySelectorAll('[data-role="set-active-decision"]').forEach((button) => {
          button.addEventListener('click', () => setActiveDecision(button.dataset.decisionId));
        });

        document.querySelectorAll('[data-role="preset-question"]').forEach((button) => {
          button.addEventListener('click', () => {
            const question = button.dataset.question || '';
            ui.askQuestion = question;
            const field = document.getElementById('clarifyQuestion');
            if (field) field.value = question;
            askAi(question);
          });
        });

        const askButton = document.getElementById('askAiButton');
        if (askButton) {
          askButton.addEventListener('click', () => {
            const field = document.getElementById('clarifyQuestion');
            const question = field ? field.value : '';
            ui.askQuestion = question;
            askAi(question);
          });
        }

        const clarifyQuestion = document.getElementById('clarifyQuestion');
        if (clarifyQuestion) {
          clarifyQuestion.addEventListener('input', () => {
            ui.askQuestion = clarifyQuestion.value;
          });
        }

        const actionNote = document.getElementById('actionNote');
        if (actionNote) {
          actionNote.addEventListener('input', () => {
            ui.actionNote = actionNote.value;
          });
        }

        const writeIn = document.getElementById('writeInInstruction');
        if (writeIn) {
          writeIn.addEventListener('input', () => {
            ui.actionWriteIn = writeIn.value;
          });
        }

        const applyOptionButton = document.getElementById('applyOptionButton');
        if (applyOptionButton) applyOptionButton.addEventListener('click', applySelectedOption);

        const applyWriteInButton = document.getElementById('applyWriteInButton');
        if (applyWriteInButton) applyWriteInButton.addEventListener('click', applyWriteIn);

        const confirmWriteInButton = document.getElementById('confirmWriteInButton');
        if (confirmWriteInButton) confirmWriteInButton.addEventListener('click', confirmWriteIn);

        const cancelWriteInConfirmationButton = document.getElementById('cancelWriteInConfirmationButton');
        if (cancelWriteInConfirmationButton) {
          cancelWriteInConfirmationButton.addEventListener('click', () => {
            ui.pendingConfirmation = null;
            ui.actionMessage = 'Cleared the pending write-in confirmation.';
            renderApp();
          });
        }

        const clearStagedOptionButton = document.getElementById('clearStagedOptionButton');
        if (clearStagedOptionButton) {
          clearStagedOptionButton.addEventListener('click', () => {
            const decision = getActiveDecision();
            if (decision) {
              delete ui.selectedOptions[decision.decision_id];
            }
            ui.pendingConfirmation = null;
            ui.actionMessage = 'Cleared the staged option for the active decision.';
            renderApp();
          });
        }
      }

      renderApp();
      fetchCommandPage();
    </script>
  </body>
</html>
"""


def write_text(path, text_value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text_value)


def render_html(snapshot_payload):
    html = HTML_TEMPLATE
    html = html.replace('__BASE_CSS__', base_css(accent='#9fd7bd', accent_rgb='159,215,189'))
    html = html.replace('__CONTROL_URL__', json.dumps(DEFAULT_CONTROL_URL))
    html = html.replace('__CONTROL_URL_CANDIDATES__', json.dumps(CONTROL_URL_CANDIDATES))
    html = html.replace('__SNAPSHOT__', json.dumps(snapshot_payload))
    return html


def main():
    parser = argparse.ArgumentParser(description='Build the main Phase 7 command cockpit page.')
    parser.add_argument('--output-path', default='docs/index.html', help='Portal HTML output path.')
    args = parser.parse_args()

    snapshot = build_command_page_payload(load_project_state(), root_prefix='./', control_online=False)
    html = render_html(snapshot)
    write_text(os.path.join(REPO_ROOT, args.output_path), html)
    print(f'Phase 7 command cockpit written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
