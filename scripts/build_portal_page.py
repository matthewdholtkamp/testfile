import argparse
import json
import os

from dashboard_ui import REPO_ROOT, base_css, build_command_page_payload, load_direction_registry, load_project_state
from manuscript_phase8 import load_journal_registry, load_publication_tracker, materialize_manuscript_outputs

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
      .board-status-details,
      .folded-panel {
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.06);
        background: rgba(255,255,255,0.02);
      }
      .board-status-details {
        padding: 12px 14px;
      }
      .board-status-details summary,
      .folded-panel summary {
        cursor: pointer;
        list-style: none;
        color: var(--ink);
        font-weight: 800;
      }
      .board-status-details summary::-webkit-details-marker,
      .folded-panel summary::-webkit-details-marker {
        display: none;
      }
      .board-status-details summary::after,
      .folded-panel summary::after {
        content: '+';
        float: right;
        color: var(--accent);
      }
      .board-status-details[open] summary::after,
      .folded-panel[open] summary::after {
        content: '−';
      }
      .board-status-details .muted-note {
        margin: 10px 0 0;
      }
      .folded-panel {
        padding: 16px 18px;
      }
      .folded-panel summary {
        margin: -2px 0;
      }
      .folded-panel .folded-body {
        margin-top: 14px;
      }
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
      .panel-attention {
        border-color: rgba(var(--accent-rgb), 0.42);
        box-shadow: 0 0 0 1px rgba(var(--accent-rgb), 0.2), 0 24px 44px rgba(0,0,0,0.22);
      }
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
      .warning-banner {
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid rgba(255, 182, 182, 0.28);
        background: rgba(255, 182, 182, 0.08);
        color: var(--ink);
        display: grid;
        gap: 10px;
      }
      .warning-banner strong { color: var(--danger); }
      .warning-banner ul { margin: 0; padding-left: 18px; color: var(--muted); display: grid; gap: 6px; }
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
      .card-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
      .card-actions .muted-note { margin: 0; }
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
      .manuscript-grid {
        display: grid;
        gap: 14px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .manuscript-card,
      .watchlist-item,
      .tracker-item {
        padding: 16px 18px;
        border-radius: 18px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        display: grid;
        gap: 12px;
      }
      .manuscript-card.primary-lane {
        border-color: rgba(var(--accent-rgb), 0.22);
        background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.08) 0%, rgba(255,255,255,0.03) 100%);
      }
      .manuscript-head {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 12px;
        flex-wrap: wrap;
      }
      .manuscript-title strong,
      .watchlist-item strong,
      .tracker-item strong {
        display: block;
        color: var(--ink);
        line-height: 1.35;
      }
      .score-stack {
        display: grid;
        gap: 10px;
      }
      .score-row {
        display: grid;
        gap: 6px;
      }
      .score-row label {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        color: var(--muted);
        font-size: 0.88rem;
      }
      .score-row strong {
        color: var(--ink);
        font-size: 0.88rem;
      }
      .score-track {
        width: 100%;
        height: 8px;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        overflow: hidden;
      }
      .score-fill {
        height: 100%;
        background: linear-gradient(90deg, rgba(var(--accent-rgb), 0.92), rgba(155,227,192,0.92));
      }
      .manuscript-meta-list {
        display: grid;
        gap: 8px;
      }
      .manuscript-meta-list p {
        color: var(--muted);
        line-height: 1.5;
      }
      .manuscript-alert {
        padding: 12px 14px;
        border-radius: 14px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        display: grid;
        gap: 8px;
      }
      .manuscript-alert p {
        color: var(--muted);
        line-height: 1.45;
        margin: 0;
      }
      .manuscript-alert strong {
        color: var(--ink);
      }
      .watchlist-shell,
      .tracker-shell {
        display: grid;
        gap: 12px;
      }
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
        .phase-grid,
        .manuscript-grid { grid-template-columns: 1fr; }
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
      const GITHUB_API_ROOT = 'https://api.github.com';
      const GITHUB_OWNER = 'matthewdholtkamp';
      const GITHUB_REPO = 'testfile';
      const GITHUB_REF = 'main';
      const GITHUB_APPLY_WORKFLOW = 'cockpit_apply_decision.yml';
      const GITHUB_CLARIFY_WORKFLOW = 'cockpit_clarify_question.yml';
      const GITHUB_TOKEN_KEY = 'atlas-github-token';
      const GITHUB_STATE_FILES = {
        commandSnapshot: 'docs/command_snapshot.json',
        directionRegistry: 'outputs/state/engine_direction_registry.json',
        decisionLog: 'outputs/state/engine_decision_log.jsonl',
        actionStatus: 'outputs/state/engine_action_status.json',
        lastApply: 'outputs/state/engine_last_apply_response.json',
        lastClarify: 'outputs/state/engine_last_clarify_response.json',
      };
      const EMBEDDED_PAYLOAD = __SNAPSHOT__;
      const ui = {
        payload: EMBEDDED_PAYLOAD,
        online: false,
        controlMode: 'snapshot',
        remoteState: null,
        activeDecisionId: '',
        askQuestion: '',
        selectedOptions: {},
        actionNote: '',
        actionWriteIn: '',
        actionMessage: 'Choose a decision, stage an option, and apply it from this panel.',
        aiResponse: null,
        pendingConfirmation: null,
        liveActionStatus: null,
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

      function isLocalHostname(hostname) {
        return ['127.0.0.1', 'localhost', '::1', '[::1]'].includes(String(hostname || '').toLowerCase());
      }

      function sameOriginControlUrl() {
        if ((window.location.protocol === 'http:' || window.location.protocol === 'https:') && isLocalHostname(window.location.hostname)) {
          return window.location.origin;
        }
        return '';
      }

      function discoverControlUrls() {
        const params = new URLSearchParams(window.location.search);
        const queryUrl = params.get('control_url') || '';
        const storedUrl = window.localStorage ? window.localStorage.getItem('atlas-control-url') : '';
        const allowStoredUrl = isLocalHostname(window.location.hostname) || String(storedUrl || '').startsWith('https://');
        const localCandidates = isLocalHostname(window.location.hostname) ? CONTROL_URL_CANDIDATES : [];
        return uniqueValues([queryUrl, allowStoredUrl ? storedUrl : '', sameOriginControlUrl()].concat(localCandidates));
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

      function deepClone(value) {
        return JSON.parse(JSON.stringify(value));
      }

      function normalizeText(value) {
        return String(value ?? '').trim();
      }

      function parseTimestamp(value) {
        const normalized = normalizeText(value);
        if (!normalized) return null;
        const parsed = Date.parse(normalized);
        return Number.isFinite(parsed) ? parsed : null;
      }

      function formatRelativeAge(value) {
        const parsed = parseTimestamp(value);
        if (!parsed) return 'not available';
        const diffMs = Math.max(0, Date.now() - parsed);
        const minutes = Math.floor(diffMs / 60000);
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes} min ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
        const days = Math.floor(hours / 24);
        return `${days} day${days === 1 ? '' : 's'} ago`;
      }

      function githubToken() {
        return window.localStorage ? (window.localStorage.getItem(GITHUB_TOKEN_KEY) || '').trim() : '';
      }

      function hasGitHubToken() {
        return Boolean(githubToken());
      }

      function storeGitHubToken(token) {
        if (!window.localStorage) return;
        window.localStorage.setItem(GITHUB_TOKEN_KEY, token.trim());
      }

      function clearGitHubToken() {
        if (!window.localStorage) return;
        window.localStorage.removeItem(GITHUB_TOKEN_KEY);
      }

      function githubHeaders(extraHeaders = {}) {
        const headers = {
          'Accept': 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
          ...extraHeaders,
        };
        const token = githubToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
      }

      async function githubApi(path, options = {}) {
        const response = await fetch(`${GITHUB_API_ROOT}${path}`, {
          cache: 'no-store',
          ...options,
          headers: githubHeaders(options.headers || {}),
        });
        if (!response.ok) {
          let message = `GitHub request failed (${response.status}).`;
          try {
            const payload = await response.json();
            message = payload.message || message;
          } catch (error) {
            // Keep the generic message.
          }
          throw new Error(message);
        }
        if (response.status === 204) {
          return null;
        }
        return response.json();
      }

      function decodeBase64Utf8(content) {
        const clean = String(content || '').replace(/\\n/g, '');
        const binary = atob(clean);
        const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
        return new TextDecoder().decode(bytes);
      }

      async function fetchGitHubFile(path, parser, fallbackValue) {
        try {
          const payload = await githubApi(`/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/contents/${path}?ref=${encodeURIComponent(GITHUB_REF)}`);
          return parser(decodeBase64Utf8(payload.content || ''));
        } catch (error) {
          if (/404/.test(String(error.message || '')) || /Not Found/i.test(String(error.message || ''))) {
            return fallbackValue;
          }
          throw error;
        }
      }

      async function fetchGitHubJson(path, fallbackValue = null) {
        return fetchGitHubFile(path, (textValue) => JSON.parse(textValue), fallbackValue);
      }

      async function fetchGitHubJsonl(path, fallbackValue = []) {
        return fetchGitHubFile(path, (textValue) => textValue.split(/\\n+/).map((line) => line.trim()).filter(Boolean).map((line) => JSON.parse(line)), fallbackValue);
      }

      async function dispatchGitHubWorkflow(workflowFile, inputs) {
        await githubApi(`/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/actions/workflows/${encodeURIComponent(workflowFile)}/dispatches`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ref: GITHUB_REF,
            inputs,
          }),
        });
      }

      function createRequestId(prefix) {
        return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      }

      function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
      }

      async function waitForGitHubResponse(path, requestId, timeoutMs = 120000) {
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
          const result = await fetchGitHubJson(path, null);
          if (result && result.request_id === requestId) {
            return result;
          }
          await sleep(4000);
        }
        throw new Error('GitHub control timed out while waiting for the response file. Check the Actions tab if this keeps happening.');
      }

      function overlayPayloadWithGitHubState(basePayload, remoteState) {
        const payload = deepClone(basePayload || EMBEDDED_PAYLOAD);
        const registry = remoteState.directionRegistry || {};
        const history = Array.isArray(remoteState.decisionHistory) ? remoteState.decisionHistory.slice().reverse().slice(0, 8) : [];
        const actionStatus = remoteState.actionStatus || null;
        payload.board_state = payload.board_state || {};
        if (registry.active_path_label) {
          payload.current_direction = {
            label: registry.active_path_label,
            reason: registry.active_direction_reason || payload.current_direction?.reason || '',
          };
        }
        if (!payload.goal_progress) {
          payload.goal_progress = {};
        }
        if (registry.current_manuscript_candidate?.title) {
          payload.goal_progress.current_manuscript_candidate = registry.current_manuscript_candidate;
        }
        if (registry.next_paper_opportunity?.title) {
          payload.goal_progress.next_paper_opportunity = registry.next_paper_opportunity;
        }
        if (history.length) {
          payload.decision_history = history;
        }
        if (!payload.control_state) {
          payload.control_state = {};
        }
        payload.control_state.preset_questions = payload.control_state.preset_questions || [
          'What have we discovered so far?',
          'Why is this recommended?',
          'What happens if I choose the second option?',
          'What paper story is emerging?',
        ];
        if (actionStatus) {
          payload.live_action_status = actionStatus;
          payload.control_state.live_action_status = actionStatus;
          payload.board_state.action_status_timestamp = actionStatus.timestamp || payload.board_state.action_status_timestamp || '';
        }
        if (registry.last_updated) {
          payload.board_state.steering_registry_last_updated = registry.last_updated;
        }
        if (registry.active_path_id) {
          payload.board_state.active_decision_id = registry.active_path_id;
          payload.board_state.active_decision_label = registry.active_path_label || payload.board_state.active_decision_label || '';
        }
        return payload;
      }

      async function loadGitHubRemoteState() {
        const [
          commandSnapshot,
          directionRegistry,
          decisionHistory,
          actionStatus,
          lastApplyResponse,
          lastClarifyResponse,
        ] = await Promise.all([
          fetchGitHubJson(GITHUB_STATE_FILES.commandSnapshot, {}),
          fetchGitHubJson(GITHUB_STATE_FILES.directionRegistry, {}),
          fetchGitHubJsonl(GITHUB_STATE_FILES.decisionLog, []),
          fetchGitHubJson(GITHUB_STATE_FILES.actionStatus, {}),
          fetchGitHubJson(GITHUB_STATE_FILES.lastApply, {}),
          fetchGitHubJson(GITHUB_STATE_FILES.lastClarify, {}),
        ]);
        return {
          commandSnapshot,
          directionRegistry,
          decisionHistory,
          actionStatus,
          lastApplyResponse,
          lastClarifyResponse,
        };
      }

      async function fetchGitHubCommandPage() {
        const remoteState = await loadGitHubRemoteState();
        const basePayload = remoteState.commandSnapshot?.primary_decision
          ? remoteState.commandSnapshot
          : (remoteState.lastApplyResponse?.payload?.primary_decision
            ? remoteState.lastApplyResponse.payload
            : EMBEDDED_PAYLOAD);
        ui.payload = overlayPayloadWithGitHubState(basePayload, remoteState);
        ui.online = true;
        ui.controlMode = 'github';
        ui.remoteState = remoteState;
        ui.liveActionStatus = remoteState.actionStatus || null;
        ui.actionMessage = computeBoardRuntimeState(ui.payload).mismatch
          ? 'GitHub control is connected, but the published board snapshot is behind the live steering state. Refresh or wait for publish before applying a choice.'
          : 'GitHub control is connected. Decisions and questions are dispatched through GitHub Actions.';
      }

      function decisionList(payload) {
        const primary = payload.primary_decision ? [payload.primary_decision] : [];
        const secondary = Array.isArray(payload.secondary_decisions) ? payload.secondary_decisions.slice(0, 2) : [];
        return primary.concat(secondary).filter((decision) => decision && decision.decision_id);
      }

      function decisionIdsForPayload(payload) {
        return decisionList(payload).map((decision) => normalizeText(decision.decision_id)).filter(Boolean);
      }

      function computeBoardRuntimeState(payload) {
        const boardState = deepClone(payload.board_state || {});
        const publishedSnapshot = ui.remoteState?.commandSnapshot?.primary_decision
          ? ui.remoteState.commandSnapshot
          : payload;
        const publishedBoardState = publishedSnapshot.board_state || {};
        const registry = ui.remoteState?.directionRegistry || {};
        const actionStatus = ui.remoteState?.actionStatus || payload.live_action_status || ui.liveActionStatus || {};
        const publishedVisibleIds = decisionIdsForPayload(publishedSnapshot);
        const visibleIds = decisionIdsForPayload(payload);
        const liveActiveId = normalizeText(registry.active_path_id || boardState.active_decision_id);
        const publishedDirectionLabel = normalizeText(publishedSnapshot.current_direction?.label);
        const liveDirectionLabel = normalizeText(registry.active_path_label || payload.current_direction?.label);
        const mismatchReasons = [];

        if (ui.controlMode === 'github') {
          if (publishedDirectionLabel && liveDirectionLabel && publishedDirectionLabel !== liveDirectionLabel) {
            mismatchReasons.push(`Published direction is ${publishedDirectionLabel}, but live steering says ${liveDirectionLabel}.`);
          }
          if (liveActiveId && !publishedVisibleIds.includes(liveActiveId)) {
            mismatchReasons.push('The published decision slate does not include the live active decision.');
          }
        }

        return Object.assign(boardState, {
          mode: ui.controlMode === 'local'
            ? 'local_control'
            : (ui.controlMode === 'github' ? 'github_overlay' : 'embedded_snapshot'),
          snapshot_generated_at: normalizeText(publishedBoardState.snapshot_generated_at || boardState.snapshot_generated_at),
          snapshot_age: formatRelativeAge(publishedBoardState.snapshot_generated_at || boardState.snapshot_generated_at),
          live_steering_last_updated: normalizeText(registry.last_updated || boardState.steering_registry_last_updated),
          live_steering_age: formatRelativeAge(registry.last_updated || boardState.steering_registry_last_updated),
          live_action_timestamp: normalizeText(actionStatus.timestamp || boardState.action_status_timestamp),
          live_action_age: formatRelativeAge(actionStatus.timestamp || boardState.action_status_timestamp),
          active_decision_id: liveActiveId,
          active_decision_in_visible_slate: liveActiveId ? visibleIds.includes(liveActiveId) : Boolean(boardState.active_decision_in_visible_slate),
          mismatch: mismatchReasons.length > 0,
          mismatch_reasons: mismatchReasons,
          actions_blocked: ui.controlMode === 'github' && mismatchReasons.length > 0,
        });
      }

      function actionsAvailable(payload = ui.payload) {
        if (!ui.online) return false;
        return !computeBoardRuntimeState(payload).actions_blocked;
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

      function freezeDecisionPacket(decision) {
        if (!decision || typeof decision !== 'object') return '';
        try {
          return JSON.stringify(decision);
        } catch (error) {
          return '';
        }
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
        const boardState = computeBoardRuntimeState(payload);
        const modeLabel = ui.controlMode === 'local'
          ? 'Local control'
          : (ui.controlMode === 'github' ? 'GitHub control' : 'Offline snapshot');
        const onlinePill = `<span class=\"pill ${ui.online ? 'online' : 'offline'}\">${escapeHtml(modeLabel)}</span>`;
        const statusLine = ui.controlMode === 'local'
          ? `Live control is connected at ${activeControlUrl}. Choices and questions post directly to the local command server.`
          : (ui.controlMode === 'github'
            ? (boardState.mismatch
              ? 'GitHub control is connected, but the published board snapshot does not fully match the live steering state yet.'
              : 'GitHub control is connected. This browser can dispatch decisions and clarifying questions through GitHub Actions.')
            : 'The cockpit is using its embedded fallback snapshot. You can review the page offline, but question and apply actions stay disabled until live control is back.');
        const mismatchBanner = boardState.mismatch ? `
          <div class=\"warning-banner\">
            <strong>Board mismatch detected</strong>
            <p>The published board is lagging the live steering state. Do not trust the visible slate for new actions until the mismatch clears.</p>
            <ul>
              ${boardState.mismatch_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join('')}
              <li>Hard refresh the page.</li>
              <li>Reconnect GitHub control if needed.</li>
              <li>Wait for the latest publish run to finish if a board-affecting workflow is still running.</li>
            </ul>
          </div>
        ` : '';
        const controlButtons = ui.controlMode === 'local'
          ? `<button class=\"button-inline primary\" id=\"refreshCommandButton\">Refresh live state</button>`
          : `
              <button class=\"button-inline primary\" id=\"refreshCommandButton\">Refresh live state</button>
              <button class=\"button-inline\" id=\"${hasGitHubToken() ? 'disconnectGitHubButton' : 'connectGitHubButton'}\">${hasGitHubToken() ? 'Disconnect GitHub control' : 'Connect GitHub control'}</button>
            `;
        const boardStatusDetails = `
          <details class=\"board-status-details\">
            <summary>Board status and control details</summary>
            <p class=\"muted-note\">${escapeHtml(statusLine)}</p>
            <p class=\"muted-note\">Published snapshot age: ${escapeHtml(boardState.snapshot_age)}</p>
            <p class=\"muted-note\">Live steering age: ${escapeHtml(boardState.live_steering_age)}</p>
            <p class=\"muted-note\">Latest action age: ${escapeHtml(boardState.live_action_age)}</p>
            <p class=\"muted-note\">Steering-aware automation: ${boardState.steering_aware_automation ? 'Yes' : 'No'}</p>
            <p class=\"muted-note\">${hasGitHubToken() ? 'GitHub control is stored in this browser for this page.' : 'To use the public page as a live command surface, connect a fine-grained GitHub token with Actions and Contents read/write.'}</p>
          </details>
        `;
        return `
          <div class=\"offline-banner\">Live control is offline. The cockpit is still usable as a read-only fallback snapshot, and all server actions stay disabled until /api/command-page responds again.</div>
          <section class=\"hero\">
            <div class=\"hero-main\">
              <p class=\"eyebrow\">Current Brief</p>
              <h1>Where the Project Stands</h1>
              <div class=\"status-strip\">${onlinePill}</div>
              <p class=\"hero-copy\">${escapeHtml(status.line || '')}</p>
              <p class=\"hero-note\">${escapeHtml(status.paragraph || '')}</p>
              ${mismatchBanner}
              <div class=\"mini-panel\">
                <span class=\"field-label\">Current direction</span>
                <strong>${escapeHtml(direction.label || 'Direction not emitted')}</strong>
                <p class=\"hero-note\">${escapeHtml(direction.reason || status.current_direction_line || '')}</p>
              </div>
              ${boardStatusDetails}
              <div class=\"hero-actions\">
                ${controlButtons}
              </div>
            </div>
            <div class=\"hero-side\">
              <div class=\"hero-meta mini-panel\">
                <span>Current paper path</span>
                <strong>${escapeHtml(manuscript.title || 'Not selected yet')}</strong>
                <p class=\"muted-note\">${escapeHtml(manuscript.story || '')}</p>
                <span style=\"margin-top:10px;\">Next paper opportunity</span>
                <strong>${escapeHtml(nextPaper.title || 'No secondary paper path emitted')}</strong>
                <p class=\"muted-note\" style=\"margin-top:10px;\">This is the paper lane the engine is carrying right now, plus the next plausible branch if you decide to pivot later.</p>
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
        const liveActionsEnabled = actionsAvailable(ui.payload);
        const selected = ui.selectedOptions[decision.decision_id] || '';
        const selectedOption = getSelectedOption(decision.decision_id);
        const visibleKnow = primary ? renderMetaList(decision.what_we_know) : '';
        const visibleUncertain = primary ? renderMetaList(decision.what_is_uncertain) : '';
        const workButtonLabel = selectedOption ? 'Go to apply panel' : 'Open apply panel';
        const stagedHint = selectedOption
          ? `<p class=\"muted-note\">${escapeHtml(selectedOption.label)} is staged. Apply it in the panel below.</p>`
          : '<p class=\"muted-note\">Choose an option, then jump to the apply panel.</p>';
        const options = (decision.options || []).map((option) => `
          <button
            class=\"option-button ${selected === option.id ? 'selected' : ''} ${decision.recommended_option_id === option.id ? 'recommended' : ''}\"
            data-role=\"stage-option\"
            data-decision-id=\"${escapeHtml(decision.decision_id)}\"
            data-option-id=\"${escapeHtml(option.id)}\"
            ${liveActionsEnabled ? '' : 'disabled'}>
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
              <button class=\"button-inline\" data-role=\"set-active-decision\" data-decision-id=\"${escapeHtml(decision.decision_id)}\">${workButtonLabel}</button>
              ${stagedHint}
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
            <details class=\"folded-panel\">
              <summary>Other decisions worth keeping nearby</summary>
              <div class=\"folded-body\">
                <p class=\"muted-note\">These may matter next, but they should not outrank the main choice.</p>
                <div class=\"secondary-grid\">${body}</div>
              </div>
            </details>
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
        const liveActionsEnabled = actionsAvailable(payload);
        const presets = (payload.control_state?.preset_questions || []).map((question) => `
          <button class=\"chip-button\" data-role=\"preset-question\" data-question=\"${escapeHtml(question)}\" ${liveActionsEnabled ? '' : 'disabled'}>${escapeHtml(question)}</button>
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
            <details class=\"folded-panel\">
              <summary>Ask for clarification before you commit</summary>
              <div class=\"folded-body\">
                <p class=\"muted-note\">Use this when you want the recommendation explained in plain English.</p>
                <div class=\"ask-grid\">
                  <div class=\"ask-panel\">
                    <div class=\"ask-toolbar\">${presets}</div>
                    <label class=\"field-label\" for=\"clarifyQuestion\">Question</label>
                    <textarea class=\"ask-input\" id=\"clarifyQuestion\" placeholder=\"Ask what the engine discovered, why a recommendation is leading, or what another option would change.\" ${liveActionsEnabled ? '' : 'disabled'}>${escapeHtml(ui.askQuestion)}</textarea>
                    <div class=\"action-buttons\">
                      <button class=\"action-button primary\" id=\"askAiButton\" ${liveActionsEnabled ? '' : 'disabled'}>Ask</button>
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
              </div>
            </details>
          </section>
        `;
      }

      function renderActionPanel(payload) {
        const active = getActiveDecision();
        const selected = active ? getSelectedOption(active.decision_id) : null;
        const pending = ui.pendingConfirmation;
        const liveAction = payload.live_action_status || ui.liveActionStatus || null;
        const liveActionsEnabled = actionsAvailable(payload);
        const boardState = computeBoardRuntimeState(payload);
        const selectedSummary = selected
          ? `<strong>${escapeHtml(selected.label)}</strong><p>${escapeHtml(optionDetail(selected))}</p>`
          : '<strong>No option staged yet</strong><p>Pick an option in one of the decision cards above to stage it here.</p>';
        const liveActionSummary = liveAction ? `
          <p class=\"muted-note\" style=\"margin-top:8px;\">Latest recorded action: ${escapeHtml(liveAction.message || liveAction.status || 'Action recorded.')}</p>
          ${liveAction.run?.url ? `<p class=\"muted-note\"><a class=\"button-link\" href=\"${escapeHtml(liveAction.run.url)}\" target=\"_blank\" rel=\"noreferrer\">Open related run</a></p>` : ''}
        ` : '';
        const blockNotice = boardState.actions_blocked ? `
          <div class=\"warning-banner\">
            <strong>Actions are paused for this board</strong>
            <p>GitHub control is available, but this published board snapshot is out of sync with live steering. Refresh the page or wait for the latest docs publish before applying new instructions.</p>
          </div>
        ` : '';
        const confirmationCard = pending ? `
          <div class=\"action-card\">
            <h3>Confirmation needed</h3>
            <p>${escapeHtml(pending.explanation || 'The cockpit needs you to confirm the interpreted instruction before it executes it.')}</p>
            <p class=\"muted-note\">${escapeHtml(pending.summary || '')}</p>
            <div class=\"action-buttons\">
              <button class=\"action-button primary\" id=\"confirmWriteInButton\" ${liveActionsEnabled ? '' : 'disabled'}>Confirm and apply</button>
              <button class=\"action-button\" id=\"cancelWriteInConfirmationButton\">Cancel</button>
            </div>
          </div>
        ` : '';
        return `
          <section class=\"panel\" id=\"applyPanel\">
            ${sectionHeader('Apply', 'Record Your Choice and Move the Engine', 'Choose an option above, then apply it here. The button on each decision card jumps straight to this panel.')}
            ${blockNotice}
            <div class=\"action-grid\">
              <div class=\"action-shell\">
                <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Working on:</strong> ${escapeHtml(active?.decision_title || 'No active decision')}.</p>
                <div class=\"action-card\">
                  <h3>Choice ready to apply</h3>
                  ${selectedSummary}
                </div>
                <label class=\"field-label\" for=\"actionNote\">Optional note</label>
                <input class=\"note-input\" id=\"actionNote\" type=\"text\" placeholder=\"Add a short note for the command log if helpful.\" ${liveActionsEnabled ? '' : 'disabled'} value=\"${escapeHtml(ui.actionNote)}\" />
                <div class=\"action-buttons\">
                  <button class=\"action-button primary\" id=\"applyOptionButton\" ${liveActionsEnabled && active && selected ? '' : 'disabled'}>Apply this choice</button>
                  <button class=\"action-button\" id=\"clearStagedOptionButton\">Clear</button>
                </div>
              </div>
              <div class=\"action-shell\">
                <label class=\"field-label\" for=\"writeInInstruction\">Or write your own instruction</label>
                <textarea class=\"write-in\" id=\"writeInInstruction\" placeholder=\"If none of the staged options fit, write the instruction in plain English here.\" ${liveActionsEnabled ? '' : 'disabled'}>${escapeHtml(ui.actionWriteIn)}</textarea>
                <div class=\"action-buttons\">
                  <button class=\"action-button\" id=\"applyWriteInButton\" ${liveActionsEnabled && active ? '' : 'disabled'}>Interpret and apply</button>
                </div>
                ${confirmationCard}
                <div class=\"action-card action-status\" id=\"actionStatus\">
                  <h3>Action status</h3>
                  <p>${escapeHtml(ui.actionMessage)}</p>
                  ${liveActionSummary}
                </div>
              </div>
            </div>
          </section>
        `;
      }

      function renderScoreRow(label, scorePayload) {
        const score = scorePayload?.score || 0;
        const max = scorePayload?.max || 4;
        const percent = scorePayload?.percent || 0;
        return `
          <div class=\"score-row\">
            <label><span>${escapeHtml(label)}</span><strong>${score} / ${max}</strong></label>
            <div class=\"score-track\"><div class=\"score-fill\" style=\"width:${percent}%\"></div></div>
          </div>
        `;
      }

      function manuscriptArtifactLink(packKey, label) {
        if (!packKey) return '';
        const href = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/tree/${GITHUB_REF}/outputs/manuscripts/${encodeURIComponent(packKey)}`;
        return `<a class=\"button-link\" href=\"${escapeHtml(href)}\" target=\"_blank\" rel=\"noreferrer\">${escapeHtml(label)}</a>`;
      }

      function manuscriptTaskSummary(candidate) {
        const summary = candidate.task_execution_summary || {};
        const counts = summary.status_counts || {};
        const parts = [];
        if (counts.running) parts.push(`${counts.running} running`);
        if (counts.blocked) parts.push(`${counts.blocked} blocked`);
        if (counts.satisfied) parts.push(`${counts.satisfied} satisfied`);
        if (!parts.length) parts.push('No executor activity yet');
        return parts.join(' · ');
      }

      function manuscriptTopIssue(candidate) {
        const tasks = candidate.task_ledger || [];
        const blocked = tasks.find((task) => task.critical && task.status === 'blocked');
        const running = tasks.find((task) => task.critical && task.status === 'running');
        const fallback = tasks.find((task) => task.status !== 'satisfied');
        const selected = blocked || running || fallback;
        if (!selected) return 'No active blocker is recorded right now.';
        return selected.execution_note || selected.rationale || selected.label || 'A blocker is still being worked.';
      }

      function manuscriptJournalStatus(candidate) {
        return candidate.journal_targets?.requirements_checked ? 'Verified requirements' : 'Shortlist only';
      }

      function renderManuscriptCard(candidate, primaryLane = false) {
        if (!candidate) return '';
        const primaryJournal = candidate.journal_targets?.primary?.journal?.name || 'Primary journal not selected yet';
        const backupJournals = (candidate.journal_targets?.backups || []).map((item) => item.journal?.name).filter(Boolean);
        return `
          <article class=\"manuscript-card ${primaryLane ? 'primary-lane' : ''}\">
            <div class=\"manuscript-head\">
              <div class=\"manuscript-title\">
                <strong>${escapeHtml(candidate.title || 'Manuscript candidate')}</strong>
                <p class=\"muted-note\">${escapeHtml(candidate.manuscript_gate_state || 'not ready')}</p>
              </div>
              <div class=\"status-strip\">
                <span class=\"pill ${slugToken(candidate.support_status)}\">${escapeHtml(candidate.support_status || 'not specified')}</span>
                <span class=\"pill ${slugToken((candidate.publication_status || 'candidate').replace(/\\s+/g, '-'))}\">${escapeHtml(candidate.publication_status || 'candidate')}</span>
                <span class=\"pill ${candidate.journal_targets?.requirements_checked ? 'supported' : 'bounded'}\">${escapeHtml(manuscriptJournalStatus(candidate))}</span>
              </div>
            </div>
            <div class=\"score-stack\">
              ${renderScoreRow('Scientific strength', candidate.scientific_strength_bar)}
              ${renderScoreRow('Journal fit', candidate.journal_fit_bar)}
              ${renderScoreRow('Draft readiness', candidate.draft_readiness_bar)}
            </div>
            <div class=\"manuscript-alert\">
              <p><strong>Task summary:</strong> ${escapeHtml(manuscriptTaskSummary(candidate))}</p>
              <p><strong>Top blocker:</strong> ${escapeHtml(manuscriptTopIssue(candidate))}</p>
            </div>
            <div class=\"manuscript-meta-list\">
              <p><strong style=\"color:var(--ink);\">Primary journal:</strong> ${escapeHtml(primaryJournal)}</p>
              <p><strong style=\"color:var(--ink);\">Backups:</strong> ${escapeHtml(backupJournals.length ? backupJournals.join(', ') : 'Still ranking')}</p>
              <p><strong style=\"color:var(--ink);\">Draft status:</strong> ${escapeHtml(candidate.draft_status || 'not started')}</p>
              <p><strong style=\"color:var(--ink);\">Review memo:</strong> ${escapeHtml(candidate.review_memo_status || 'not available')}</p>
              <p><strong style=\"color:var(--ink);\">Last pack refresh:</strong> ${escapeHtml(candidate.last_pack_refresh || 'Not recorded')}</p>
            </div>
            ${manuscriptArtifactLink(candidate.pack_key, 'Open manuscript pack')}
          </article>
        `;
      }

      function renderWatchlistItem(candidate) {
        return `
          <article class=\"watchlist-item\">
            <strong>${escapeHtml(candidate.title || 'Watchlist candidate')}</strong>
            <p class=\"muted-note\">${escapeHtml(candidate.manuscript_gate_state || 'not ready')}</p>
            <div class=\"score-stack\">
              ${renderScoreRow('Scientific strength', candidate.scientific_strength_bar)}
              ${renderScoreRow('Journal fit', candidate.journal_fit_bar)}
              ${renderScoreRow('Draft readiness', candidate.draft_readiness_bar)}
            </div>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Primary journal:</strong> ${escapeHtml(candidate.journal_targets?.primary?.journal?.name || 'Still ranking')}</p>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Journal state:</strong> ${escapeHtml(manuscriptJournalStatus(candidate))}</p>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Task summary:</strong> ${escapeHtml(manuscriptTaskSummary(candidate))}</p>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Top blocker:</strong> ${escapeHtml(manuscriptTopIssue(candidate))}</p>
          </article>
        `;
      }

      function renderPublicationTrackerItem(entry) {
        return `
          <article class=\"tracker-item\">
            <strong>${escapeHtml(entry.title || 'Tracked manuscript')}</strong>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Status:</strong> ${escapeHtml(entry.status || 'not set')}</p>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Journal:</strong> ${escapeHtml(entry.journal_name || 'Not recorded')}</p>
            <p class=\"muted-note\"><strong style=\"color:var(--ink);\">Updated:</strong> ${escapeHtml(entry.updated_at || 'Not recorded')}</p>
            <p class=\"muted-note\">${escapeHtml(entry.note || '')}</p>
          </article>
        `;
      }

      function renderManuscriptQueue(payload) {
        const queue = payload.manuscript_queue || {};
        const active = queue.active_candidates || [];
        const watchlist = queue.watchlist || [];
        const tracker = queue.publication_tracker || [];
        const activeCards = active.length
          ? active.map((candidate, index) => renderManuscriptCard(candidate, index === 0)).join('')
          : '<div class=\"manuscript-card\"><p class=\"empty-note\">No manuscript lanes are active yet.</p></div>';
        const watchlistCards = watchlist.length
          ? watchlist.map((candidate) => renderWatchlistItem(candidate)).join('')
          : '<div class=\"watchlist-item\"><p class=\"empty-note\">No watchlist candidates are waiting behind the active manuscript lanes.</p></div>';
        const trackerCards = tracker.length
          ? tracker.map((entry) => renderPublicationTrackerItem(entry)).join('')
          : '<div class=\"tracker-item\"><p class=\"empty-note\">No manuscripts have been moved into the publication tracker yet.</p></div>';
        return `
          <section class=\"panel\">
            ${sectionHeader('Manuscripts', 'Manuscript Queue', 'These are the paper outputs the engine is actively building, plus the next candidates waiting behind them.')}
            <div class=\"manuscript-grid\">${activeCards}</div>
            <details class=\"folded-panel\" style=\"margin-top:14px;\" open>
              <summary>Watchlist</summary>
              <div class=\"folded-body watchlist-shell\">${watchlistCards}</div>
            </details>
            <details class=\"folded-panel\" style=\"margin-top:14px;\">
              <summary>Publication Tracker</summary>
              <div class=\"folded-body tracker-shell\">${trackerCards}</div>
            </details>
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
          renderPrimaryDecision(ui.payload),
          renderActionPanel(ui.payload),
          renderManuscriptQueue(ui.payload),
          renderProgress(ui.payload),
          renderDiscovery(ui.payload),
          renderSecondaryDecisions(ui.payload),
          renderAskAi(ui.payload),
          renderTimelineHistory(ui.payload),
          renderSupportLinks(ui.payload),
        ].join('');
        installHandlers();
      }

      function highlightApplyPanel() {
        const panel = document.getElementById('applyPanel');
        if (!panel) return;
        panel.classList.remove('panel-attention');
        panel.classList.add('panel-attention');
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        const applyButton = document.getElementById('applyOptionButton');
        const noteInput = document.getElementById('actionNote');
        const focusTarget = applyButton && !applyButton.disabled ? applyButton : noteInput;
        if (focusTarget) {
          window.setTimeout(() => {
            try {
              focusTarget.focus({ preventScroll: true });
            } catch (error) {
              focusTarget.focus();
            }
          }, 220);
        }
        window.setTimeout(() => panel.classList.remove('panel-attention'), 1600);
      }

      async function fetchCommandPage() {
        try {
          const result = await fetchControlJson(COMMAND_PAGE_ENDPOINT, { headers: { 'Accept': 'application/json' } });
          ui.payload = result.payload || EMBEDDED_PAYLOAD;
          ui.online = true;
          ui.controlMode = 'local';
          ui.remoteState = null;
          ui.liveActionStatus = ui.payload.live_action_status || null;
          ui.actionMessage = `Live control is connected at ${activeControlUrl}. Stage a choice above or ask the AI for clarification.`;
        } catch (error) {
          if (hasGitHubToken()) {
            try {
              await fetchGitHubCommandPage();
            } catch (githubError) {
              ui.payload = EMBEDDED_PAYLOAD;
              ui.online = false;
              ui.controlMode = 'snapshot';
              ui.remoteState = null;
              ui.liveActionStatus = null;
              ui.actionMessage = githubError.message || 'GitHub control is unavailable. Review the embedded fallback snapshot until live control comes back.';
            }
          } else {
            ui.payload = EMBEDDED_PAYLOAD;
            ui.online = false;
            ui.controlMode = 'snapshot';
            ui.remoteState = null;
            ui.liveActionStatus = null;
            ui.actionMessage = 'Live control is offline. Review the embedded fallback snapshot until /api/command-page comes back, or connect GitHub control from this page.';
          }
        }
        renderApp();
      }

      function setActiveDecision(decisionId, revealApplyPanel = false) {
        if (!decisionId) return;
        ui.activeDecisionId = decisionId;
        const decision = getDecision(decisionId);
        const selectedOption = decision ? getSelectedOption(decisionId) : null;
        ui.actionMessage = selectedOption
          ? `Ready to apply “${selectedOption.label}” for ${decision?.decision_title || 'the active decision'}.`
          : `Now working on ${decision?.decision_title || 'the active decision'}. Choose an option, then apply it in the panel below.`;
        renderApp();
        if (revealApplyPanel) {
          window.requestAnimationFrame(() => highlightApplyPanel());
        }
      }

      function ensureGitHubApplyResult(result) {
        if (result && result.ok === false) {
          throw new Error(result.error_message || result.error || 'GitHub control could not apply the decision.');
        }
        return result;
      }

      async function syncGitHubPayload(preferredPayload = null) {
        const remoteState = await loadGitHubRemoteState();
        const basePayload = preferredPayload
          || (remoteState.commandSnapshot?.primary_decision ? remoteState.commandSnapshot : null)
          || remoteState.lastApplyResponse?.payload
          || EMBEDDED_PAYLOAD;
        ui.payload = overlayPayloadWithGitHubState(basePayload, remoteState);
        ui.remoteState = remoteState;
        ui.liveActionStatus = remoteState.actionStatus || null;
        return remoteState;
      }

      async function askAi(question) {
        if (!actionsAvailable(ui.payload) || !question.trim()) return;
        ui.aiResponse = {
          answer: 'Thinking through the current repo state…',
          evidence_chain: ['The cockpit is waiting for /api/clarify-question.'],
          implication: 'This answer will be attached to the current decision focus.',
          recommended_follow_up: 'If the answer changes your confidence, move to the action panel.',
        };
        renderApp();
        if (ui.controlMode === 'github') {
          try {
            const requestId = createRequestId('clarify');
            await dispatchGitHubWorkflow(GITHUB_CLARIFY_WORKFLOW, {
              request_id: requestId,
              decision_id: ui.activeDecisionId || '',
              question,
            });
            const result = await waitForGitHubResponse(GITHUB_STATE_FILES.lastClarify, requestId);
            ui.aiResponse = result;
            await syncGitHubPayload();
          } catch (error) {
            ui.aiResponse = {
              answer: error.message || 'The question could not be answered.',
              evidence_chain: ['GitHub control could not complete the clarify workflow.'],
              implication: 'The decision state has not changed.',
              recommended_follow_up: 'Open GitHub control again or try the question once the workflow lane is healthy.',
            };
          }
          renderApp();
          return;
        }
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
        if (!actionsAvailable(ui.payload) || !decision || !option) return;
        ui.actionMessage = 'Applying the staged option…';
        ui.pendingConfirmation = null;
        renderApp();
        if (ui.controlMode === 'github') {
          try {
            const requestId = createRequestId('apply');
            await dispatchGitHubWorkflow(GITHUB_APPLY_WORKFLOW, {
              request_id: requestId,
              decision_id: decision.decision_id,
              decision_json: freezeDecisionPacket(decision),
              option_id: option.id,
              note: ui.actionNote || '',
              free_text: '',
              confirmed: 'false',
            });
            const result = ensureGitHubApplyResult(await waitForGitHubResponse(GITHUB_STATE_FILES.lastApply, requestId));
            const remoteState = await syncGitHubPayload(result.payload || null);
            ui.actionNote = '';
            ui.actionWriteIn = '';
            ui.aiResponse = null;
            ui.pendingConfirmation = null;
            ui.liveActionStatus = remoteState.actionStatus || result.triggered_action || null;
            ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The decision was applied through GitHub control.';
          } catch (error) {
            ui.actionMessage = error.message || 'The decision could not be applied.';
          }
          renderApp();
          return;
        }
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
        if (!actionsAvailable(ui.payload) || !decision || !ui.actionWriteIn.trim()) return;
        ui.actionMessage = 'Interpreting your instruction…';
        ui.pendingConfirmation = null;
        renderApp();
        if (ui.controlMode === 'github') {
          try {
            const requestId = createRequestId('apply');
            await dispatchGitHubWorkflow(GITHUB_APPLY_WORKFLOW, {
              request_id: requestId,
              decision_id: decision.decision_id,
              decision_json: freezeDecisionPacket(decision),
              option_id: '',
              free_text: ui.actionWriteIn,
              note: ui.actionNote || '',
              confirmed: 'false',
            });
            const result = ensureGitHubApplyResult(await waitForGitHubResponse(GITHUB_STATE_FILES.lastApply, requestId));
            if (result.needs_confirmation) {
              const proposed = result.interpreted_decision?.matched_option_id;
              if (proposed) {
                ui.selectedOptions[decision.decision_id] = proposed;
              }
              ui.pendingConfirmation = {
                decisionId: decision.decision_id,
                decisionJson: freezeDecisionPacket(decision),
                freeText: ui.actionWriteIn,
                note: ui.actionNote,
                explanation: result.interpreted_decision?.explanation || 'The write-in instruction needs confirmation.',
                summary: proposed ? `The cockpit thinks you mean: ${proposed}.` : 'The cockpit could not map your instruction cleanly enough to act without confirmation.',
              };
              ui.actionMessage = result.interpreted_decision?.explanation || 'The write-in instruction needs confirmation.';
              renderApp();
              return;
            }
            const remoteState = await syncGitHubPayload(result.payload || null);
            ui.actionNote = '';
            ui.actionWriteIn = '';
            ui.aiResponse = null;
            ui.pendingConfirmation = null;
            ui.liveActionStatus = remoteState.actionStatus || result.triggered_action || null;
            ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The instruction was applied through GitHub control.';
          } catch (error) {
            ui.actionMessage = error.message || 'The instruction could not be applied.';
          }
          renderApp();
          return;
        }
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
        if (!actionsAvailable(ui.payload) || !pending) return;
        ui.actionMessage = 'Applying the confirmed interpretation…';
        renderApp();
        if (ui.controlMode === 'github') {
          try {
            const requestId = createRequestId('apply');
            await dispatchGitHubWorkflow(GITHUB_APPLY_WORKFLOW, {
              request_id: requestId,
              decision_id: pending.decisionId,
              decision_json: pending.decisionJson || '',
              option_id: '',
              free_text: pending.freeText,
              note: pending.note || '',
              confirmed: 'true',
            });
            const result = ensureGitHubApplyResult(await waitForGitHubResponse(GITHUB_STATE_FILES.lastApply, requestId));
            const remoteState = await syncGitHubPayload(result.payload || null);
            ui.actionNote = '';
            ui.actionWriteIn = '';
            ui.aiResponse = null;
            ui.pendingConfirmation = null;
            ui.liveActionStatus = remoteState.actionStatus || result.triggered_action || null;
            ui.actionMessage = (result.triggered_action && result.triggered_action.message) || 'The confirmed instruction was applied through GitHub control.';
          } catch (error) {
            ui.actionMessage = error.message || 'The confirmed instruction could not be applied.';
          }
          renderApp();
          return;
        }
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

        const connectGitHubButton = document.getElementById('connectGitHubButton');
        if (connectGitHubButton) {
          connectGitHubButton.addEventListener('click', async () => {
            const token = window.prompt('Paste a fine-grained GitHub token with Actions and Contents read/write access for matthewdholtkamp/testfile.');
            if (!token || !token.trim()) return;
            storeGitHubToken(token.trim());
            ui.actionMessage = 'GitHub control token saved in this browser. Refreshing live state…';
            renderApp();
            await fetchCommandPage();
          });
        }

        const disconnectGitHubButton = document.getElementById('disconnectGitHubButton');
        if (disconnectGitHubButton) {
          disconnectGitHubButton.addEventListener('click', async () => {
            clearGitHubToken();
            ui.actionMessage = 'GitHub control has been disconnected in this browser.';
            await fetchCommandPage();
          });
        }

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
          button.addEventListener('click', () => setActiveDecision(button.dataset.decisionId, true));
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
    parser.add_argument('--snapshot-path', default='docs/command_snapshot.json', help='Tracked command payload snapshot output path.')
    args = parser.parse_args()

    state = load_project_state()
    materialize_manuscript_outputs(
        state,
        direction_registry=load_direction_registry(),
        publication_tracker=load_publication_tracker(),
        journal_registry=load_journal_registry(),
    )
    snapshot = build_command_page_payload(state, root_prefix='./', control_online=False)
    html = render_html(snapshot)
    write_text(os.path.join(REPO_ROOT, args.output_path), html)
    write_text(os.path.join(REPO_ROOT, args.snapshot_path), json.dumps(snapshot, indent=2) + '\n')
    print(f'Phase 7 command cockpit written: {os.path.join(REPO_ROOT, args.output_path)}')


if __name__ == '__main__':
    main()
