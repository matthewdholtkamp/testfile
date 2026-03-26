(function () {
  const data = window.ATLAS_VIEWER_DATA;
  if (!data) {
    document.body.innerHTML = "<pre>Atlas viewer data was not found.</pre>";
    return;
  }

  const DETAIL_TABS = [
    { id: "overview", label: "Overview" },
    { id: "evidence", label: "Anchor Evidence" },
    { id: "translational", label: "Translational" },
    { id: "gaps", label: "Gaps + Queue" },
  ];

  const state = {
    selectedMechanism:
      data.mechanisms.find((item) => item.display_name === data.summary.lead_mechanism)?.id ||
      data.mechanisms[0]?.id,
    selectedDetailTab: "overview",
    evidenceSearch: "",
    evidenceConfidence: "all",
    evidencePromotion: "all",
    evidenceLayer: "all",
    sidebarSearch: "",
    expandedLedgerKey: null,
    showAllWorkpack: false,
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function clear(node) {
    node.innerHTML = "";
  }

  function normalize(value) {
    return (value || "").toString().trim();
  }

  function titleCase(value) {
    return normalize(value)
      .replace(/_/g, " ")
      .replace(/\b\w/g, (match) => match.toUpperCase());
  }

  function sentenceCase(value) {
    const normalized = normalize(value);
    if (!normalized) return "—";
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }

  function safeNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatPromo(value) {
    return sentenceCase(normalize(value).replace(/_/g, " "));
  }

  function mechanismById(id) {
    return data.mechanisms.find((item) => item.id === id);
  }

  function mechanismLedgerRows(id) {
    const mechanism = mechanismById(id);
    return data.ledger.filter((row) => row.mechanism_display_name === mechanism.display_name);
  }

  function mechanismBridgeRows(id) {
    const mechanism = mechanismById(id);
    return data.bridge_rows.filter((row) => row.canonical_mechanism === mechanism.canonical_mechanism);
  }

  function mechanismChain(id) {
    const mechanism = mechanismById(id);
    return data.causal_chains[mechanism.canonical_mechanism] || null;
  }

  function mechanismIdeas(id) {
    const mechanism = mechanismById(id);
    return data.hypothesis_candidates.by_mechanism[mechanism.canonical_mechanism] || [];
  }

  function mechanismIdeaGate(id) {
    const mechanism = mechanismById(id);
    return (data.idea_gate.rows || []).find((row) => row.canonical_mechanism === mechanism.canonical_mechanism) || null;
  }

  function ledgerKey(row) {
    return [row.mechanism_display_name, row.atlas_layer, row.best_anchor_pmid, row.proposed_narrative_claim].join("|");
  }

  function parseCounts(value) {
    if (Array.isArray(value)) return value;
    return normalize(value)
      .split(";")
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => {
        const [label, count] = entry.split(":");
        return { label: normalize(label), count: safeNumber(count) };
      });
  }

  function parsePmids(value) {
    return normalize(value)
      .split(";")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function pubmedLink(pmid) {
    return `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;
  }

  function repoPathHref(path) {
    const normalized = normalize(path).replace(/\\/g, "/");
    return normalized ? `../../${normalized}` : "";
  }

  function repoBlobLink(path) {
    const normalized = normalize(path).replace(/\\/g, "/");
    const base = data.metadata?.repo?.blob_base_url || "";
    return normalized && base ? `${base}/${normalized}` : "";
  }

  function preferredHref(path, explicitHref) {
    const repoHref = repoPathHref(path);
    if (window.location.protocol === "file:" && repoHref) return repoHref;
    return explicitHref || repoBlobLink(path) || repoHref;
  }

  function resolveActionHref(href) {
    const normalized = normalize(href);
    if (!normalized) return "";
    if (normalized.startsWith("http") || normalized.startsWith("#")) return normalized;
    if (window.location.protocol === "file:") return normalized;
    const repoPath = normalized.replace(/^\.\.\/\.\.\//, "");
    return repoBlobLink(repoPath) || normalized;
  }

  function releaseTone(value) {
    const normalized = normalize(value);
    if (["near_ready", "core_atlas_candidate", "ready_to_write", "core_atlas", "promote_now", "canonical_demo_ready"].includes(normalized)) return "stable";
    if (["write_with_caution", "review_track", "provisional", "bounded_demo_ready", "supporting_section"].includes(normalized)) return "provisional";
    return "hold";
  }

  function releaseRowForMechanism(mechanism) {
    return (data.release_manifest?.rows || []).find((row) => row.canonical_mechanism === mechanism.canonical_mechanism) || null;
  }

  function makeActionLink(label, href, variant = "primary") {
    if (!href) return null;
    const link = el("a", `action-button ${variant === "secondary" ? "secondary" : ""}`, label);
    link.href = href;
    if (!href.startsWith("#")) {
      link.target = "_blank";
      link.rel = "noreferrer";
    }
    return link;
  }

  function makeCopyButton(label, text) {
    if (!normalize(text)) return null;
    const button = el("button", "action-button secondary", label);
    button.type = "button";
    button.addEventListener("click", async () => {
      const fallback = () => {
        const area = document.createElement("textarea");
        area.value = text;
        document.body.append(area);
        area.select();
        document.execCommand("copy");
        area.remove();
      };
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          fallback();
        }
        button.textContent = "Copied";
      } catch (error) {
        fallback();
        button.textContent = "Copied";
      }
      setTimeout(() => {
        button.textContent = label;
      }, 1400);
    });
    return button;
  }

  function actionRow(items) {
    const row = el("div", "action-row");
    items.filter(Boolean).forEach((item) => row.append(item));
    return row;
  }

  function metadataTimestamp() {
    const allPaths = Object.values(data.metadata.generated_from || {});
    const match = allPaths
      .map((path) => normalize(path).match(/(\d{4}-\d{2}-\d{2})_(\d{6})/))
      .find(Boolean);
    if (!match) return "Latest curated atlas snapshot";
    const [, day, time] = match;
    return `${day} ${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`;
  }

  function mechanismDerivedStats(mechanism) {
    const rows = mechanismLedgerRows(mechanism.id);
    const stable = rows.filter((row) => row.confidence_bucket === "stable").length;
    const provisional = rows.filter((row) => row.confidence_bucket === "provisional").length;
    const blocked = rows.filter((row) => normalize(row.promotion_note) !== "ready to write").length;
    return { stable, provisional, blocked, total: rows.length };
  }

  function createEmptyState(message) {
    const card = el("div", "empty-state");
    card.append(el("div", "muted", message));
    return card;
  }

  function pmidChips(value) {
    const pmids = parsePmids(value);
    if (!pmids.length) {
      return el("span", "muted", "—");
    }
    const wrap = el("div", "chip-row");
    pmids.forEach((pmid) => {
      const link = el("a", "chip-link", pmid);
      link.href = pubmedLink(pmid);
      link.target = "_blank";
      link.rel = "noreferrer";
      wrap.append(link);
    });
    return wrap;
  }

  function strengthPill(tag) {
    return el("span", `strength-pill ${normalize(tag) || "speculative"}`, titleCase(tag || "speculative"));
  }

  function statusPill(value) {
    return el("span", `status-pill ${normalize(value)}`, formatPromo(value));
  }

  function renderMarkdownLite(root, text) {
    clear(root);
    const lines = text.split(/\r?\n/);
    let currentList = null;

    function closeList() {
      currentList = null;
    }

    lines.forEach((rawLine) => {
      const line = rawLine.trimEnd();
      const trimmed = line.trim();
      if (!trimmed) {
        closeList();
        return;
      }
      if (trimmed.startsWith("# ")) {
        closeList();
        root.append(el("h3", "markdown-h1", trimmed.replace(/^#\s+/, "")));
        return;
      }
      if (trimmed.startsWith("## ")) {
        closeList();
        root.append(el("h4", "markdown-h2", trimmed.replace(/^##\s+/, "")));
        return;
      }
      if (trimmed.startsWith("### ")) {
        closeList();
        root.append(el("h5", "markdown-h3", trimmed.replace(/^###\s+/, "")));
        return;
      }
      if (trimmed.startsWith("- ")) {
        if (!currentList || currentList.tagName !== "UL") {
          currentList = el("ul", "markdown-list");
          root.append(currentList);
        }
        currentList.append(el("li", "", trimmed.slice(2)));
        return;
      }
      if (/^\d+\.\s+/.test(trimmed)) {
        if (!currentList || currentList.tagName !== "OL") {
          currentList = el("ol", "markdown-list ordered");
          root.append(currentList);
        }
        currentList.append(el("li", "", trimmed.replace(/^\d+\.\s+/, "")));
        return;
      }
      closeList();
      root.append(el("p", "markdown-paragraph", trimmed));
    });
  }

  function renderStatGrid(stats) {
    const grid = el("div", "mechanism-meta");
    stats.forEach(([label, value]) => {
      const block = el("div", "meta-block");
      block.append(el("div", "meta-label", label));
      block.append(el("div", "meta-value", String(value)));
      grid.append(block);
    });
    return grid;
  }

  function renderRichList(title, items, emptyMessage) {
    const section = el("div", "detail-section");
    section.append(el("h3", "", title));
    if (!items || !items.length) {
      section.append(createEmptyState(emptyMessage));
      return section;
    }
    const wrap = el("div", "tag-cloud");
    items.forEach((item) => wrap.append(el("span", "micro-pill", item)));
    section.append(wrap);
    return section;
  }

  function renderAnchorTable(rows) {
    if (!rows.length) return createEmptyState("No anchor papers are available for this mechanism yet.");
    const wrap = el("div", "table-wrap");
    const table = document.createElement("table");
    table.innerHTML = `
      <thead>
        <tr>
          <th>PMID</th>
          <th>Source Quality</th>
          <th>Bucket</th>
          <th>Avg Depth</th>
          <th>Example Claim</th>
        </tr>
      </thead>
    `;
    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const pmidTd = document.createElement("td");
      pmidTd.append(pmidChips(row.PMID));
      tr.append(pmidTd);
      [row["Source Quality"], row["Quality Bucket"], row["Avg Depth"], row["Example Claim"]].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value || "—";
        tr.append(td);
      });
      tbody.append(tr);
    });
    table.append(tbody);
    wrap.append(table);
    return wrap;
  }

  function renderLayerTable(rows) {
    if (!rows.length) return createEmptyState("No atlas-layer rows are available for this mechanism yet.");
    const wrap = el("div", "table-wrap");
    const table = document.createElement("table");
    table.innerHTML = `
      <thead>
        <tr>
          <th>Atlas Layer</th>
          <th>Papers</th>
          <th>Full-text-like</th>
          <th>Abstract-only</th>
          <th>Avg Depth</th>
          <th>Anchor PMIDs</th>
        </tr>
      </thead>
    `;
    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      [row["Atlas Layer"], row.Papers, row["Full-text-like"], row["Abstract-only"], row["Avg Depth"]].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value || "—";
        tr.append(td);
      });
      const pmidTd = document.createElement("td");
      pmidTd.append(pmidChips(row["Anchor PMIDs"]));
      tr.append(pmidTd);
      tbody.append(tr);
    });
    table.append(tbody);
    wrap.append(table);
    return wrap;
  }

  function fillSelect(selectId, values, selected) {
    const select = document.getElementById(selectId);
    const current = selected || "all";
    clear(select);
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All";
    select.append(allOption);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = formatPromo(value);
      select.append(option);
    });
    select.value = values.includes(current) || current === "all" ? current : "all";
  }

  function filteredLedgerRows() {
    const query = state.evidenceSearch.toLowerCase();
    return mechanismLedgerRows(state.selectedMechanism).filter((row) => {
      const haystack = [
        row.atlas_layer,
        row.proposed_narrative_claim,
        row.best_anchor_claim_text,
        row.best_anchor_pmid,
        row.supporting_pmids,
        row.source_quality_mix,
        row.promotion_note,
        row.action_blockers,
        row.contradiction_signal,
      ].join(" ").toLowerCase();
      if (query && !haystack.includes(query)) return false;
      if (state.evidenceConfidence !== "all" && row.confidence_bucket !== state.evidenceConfidence) return false;
      if (state.evidencePromotion !== "all" && row.promotion_note !== state.evidencePromotion) return false;
      if (state.evidenceLayer !== "all" && row.atlas_layer !== state.evidenceLayer) return false;
      return true;
    });
  }

  function renderSummary() {
    document.getElementById("leadMechanism").textContent = data.summary.lead_mechanism;
    document.getElementById("leadHint").textContent = data.summary.top_priority
      ? `Next manual priority: ${data.summary.top_priority}`
      : "Starter atlas synthesis";
    document.getElementById("heroSummary").textContent =
      `${data.summary.lead_mechanism} is the current lead chapter. ` +
      `${data.summary.stable_rows} ledger rows are stable, ${data.summary.provisional_rows} are provisional, and ${data.summary.blocked_rows} rows still need cleanup before they are fully writing-grade.`;
    document.getElementById("freshnessNote").textContent = metadataTimestamp();

    const sidebarQuery = state.sidebarSearch.trim();
    document.getElementById("sidebarFocusSummary").textContent = sidebarQuery
      ? `Filtering evidence review for “${sidebarQuery}”.`
      : "Use search to jump straight to a claim, PMID, or target seed.";

    const summaryCards = [
      ["Lead Mechanism", data.summary.lead_mechanism],
      ["Stable Ledger Rows", String(data.summary.stable_rows)],
      ["Idea-Ready Mechanisms", String(data.summary.idea_ready_now || 0)],
      ["Breakthrough-Ready Mechanisms", String(data.summary.breakthrough_ready_now || 0)],
      ["Blocked Rows", String(data.summary.blocked_rows)],
    ];

    const summaryRoot = document.getElementById("summaryCards");
    clear(summaryRoot);
    summaryCards.forEach(([label, value]) => {
      const card = el("div", "card");
      card.append(el("div", "summary-card-value", value));
      card.append(el("div", "summary-card-label", label));
      summaryRoot.append(card);
    });

    const nav = document.getElementById("mechanismNav");
    clear(nav);
    data.mechanisms.forEach((mechanism) => {
      const stats = mechanismDerivedStats(mechanism);
      const button = el("button", state.selectedMechanism === mechanism.id ? "is-active" : "");
      button.type = "button";
      button.append(el("div", "nav-title", mechanism.display_name));
      button.append(el("div", "muted nav-subtitle", `${formatPromo(mechanism.promotion_status)} · ${stats.stable} stable · ${stats.blocked} blocked`));
      button.addEventListener("click", () => setMechanism(mechanism.id, "deep-dive"));
      nav.append(button);
    });

    const mechanismCards = document.getElementById("mechanismCards");
    clear(mechanismCards);
    data.mechanisms.forEach((mechanism) => {
      const stats = mechanismDerivedStats(mechanism);
      const ideaRow = mechanismIdeaGate(mechanism.id);
      const releaseRow = releaseRowForMechanism(mechanism);
      const card = el("button", "card mechanism-card-button");
      card.type = "button";
      card.addEventListener("click", () => setMechanism(mechanism.id, "deep-dive"));

      const header = el("div", "mechanism-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", mechanism.display_name));
      titleBlock.append(el("div", "muted", `${mechanism.queue_burden} open queue items · ${mechanism.papers} papers`));
      const pillWrap = el("div", "tag-cloud");
      pillWrap.append(statusPill(mechanism.promotion_status));
      if (releaseRow?.gate_status) pillWrap.append(el("span", `micro-pill ${releaseTone(releaseRow.gate_status)}`, `Gate ${formatPromo(releaseRow.gate_status)}`));
      if (releaseRow?.release_bucket) pillWrap.append(el("span", `micro-pill ${releaseTone(releaseRow.release_bucket)}`, `Release ${formatPromo(releaseRow.release_bucket)}`));
      if (ideaRow) pillWrap.append(el("span", `micro-pill ${normalize(ideaRow.idea_generation_status) === 'ready_now' ? 'stable' : 'provisional'}`, `Idea ${formatPromo(ideaRow.idea_generation_status)}`));
      header.append(titleBlock, pillWrap);
      card.append(header);

      const readiness = el("div", "readiness-strip");
      [["stable", stats.stable], ["provisional", stats.provisional], ["blocked", stats.blocked]].forEach(([label, count]) => {
        readiness.append(el("span", `micro-pill ${label}`, `${titleCase(label)} ${count}`));
      });
      card.append(readiness);

      card.append(renderStatGrid([
        ["Papers", mechanism.papers],
        ["Queue", mechanism.queue_burden],
        ["Targets", mechanism.target_rows],
        ["Trials", mechanism.trial_rows],
        ["10x", mechanism.genomics_rows],
      ]));

      if (mechanism.top_bullets?.length) {
        card.append(el("p", "card-preview", mechanism.top_bullets[0]));
      }
      if (releaseRow?.blocker_summary || releaseRow?.recommended_next_move) {
        const releaseCallout = el("div", "card-callout");
        releaseCallout.append(el("div", "detail-label", "Current release blocker"));
        releaseCallout.append(el("div", "detail-value", releaseRow.blocker_summary || "None"));
        if (releaseRow.recommended_next_move) {
          releaseCallout.append(el("div", "muted compact-note", `Next move: ${formatPromo(releaseRow.recommended_next_move)}`));
        }
        card.append(releaseCallout);
      }
      mechanismCards.append(card);
    });
  }

  function renderDecisionBrief() {
    const brief = data.decision_brief || {};
    document.getElementById("decisionDateHeading").textContent = brief.review_date || "This Week";
    document.getElementById("decisionIntro").textContent =
      `This brief is the bounded weekly control surface. It shows the smallest set of decisions needed to keep the atlas moving toward a publishable TBI investigation product.`;

    const summaryRoot = document.getElementById("decisionSummaryCards");
    clear(summaryRoot);
    const items = [
      ["Lead mechanism", brief.lead_mechanism || data.summary.lead_mechanism],
      ["Stable rows", String(brief.stable_rows || data.summary.stable_rows)],
      ["Idea-ready now", String(brief.idea_summary?.idea_ready_now || data.summary.idea_ready_now || 0)],
      ["Breakthrough-ready now", String(brief.idea_summary?.breakthrough_ready_now || 0)],
    ];
    items.forEach(([label, value]) => {
      const card = el("div", "brief-card");
      card.append(el("div", "brief-card-value", value));
      card.append(el("div", "brief-card-label", label));
      summaryRoot.append(card);
    });

    const decisionsRoot = document.getElementById("decisionCards");
    clear(decisionsRoot);
    const decisions = brief.decisions || [];
    if (!decisions.length) {
      decisionsRoot.append(createEmptyState("The weekly brief has not been generated yet."));
    } else {
      decisions.forEach((item) => {
        const card = el("div", "decision-card");
        const header = el("div", "decision-card-header");
        const titleBlock = el("div");
        titleBlock.append(el("h3", "", item.title));
        titleBlock.append(el("p", "decision-text", item.why));
        header.append(titleBlock, el("span", "execution-pill manual", item.recommended_decision || "Decision"));
        card.append(header);

        const grid = el("div", "decision-detail-grid");
        [["What I need from you", item.what_i_need_from_you], ["If yes", item.if_yes]].forEach(([label, value]) => {
          const block = el("div", "meta-block");
          block.append(el("div", "detail-label", label));
          block.append(el("div", "detail-value", value || "—"));
          grid.append(block);
        });
        card.append(grid);
        decisionsRoot.append(card);
      });
    }

    const humanActions = document.getElementById("humanActions");
    clear(humanActions);
    (brief.human_actions || []).forEach((item) => humanActions.append(el("li", "", item)));
    if (!brief.human_actions?.length) {
      humanActions.append(el("li", "", "No explicit human actions are listed yet."));
    }

    const release = document.getElementById("releaseSnapshot");
    clear(release);
    const releaseSummary = brief.release_summary || {};
    [
      `Lead chapter candidate: ${releaseSummary.lead_chapter_candidate || data.summary.lead_mechanism}`,
      `Review track: ${releaseSummary.review_track || 0}`,
      `Hold: ${releaseSummary.hold || 0}`,
      `Core atlas now: ${releaseSummary.core_atlas_now || 0}`,
    ].forEach((item) => release.append(el("span", "micro-pill", item)));
  }

  function renderControlSurface() {
    const releaseRoot = document.getElementById("releaseLaneCards");
    const artifactRoot = document.getElementById("artifactCards");
    const templateRoot = document.getElementById("templateCards");
    const workflowRoot = document.getElementById("workflowCards");
    [releaseRoot, artifactRoot, templateRoot, workflowRoot].forEach(clear);

    data.mechanisms.forEach((mechanism) => {
      const releaseRow = releaseRowForMechanism(mechanism) || {};
      const card = el("div", "release-card");
      const header = el("div", "mechanism-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", mechanism.display_name));
      titleBlock.append(el("p", "card-preview", `${safeNumber(releaseRow.readiness_score || 0)} readiness · ${safeNumber(releaseRow.queue_burden || mechanism.queue_burden)} queue burden`));
      const pills = el("div", "tag-cloud");
      pills.append(el("span", `micro-pill ${releaseTone(releaseRow.gate_status || mechanism.promotion_status)}`, `Gate ${formatPromo(releaseRow.gate_status || mechanism.promotion_status)}`));
      if (releaseRow.release_bucket) pills.append(el("span", `micro-pill ${releaseTone(releaseRow.release_bucket)}`, `Release ${formatPromo(releaseRow.release_bucket)}`));
      if (releaseRow.chapter_role) pills.append(el("span", "micro-pill", `Role ${formatPromo(releaseRow.chapter_role)}`));
      header.append(titleBlock, pills);
      card.append(header);

      card.append(renderStatGrid([
        ["Stable", safeNumber(releaseRow.stable_rows || mechanism.release_stable_rows)],
        ["Provisional", safeNumber(releaseRow.provisional_rows || mechanism.release_provisional_rows)],
        ["Blocked", safeNumber(releaseRow.blocked_rows || mechanism.release_blocked_rows)],
        ["Targets", safeNumber(releaseRow.target_rows || mechanism.target_rows)],
        ["Trials", safeNumber(releaseRow.trial_rows || mechanism.trial_rows)],
      ]));

      const noteGrid = el("div", "release-note-grid");
      [["Blocker", releaseRow.blocker_summary || "None listed"], ["Next move", formatPromo(releaseRow.recommended_next_move || "review atlas state")]].forEach(([label, value]) => {
        const block = el("div", "meta-block");
        block.append(el("div", "detail-label", label));
        block.append(el("div", "detail-value", value));
        noteGrid.append(block);
      });
      card.append(noteGrid);

      const openDossierHref = preferredHref(mechanism.source_path, mechanism.source_github_url);
      const reviewLedgerButton = el("button", "action-button", "Review ledger");
      reviewLedgerButton.type = "button";
      reviewLedgerButton.addEventListener("click", () => setMechanism(mechanism.id, "evidence"));
      const nextActionsButton = el("button", "action-button secondary", "Open queue");
      nextActionsButton.type = "button";
      nextActionsButton.addEventListener("click", () => setMechanism(mechanism.id, "actions"));
      card.append(actionRow([
        reviewLedgerButton,
        makeActionLink("Open dossier", openDossierHref, "secondary"),
        nextActionsButton,
      ]));

      releaseRoot.append(card);
    });

    const paths = data.metadata.generated_from || {};
    const artifacts = [
      ["Weekly review packet", "Bounded human packet for weekly review decisions.", paths.decision_brief],
      ["Release manifest", "Promotion, gate, and release bucket state.", paths.release_manifest],
      ["Program status report", "Top-level status and next moves across the product.", paths.program_status],
      ["Target packet index", "Entry point into target-specific enrichment packets.", paths.target_packet_index],
      ["Chapter synthesis draft", "Current curated cross-mechanism synthesis draft.", paths.chapter_synthesis || paths.chapter],
      ["Chapter evidence ledger", "Structured row-level support for chapter writing.", paths.ledger],
      ["Manual enrichment workpack", "Current human queue for enrichment work.", paths.workpack],
      ["Mechanism dossier index", "Starter mechanism status index.", paths.index],
    ].filter(([, , path]) => normalize(path));

    artifacts.forEach(([label, description, path]) => {
      const card = el("div", "artifact-card");
      card.append(el("div", "eyebrow artifact-eyebrow", "Artifact"));
      card.append(el("h3", "", label));
      card.append(el("p", "card-preview", description));
      card.append(el("div", "path-code", path));
      card.append(actionRow([
        makeActionLink("Open", preferredHref(path), "primary"),
        makeCopyButton("Copy path", path),
      ]));
      artifactRoot.append(card);
    });

    const templates = [
      ["Open Targets manual fill", "Human-fill target template for current atlas priorities.", paths.open_targets_template],
      ["ChEMBL manual fill", "Human-fill compound template for current atlas priorities.", paths.chembl_template],
      ["ClinicalTrials.gov import", "Connector-sidecar trial import template.", paths.clinicaltrials_template],
      ["bioRxiv / medRxiv import", "Connector-sidecar preprint import template.", paths.preprint_template],
      ["10x genomics import", "Optional genomics template for connector enrichment.", paths.tenx_template],
    ].filter(([, , path]) => normalize(path));

    templates.forEach(([label, description, path]) => {
      const card = el("div", "artifact-card compact");
      card.append(el("div", "eyebrow artifact-eyebrow", "Template"));
      card.append(el("h3", "", label));
      card.append(el("p", "card-preview", description));
      card.append(el("div", "path-code", path));
      card.append(actionRow([
        makeActionLink("Open", preferredHref(path), "primary"),
        makeCopyButton("Copy path", path),
      ]));
      templateRoot.append(card);
    });

    (data.execution_map || []).forEach((item) => {
      const card = el("div", "artifact-card compact");
      card.append(el("div", "eyebrow artifact-eyebrow", "Workflow"));
      card.append(el("h3", "", item.title));
      card.append(el("p", "card-preview", item.workflow_or_command || item.trigger));
      const buttons = [];
      (item.actions || []).forEach((action) => {
        buttons.push(makeActionLink(action.label, resolveActionHref(action.href), buttons.length ? "secondary" : "primary"));
      });
      buttons.push(makeCopyButton("Copy command", item.workflow_or_command));
      card.append(actionRow(buttons));
      workflowRoot.append(card);
    });
  }

  function renderChapter() {
    const leadRoot = document.getElementById("leadRecommendation");
    const framingRoot = document.getElementById("chapterFraming");
    const priorityRoot = document.getElementById("writingPriority");
    const followRoot = document.getElementById("chapterFollowOn");
    [leadRoot, framingRoot, priorityRoot, followRoot].forEach(clear);

    data.chapter.lead_recommendation.forEach((item) => leadRoot.append(el("li", "", item)));
    data.chapter.framing.forEach((item) => framingRoot.append(el("li", "", item)));
    data.chapter.writing_priority.forEach((item) => priorityRoot.append(el("li", "", item)));
    data.chapter.immediate_follow_on.forEach((item) => followRoot.append(el("li", "", item)));

    renderMarkdownLite(document.getElementById("chapterPreview"), data.chapter.preview_markdown || data.chapter.raw_markdown || "");
  }

  function renderMechanismTabs() {
    const tabs = document.getElementById("mechanismTabs");
    clear(tabs);
    DETAIL_TABS.forEach((tab) => {
      const button = el("button", tab.id === state.selectedDetailTab ? "tab-button is-active" : "tab-button", tab.label);
      button.type = "button";
      button.addEventListener("click", () => {
        state.selectedDetailTab = tab.id;
        renderMechanismDetail();
      });
      tabs.append(button);
    });
  }

  function renderMechanismDetail() {
    const mechanism = mechanismById(state.selectedMechanism);
    const stats = mechanismDerivedStats(mechanism);
    const releaseRow = releaseRowForMechanism(mechanism);
    document.getElementById("selectedMechanismTitle").textContent = mechanism.display_name;
    document.getElementById("selectedMechanismSubtitle").textContent =
      `${formatPromo(mechanism.promotion_status)} · gate ${formatPromo(releaseRow?.gate_status || mechanism.promotion_status)} · release ${formatPromo(releaseRow?.release_bucket || "unassigned")} · ${stats.stable} stable rows · ${stats.provisional} provisional rows · ${stats.blocked} blocked rows`;
    renderMechanismTabs();

    const root = document.getElementById("mechanismDetail");
    clear(root);

    if (state.selectedDetailTab === "overview") {
      const panel = el("div", "panel");
      panel.append(renderStatGrid([
        ["Papers", mechanism.papers],
        ["Queue burden", mechanism.queue_burden],
        ["Targets", mechanism.target_rows],
        ["Trials", mechanism.trial_rows],
        ["Preprints", mechanism.preprint_rows],
      ]));
      const grid = el("div", "panel-grid two");
      const overview = el("div", "detail-section");
      overview.append(el("h3", "", "Mechanism Overview"));
      if (mechanism.overview.length) {
        const list = el("ul", "bullet-list");
        mechanism.overview.forEach((item) => list.append(el("li", "", item)));
        overview.append(list);
      } else {
        overview.append(createEmptyState("Overview bullets are not available yet."));
      }
      const readiness = el("div", "detail-section");
      readiness.append(el("h3", "", "Why It Is At This Status"));
      const list = el("ul", "bullet-list");
      (mechanism.top_bullets.length ? mechanism.top_bullets : ["No summary bullets were produced."]).forEach((item) => list.append(el("li", "", item)));
      readiness.append(list);
      grid.append(overview, readiness);
      panel.append(grid);
      panel.append(renderRichList("Biomarker Signals", mechanism.biomarkers, "No biomarker summary rows yet."));
      root.append(panel);
      return;
    }

    if (state.selectedDetailTab === "evidence") {
      const anchorPanel = el("div", "panel");
      anchorPanel.append(el("h3", "", "Weighted Anchor Papers"));
      anchorPanel.append(renderAnchorTable(mechanism.anchor_papers));
      root.append(anchorPanel);

      const layerPanel = el("div", "panel");
      layerPanel.append(el("h3", "", "Strongest Atlas Layers"));
      layerPanel.append(renderLayerTable(mechanism.atlas_layers));
      root.append(layerPanel);
      return;
    }

    if (state.selectedDetailTab === "translational") {
      const panel = el("div", "panel");
      const lists = el("div", "panel-grid two");
      lists.append(
        renderRichList("Targets", mechanism.targets, "No target enrichment is attached yet."),
        renderRichList("Therapeutics / Compounds", mechanism.therapeutics, "No compound rows are attached yet."),
        renderRichList("Active Trials", mechanism.trials, "No trial rows are attached yet."),
        renderRichList("Preprints + 10x / Genomics", [...mechanism.preprints, ...mechanism.genomics], "No preprint or genomics rows are attached yet.")
      );
      panel.append(lists);
      const bridgeRows = mechanismBridgeRows(mechanism.id);
      panel.append(el("h3", "", "Selected Mechanism Bridge Rows"));
      if (!bridgeRows.length) {
        panel.append(createEmptyState("No bridge rows are available for this mechanism yet."));
      } else {
        const wrap = el("div", "table-wrap");
        const table = document.createElement("table");
        table.innerHTML = `
          <thead>
            <tr>
              <th>Biomarker Seed</th>
              <th>Target</th>
              <th>Compound</th>
              <th>Trial</th>
              <th>Evidence</th>
            </tr>
          </thead>
        `;
        const tbody = document.createElement("tbody");
        bridgeRows.forEach((row) => {
          const tr = document.createElement("tr");
          [row.biomarker_seed, row.target_entity, row.compound_entity, row.trial_entity, row.evidence_summary].forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value || "—";
            tr.append(td);
          });
          tbody.append(tr);
        });
        table.append(tbody);
        wrap.append(table);
        panel.append(wrap);
      }
      root.append(panel);
      return;
    }

    const panel = el("div", "panel");
    const grid = el("div", "panel-grid two");
    const contradictions = el("div", "detail-section");
    contradictions.append(el("h3", "", "Contradiction / Tension"));
    if (mechanism.contradictions.length) {
      const wrap = el("div", "stacked-pills");
      mechanism.contradictions.forEach((item) => wrap.append(el("div", "issue-pill", item)));
      contradictions.append(wrap);
    } else {
      contradictions.append(createEmptyState("No contradiction or tension cues were detected."));
    }
    const gaps = el("div", "detail-section");
    gaps.append(el("h3", "", "Open Questions / Evidence Gaps"));
    if (mechanism.gaps.length) {
      const wrap = el("div", "stacked-pills");
      mechanism.gaps.forEach((item) => wrap.append(el("div", "issue-pill", item)));
      gaps.append(wrap);
    } else {
      gaps.append(createEmptyState("No explicit gaps are listed for this mechanism."));
    }
    grid.append(contradictions, gaps);
    panel.append(grid);

    panel.append(el("h3", "", "Remaining Work Queue"));
    if (mechanism.work_queue.length) {
      const wrap = el("div", "stacked-pills work-queue");
      mechanism.work_queue.forEach((item) => wrap.append(el("div", "issue-pill work-item", item)));
      panel.append(wrap);
    } else {
      panel.append(createEmptyState("No remaining work queue items for this mechanism."));
    }
    root.append(panel);
  }

  function renderCausalChains() {
    const mechanism = mechanismById(state.selectedMechanism);
    const chain = mechanismChain(state.selectedMechanism);
    const summaryRoot = document.getElementById("causalSummary");
    const root = document.getElementById("causalChains");
    clear(summaryRoot);
    clear(root);

    if (!chain) {
      summaryRoot.append(createEmptyState("No causal chain data is available for this mechanism yet."));
      return;
    }

    const summary = el("div", "summary-inline-card");
    summary.append(el("div", "summary-inline-title", `${mechanism.display_name} causal chain`));
    summary.append(el("div", "muted", `This view makes the implied mechanism logic explicit so we can write and test it as a chain rather than as disconnected rows.`));
    summaryRoot.append(summary);

    const card = el("div", "chain-card");
    const header = el("div", "chain-card-header");
    const titleBlock = el("div");
    titleBlock.append(el("h3", "", `${mechanism.display_name} chain`));
    titleBlock.append(el("p", "chain-text", chain.thesis.statement || "No thesis statement is available."));
    header.append(titleBlock, strengthPill(chain.thesis.strength_tag));
    card.append(header);

    const stepList = el("div", "chain-step-list");
    chain.steps.forEach((step, idx) => {
      const item = el("div", "chain-step");
      const top = el("div", "chain-step-top");
      const left = el("div");
      left.append(el("div", "chain-layer", `Step ${idx + 1} · ${titleCase(step.atlas_layer)}`));
      left.append(el("p", "chain-text", step.statement));
      top.append(left, strengthPill(step.strength_tag));
      item.append(top);
      const footer = el("div", "chain-footer");
      footer.append(pmidChips(step.supporting_pmids));
      footer.append(el("span", "micro-pill", formatPromo(step.write_status)));
      item.append(footer);
      stepList.append(item);
    });
    if (!chain.steps.length) {
      stepList.append(createEmptyState("No explicit causal steps are available yet."));
    }
    card.append(stepList);

    const callouts = el("div", "chain-callout-grid");
    const bridgeBlock = el("div", "meta-block");
    bridgeBlock.append(el("div", "detail-label", "Cross-Mechanism Bridge"));
    if (chain.bridges.length) {
      chain.bridges.forEach((bridge) => {
        bridgeBlock.append(el("div", "detail-value", bridge.statement));
        const row = el("div", "tag-cloud");
        row.append(strengthPill(bridge.strength_tag));
        row.append(el("span", "micro-pill", bridge.related_display_name || "Bridge"));
        bridgeBlock.append(row);
      });
    } else {
      bridgeBlock.append(el("div", "detail-value", "No explicit cross-mechanism bridge is attached yet."));
    }

    const translationalBlock = el("div", "meta-block");
    translationalBlock.append(el("div", "detail-label", "Translational Hook"));
    if (chain.translational_hooks.length) {
      chain.translational_hooks.forEach((hook) => {
        translationalBlock.append(el("div", "detail-value", hook.statement));
        translationalBlock.append(strengthPill(hook.strength_tag));
      });
    } else {
      translationalBlock.append(el("div", "detail-value", "No translational hook is attached yet."));
    }

    const caveatBlock = el("div", "meta-block");
    caveatBlock.append(el("div", "detail-label", "Writing Boundary"));
    caveatBlock.append(el("div", "detail-value", chain.caveat.statement || "No explicit writing boundary is attached yet."));
    if (chain.caveat.strength_tag) caveatBlock.append(strengthPill(chain.caveat.strength_tag));

    const nextBlock = el("div", "meta-block");
    nextBlock.append(el("div", "detail-label", "Execution Trigger"));
    nextBlock.append(el("div", "detail-value", chain.next_action || "No next action is attached yet."));

    const subtrackBlock = el("div", "meta-block");
    subtrackBlock.append(el("div", "detail-label", "Narrower Subtracks"));
    if (chain.subtracks?.length) {
      chain.subtracks.forEach((subtrack) => {
        subtrackBlock.append(el("div", "detail-value", `${subtrack.name}: ${subtrack.statement}`));
        const row = el("div", "tag-cloud");
        row.append(strengthPill(subtrack.strength_tag));
        if (normalize(subtrack.supporting_pmids)) row.append(pmidChips(subtrack.supporting_pmids));
        subtrackBlock.append(row);
      });
    } else {
      subtrackBlock.append(el("div", "detail-value", "No narrower subtracks are attached yet."));
    }

    callouts.append(bridgeBlock, translationalBlock, caveatBlock, nextBlock, subtrackBlock);
    card.append(callouts);
    root.append(card);
  }

  function renderIdeas() {
    const mechanism = mechanismById(state.selectedMechanism);
    const ideaRow = mechanismIdeaGate(state.selectedMechanism);
    const ideas = mechanismIdeas(state.selectedMechanism);
    const summaryRoot = document.getElementById("ideaSummary");
    const root = document.getElementById("ideaCards");
    clear(summaryRoot);
    clear(root);

    const summary = el("div", "summary-inline-card");
    const title = ideaRow
      ? `${mechanism.display_name}: ${formatPromo(ideaRow.idea_generation_status)} for idea generation`
      : `${mechanism.display_name}: candidate ideas`;
    summary.append(el("div", "summary-inline-title", title));
    const detail = ideaRow
      ? `${ideaRow.papers} papers · ${ideaRow.full_text_like} full-text-like · ${ideaRow.signal_rows} signal rows · breakthrough status ${formatPromo(ideaRow.breakthrough_status)}`
      : "Candidate ideas generated from the current atlas synthesis state.";
    summary.append(el("div", "muted", detail));
    summaryRoot.append(summary);

    if (!ideas.length) {
      root.append(createEmptyState("No candidate ideas are available for this mechanism yet."));
      return;
    }

    ideas.forEach((idea) => {
      const card = el("div", "idea-card");
      const header = el("div", "idea-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", idea.title));
      titleBlock.append(el("p", "idea-text", idea.statement));
      header.append(titleBlock, strengthPill(idea.strength_tag));
      card.append(header);

      const grid = el("div", "idea-detail-grid");
      [
        ["Why now", idea.why_now],
        ["Operator decision", idea.operator_decision || "Unassigned"],
        ["What it unlocks", idea.unlocks || "Not specified"],
        ["Next test", idea.next_test],
        ["Current blocker", idea.blockers || "None listed"],
        ["Supporting PMIDs", idea.supporting_pmids || "none listed"],
      ].forEach(([label, value]) => {
        const block = el("div", "meta-block");
        block.append(el("div", "detail-label", label));
        if (label === "Supporting PMIDs") {
          block.append(pmidChips(value));
        } else {
          block.append(el("div", "detail-value", value));
        }
        grid.append(block);
      });
      card.append(grid);
      root.append(card);
    });
  }

  function renderEvidence() {
    const mechanism = mechanismById(state.selectedMechanism);
    const allRows = mechanismLedgerRows(state.selectedMechanism);
    fillSelect("evidencePromotionFilter", Array.from(new Set(allRows.map((row) => row.promotion_note).filter(Boolean))).sort(), state.evidencePromotion);
    fillSelect("evidenceLayerFilter", Array.from(new Set(allRows.map((row) => row.atlas_layer).filter(Boolean))).sort(), state.evidenceLayer);

    const rows = filteredLedgerRows();
    const badgeRoot = document.getElementById("ledgerBadges");
    const tableRoot = document.getElementById("ledgerTable");
    const summaryRoot = document.getElementById("evidenceSummary");
    clear(badgeRoot);
    clear(tableRoot);
    clear(summaryRoot);

    const stable = rows.filter((row) => row.confidence_bucket === "stable").length;
    const provisional = rows.filter((row) => row.confidence_bucket === "provisional").length;
    const blocked = rows.filter((row) => normalize(row.promotion_note) !== "ready to write").length;
    const summaryCard = el("div", "summary-inline-card");
    summaryCard.append(el("div", "summary-inline-title", `${mechanism.display_name} evidence review`));
    summaryCard.append(el("div", "muted", `${rows.length} row(s) after filters · ${stable} stable · ${provisional} provisional · ${blocked} blocked`));
    summaryRoot.append(summaryCard);

    [["stable", stable], ["provisional", provisional], ["blocked", blocked]].forEach(([label, count]) => {
      badgeRoot.append(el("span", `badge ${label === "blocked" ? "hold" : label}`, `${titleCase(label)} · ${count}`));
    });

    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.append(createEmptyState("No ledger rows matched the current review filters."));
      tr.append(td);
      tableRoot.append(tr);
      return;
    }

    rows.forEach((row) => {
      const key = ledgerKey(row);
      const tr = document.createElement("tr");
      tr.className = `ledger-row ${row.confidence_bucket}`;
      tr.addEventListener("click", () => {
        state.expandedLedgerKey = state.expandedLedgerKey === key ? null : key;
        renderEvidence();
      });

      const layerTd = document.createElement("td");
      layerTd.textContent = titleCase(row.atlas_layer);
      tr.append(layerTd);

      const claimTd = document.createElement("td");
      const claim = el("div", "claim-cell");
      claim.append(el("div", "claim-text", row.proposed_narrative_claim));
      claim.append(el("div", "muted claim-subtext", `Click for anchor claim, blockers, and contradiction cues.`));
      claimTd.append(claim);
      tr.append(claimTd);

      const anchorTd = document.createElement("td");
      const anchorLink = el("a", "anchor-link", row.best_anchor_pmid);
      anchorLink.href = pubmedLink(row.best_anchor_pmid);
      anchorLink.target = "_blank";
      anchorLink.rel = "noreferrer";
      anchorTd.append(anchorLink);
      tr.append(anchorTd);

      const pmidTd = document.createElement("td");
      pmidTd.append(pmidChips(row.supporting_pmids));
      tr.append(pmidTd);

      const mixTd = document.createElement("td");
      const mixes = parseCounts(row.source_quality_breakdown || row.source_quality_mix);
      if (!mixes.length) {
        mixTd.textContent = "—";
      } else {
        const wrap = el("div", "stacked-micro");
        mixes.forEach((item) => wrap.append(el("div", "micro-line", `${titleCase(item.label)} ${item.count}`)));
        mixTd.append(wrap);
      }
      tr.append(mixTd);

      const strengthTd = document.createElement("td");
      strengthTd.append(strengthPill(row.strength_tag));
      tr.append(strengthTd);

      const promoTd = document.createElement("td");
      promoTd.append(el("span", `micro-pill ${normalize(row.promotion_note) === "ready to write" ? "stable" : "blocked"}`, formatPromo(row.promotion_note)));
      tr.append(promoTd);
      tableRoot.append(tr);

      if (state.expandedLedgerKey === key) {
        const detailTr = document.createElement("tr");
        const detailTd = document.createElement("td");
        detailTd.colSpan = 7;
        const detailWrap = el("div", "detail-drawer");
        const detailGrid = el("div", "panel-grid two");
        const left = el("div", "detail-section");
        left.append(el("h3", "", "Best Anchor Claim"));
        left.append(el("p", "drawer-copy", row.best_anchor_claim_text || "No anchor claim text available."));
        const right = el("div", "detail-section");
        right.append(el("h3", "", "Review Notes"));
        const notes = el("ul", "bullet-list");
        [
          `Writing strength: ${formatPromo(row.strength_tag)}`,
          `Contradiction signal: ${formatPromo(row.contradiction_signal)}`,
          `Action blockers: ${formatPromo(row.action_blockers || "none")}`,
          `Promotion note: ${formatPromo(row.promotion_note)}`,
        ].forEach((item) => notes.append(el("li", "", item)));
        right.append(notes);
        detailGrid.append(left, right);
        detailWrap.append(detailGrid);
        detailTd.append(detailWrap);
        detailTr.append(detailTd);
        tableRoot.append(detailTr);
      }
    });
  }

  function renderWorkpack() {
    const mechanism = mechanismById(state.selectedMechanism);
    const whyRoot = document.getElementById("workpackWhy");
    const orderRoot = document.getElementById("workpackOrder");
    const priorityRoot = document.getElementById("workpackPriorities");
    const fillRoot = document.getElementById("fillTargets");
    const nextRoot = document.getElementById("nextMove");
    const linksRoot = document.getElementById("workpackQuickLinks");
    const hintRoot = document.getElementById("workpackMechanismHint");
    [whyRoot, orderRoot, priorityRoot, fillRoot, nextRoot, linksRoot].forEach(clear);

    const scopedPriorities = data.workpack.top_priorities.filter((item) => item.title.toLowerCase().startsWith(mechanism.display_name.toLowerCase()));
    const priorities = state.showAllWorkpack || !scopedPriorities.length ? data.workpack.top_priorities : scopedPriorities;

    hintRoot.textContent = state.showAllWorkpack || !scopedPriorities.length
      ? `Showing the full workpack. ${mechanism.display_name} stays selected in the other sections.`
      : `Showing priorities filtered to ${mechanism.display_name}.`;
    document.getElementById("toggleWorkpackScope").textContent = state.showAllWorkpack ? "Show selected mechanism" : "Show all priorities";

    data.workpack.why_now.forEach((item) => whyRoot.append(el("li", "", item)));
    data.workpack.fill_order.forEach((item) => orderRoot.append(el("li", "", item)));
    data.workpack.fill_targets.forEach((item) => fillRoot.append(el("li", "", item)));
    data.workpack.next_move.forEach((item) => nextRoot.append(el("li", "", item)));

    priorities.forEach((item) => {
      const card = el("div", "priority-item");
      card.append(el("h4", "", item.title));
      item.details.forEach((detail, idx) => card.append(el("div", idx === 0 ? "priority-meta" : "muted", detail)));
      priorityRoot.append(card);
    });

    if (!priorities.length) {
      priorityRoot.append(createEmptyState("No workpack priorities match the current mechanism."));
    }

    const quickLinks = [
      ["Open target packet index", data.metadata.generated_from.target_packet_index ? `../../${data.metadata.generated_from.target_packet_index}` : ""],
      ["Open ChEMBL template", data.metadata.generated_from.chembl_template ? `../../${data.metadata.generated_from.chembl_template}` : ""],
      ["Open Open Targets template", data.metadata.generated_from.open_targets_template ? `../../${data.metadata.generated_from.open_targets_template}` : ""],
    ].filter(([, href]) => href);
    if (!quickLinks.length) {
      linksRoot.append(createEmptyState("Quick actions will appear after the latest seed packs are generated."));
    } else {
      quickLinks.forEach(([label, href]) => {
        const link = el("a", "action-link", label);
        link.href = resolveActionHref(href);
        if (link.href.startsWith("http")) {
          link.target = "_blank";
          link.rel = "noreferrer";
        }
        linksRoot.append(link);
      });
    }
  }

  function renderBridge() {
    const mechanism = mechanismById(state.selectedMechanism);
    const rows = mechanismBridgeRows(state.selectedMechanism);
    const root = document.getElementById("bridgeTable");
    const summaryRoot = document.getElementById("bridgeSummary");
    clear(root);
    clear(summaryRoot);

    const summary = el("div", "summary-inline-card");
    summary.append(el("div", "summary-inline-title", `${mechanism.display_name} translational bridge`));
    summary.append(el("div", "muted", rows.length ? `${rows.length} bridge row(s) currently attached. We still need stronger compound/trial depth for the most compelling mechanism lanes.` : `No translational bridge rows are attached yet.`));
    summaryRoot.append(summary);

    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 6;
      td.append(createEmptyState("No translational bridge rows are available for the selected mechanism."));
      tr.append(td);
      root.append(tr);
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      [mechanism.display_name, row.biomarker_seed, row.target_entity, row.compound_entity, row.trial_entity, row.evidence_summary].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value || "—";
        tr.append(td);
      });
      root.append(tr);
    });
  }

  function renderExecutionMap() {
    const root = document.getElementById("executionCards");
    clear(root);
    (data.execution_map || []).forEach((item) => {
      const card = el("div", "execution-card");
      const header = el("div", "execution-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", item.title));
      titleBlock.append(el("p", "execution-text", item.trigger));
      const mode = item.id.includes("daily") ? "automated" : item.id.includes("tenx") ? "optional" : "manual";
      header.append(titleBlock, el("span", `execution-pill ${mode}`, item.cadence));
      card.append(header);

      const grid = el("div", "execution-grid");
      [["Decision needed", item.operator_decision], ["Workflow / command", item.workflow_or_command], ["Unlocks", item.unlocks]].forEach(([label, value]) => {
        const block = el("div", "meta-block");
        block.append(el("div", "detail-label", label));
        block.append(el("div", "detail-value", value));
        grid.append(block);
      });
      card.append(grid);
      if (item.actions?.length) {
        const actionRow = el("div", "action-row");
        item.actions.filter((action) => action.href).forEach((action) => {
          const link = el("a", `action-link ${action.kind || "local"}`, action.label);
          link.href = resolveActionHref(action.href);
          if (link.href.startsWith("http")) {
            link.target = "_blank";
            link.rel = "noreferrer";
          }
          actionRow.append(link);
        });
        if (actionRow.childNodes.length) card.append(actionRow);
      }
      root.append(card);
    });
  }

  function renderSources() {
    const root = document.getElementById("dataSources");
    const paths = data.metadata.generated_from;
    const repo = data.metadata.repo || {};
    const sourceList = [
      paths.index,
      paths.chapter_synthesis || paths.chapter,
      paths.ledger,
      paths.workpack,
      paths.bridge,
      paths.hypothesis_candidates,
    ].filter(Boolean);
    clear(root);
    root.append(el("span", "", `Built from ${sourceList.join(", ")}.`));
    const footerActions = actionRow([
      makeActionLink("Repo", repo.repo_url, "secondary"),
      makeActionLink("Actions", repo.actions_url, "secondary"),
      makeActionLink("Open release manifest", preferredHref(paths.release_manifest), "secondary"),
    ]);
    root.append(footerActions);
  }

  function setMechanism(id, sectionId) {
    state.selectedMechanism = id;
    if (sectionId) {
      requestAnimationFrame(() => document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
    renderAll();
  }

  function bindControls() {
    const sidebarSearch = document.getElementById("sidebarSearch");
    const evidenceSearch = document.getElementById("evidenceSearch");
    const confidenceFilter = document.getElementById("evidenceConfidenceFilter");
    const promotionFilter = document.getElementById("evidencePromotionFilter");
    const layerFilter = document.getElementById("evidenceLayerFilter");
    const toggleWorkpackScope = document.getElementById("toggleWorkpackScope");

    if (!sidebarSearch.dataset.bound) {
      sidebarSearch.addEventListener("input", (event) => {
        state.sidebarSearch = event.target.value;
        state.evidenceSearch = event.target.value;
        document.getElementById("evidenceSearch").value = event.target.value;
        renderSummary();
        renderEvidence();
      });
      sidebarSearch.dataset.bound = "true";
    }

    if (!evidenceSearch.dataset.bound) {
      evidenceSearch.addEventListener("input", (event) => {
        state.evidenceSearch = event.target.value;
        state.sidebarSearch = event.target.value;
        document.getElementById("sidebarSearch").value = event.target.value;
        renderSummary();
        renderEvidence();
      });
      evidenceSearch.dataset.bound = "true";
    }

    if (!confidenceFilter.dataset.bound) {
      confidenceFilter.addEventListener("change", (event) => {
        state.evidenceConfidence = event.target.value;
        renderEvidence();
      });
      confidenceFilter.dataset.bound = "true";
    }

    if (!promotionFilter.dataset.bound) {
      promotionFilter.addEventListener("change", (event) => {
        state.evidencePromotion = event.target.value;
        renderEvidence();
      });
      promotionFilter.dataset.bound = "true";
    }

    if (!layerFilter.dataset.bound) {
      layerFilter.addEventListener("change", (event) => {
        state.evidenceLayer = event.target.value;
        renderEvidence();
      });
      layerFilter.dataset.bound = "true";
    }

    if (!toggleWorkpackScope.dataset.bound) {
      toggleWorkpackScope.addEventListener("click", () => {
        state.showAllWorkpack = !state.showAllWorkpack;
        renderWorkpack();
      });
      toggleWorkpackScope.dataset.bound = "true";
    }
  }

  function renderAll() {
    bindControls();
    document.getElementById("sidebarSearch").value = state.sidebarSearch;
    document.getElementById("evidenceSearch").value = state.evidenceSearch;
    document.getElementById("evidenceConfidenceFilter").value = state.evidenceConfidence;
    renderSummary();
    renderDecisionBrief();
    renderControlSurface();
    renderChapter();
    renderMechanismDetail();
    renderCausalChains();
    renderIdeas();
    renderEvidence();
    renderWorkpack();
    renderBridge();
    renderExecutionMap();
    renderSources();
  }

  renderAll();
})();
