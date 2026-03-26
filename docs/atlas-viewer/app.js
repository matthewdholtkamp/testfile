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

  function slugify(value) {
    return normalize(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
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

  function ledgerKey(row) {
    return [row.mechanism_display_name, row.atlas_layer, row.best_anchor_pmid, row.proposed_narrative_claim].join("|");
  }

  function formatPromo(value) {
    return sentenceCase(normalize(value).replace(/_/g, " "));
  }

  function parseCounts(value) {
    return normalize(value)
      .split(";")
      .map((entry) => entry.trim())
      .filter(Boolean)
      .map((entry) => {
        const [label, count] = entry.split(":");
        return {
          label: normalize(label),
          count: safeNumber(count),
        };
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

  function metadataTimestamp() {
    const allPaths = Object.values(data.metadata.generated_from || {});
    const match = allPaths
      .map((path) => path.match(/(\d{4}-\d{2}-\d{2})_(\d{6})/))
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

  function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setMechanism(id, sectionId) {
    state.selectedMechanism = id;
    if (sectionId) {
      requestAnimationFrame(() => scrollToSection(sectionId));
    }
    renderAll();
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

  function createEmptyState(message) {
    const card = el("div", "empty-state");
    card.append(el("div", "muted", message));
    return card;
  }

  function renderRichList(title, items, emptyMessage) {
    const section = el("div", "detail-section");
    section.append(el("h3", "", title));
    if (!items || !items.length) {
      section.append(createEmptyState(emptyMessage));
      return section;
    }
    const wrap = el("div", "tag-cloud");
    items.forEach((item) => wrap.append(el("span", "tag-pill", item)));
    section.append(wrap);
    return section;
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
    const firstOption = select.querySelector('option[value="all"]');
    clear(select);
    if (firstOption) {
      select.append(firstOption);
    } else {
      const option = document.createElement("option");
      option.value = "all";
      option.textContent = "All";
      select.append(option);
    }
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
      ]
        .join(" ")
        .toLowerCase();

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
      ["Provisional Rows", String(data.summary.provisional_rows)],
      ["Blocked Rows", String(data.summary.blocked_rows)],
      ["Mechanisms In Scope", String(data.summary.mechanism_count)],
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
      button.append(
        el(
          "div",
          "muted nav-subtitle",
          `${formatPromo(mechanism.promotion_status)} · ${stats.stable} stable · ${stats.blocked} blocked`
        )
      );
      button.addEventListener("click", () => setMechanism(mechanism.id, "deep-dive"));
      nav.append(button);
    });

    const mechanismCards = document.getElementById("mechanismCards");
    clear(mechanismCards);
    data.mechanisms.forEach((mechanism) => {
      const stats = mechanismDerivedStats(mechanism);
      const card = el("button", "card mechanism-card-button");
      card.type = "button";
      card.addEventListener("click", () => setMechanism(mechanism.id, "deep-dive"));

      const header = el("div", "mechanism-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", mechanism.display_name));
      titleBlock.append(el("div", "muted", `${mechanism.queue_burden} open queue items · ${mechanism.papers} papers`));
      const pill = el("span", `status-pill ${mechanism.promotion_status}`, formatPromo(mechanism.promotion_status));
      header.append(titleBlock, pill);
      card.append(header);

      const readiness = el("div", "readiness-strip");
      [
        ["stable", stats.stable],
        ["provisional", stats.provisional],
        ["blocked", stats.blocked],
      ].forEach(([label, count]) => {
        const chip = el("span", `micro-pill ${label}`, `${titleCase(label)} ${count}`);
        readiness.append(chip);
      });
      card.append(readiness);

      card.append(
        renderStatGrid([
          ["Papers", mechanism.papers],
          ["Queue", mechanism.queue_burden],
          ["Targets", mechanism.target_rows],
          ["Trials", mechanism.trial_rows],
          ["10x", mechanism.genomics_rows],
        ])
      );

      if (mechanism.top_bullets && mechanism.top_bullets.length) {
        card.append(el("p", "card-preview", mechanism.top_bullets[0]));
      }
      mechanismCards.append(card);
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

    renderMarkdownLite(
      document.getElementById("chapterPreview"),
      data.chapter.preview_markdown || data.chapter.raw_markdown || ""
    );
  }

  function renderMechanismTabs() {
    const tabs = document.getElementById("mechanismTabs");
    clear(tabs);
    DETAIL_TABS.forEach((tab) => {
      const button = el("button", tab.id === state.selectedDetailTab ? "tab-button is-active" : "tab-button", tab.label);
      button.type = "button";
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(tab.id === state.selectedDetailTab));
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
    document.getElementById("selectedMechanismTitle").textContent = mechanism.display_name;
    document.getElementById("selectedMechanismSubtitle").textContent =
      `${formatPromo(mechanism.promotion_status)} · ${stats.stable} stable rows · ${stats.provisional} provisional rows · ${stats.blocked} blocked rows`;
    renderMechanismTabs();

    const root = document.getElementById("mechanismDetail");
    clear(root);

    if (state.selectedDetailTab === "overview") {
      const panel = el("div", "panel");
      panel.append(
        renderStatGrid([
          ["Papers", mechanism.papers],
          ["Queue burden", mechanism.queue_burden],
          ["Targets", mechanism.target_rows],
          ["Trials", mechanism.trial_rows],
          ["Preprints", mechanism.preprint_rows],
        ])
      );
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
          [row.biomarker_seed, row.target_entity, row.compound_entity, row.trial_entity, row.evidence_tiers].forEach((value) => {
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

  function renderEvidence() {
    const mechanism = mechanismById(state.selectedMechanism);
    const allRows = mechanismLedgerRows(state.selectedMechanism);
    fillSelect(
      "evidencePromotionFilter",
      Array.from(new Set(allRows.map((row) => row.promotion_note).filter(Boolean))).sort(),
      state.evidencePromotion
    );
    fillSelect(
      "evidenceLayerFilter",
      Array.from(new Set(allRows.map((row) => row.atlas_layer).filter(Boolean))).sort(),
      state.evidenceLayer
    );

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
    summaryCard.append(
      el(
        "div",
        "muted",
        `${rows.length} row(s) after filters · ${stable} stable · ${provisional} provisional · ${blocked} blocked`
      )
    );
    summaryRoot.append(summaryCard);

    [
      ["stable", stable],
      ["provisional", provisional],
      ["blocked", blocked],
    ].forEach(([label, count]) => {
      const badge = el("span", `badge ${label === "blocked" ? "hold" : label}`, `${titleCase(label)} · ${count}`);
      badgeRoot.append(badge);
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
      const mixes = parseCounts(row.source_quality_mix);
      if (!mixes.length) {
        mixTd.textContent = "—";
      } else {
        const wrap = el("div", "stacked-micro");
        mixes.forEach((item) => wrap.append(el("div", "micro-line", `${titleCase(item.label)} ${item.count}`)));
        mixTd.append(wrap);
      }
      tr.append(mixTd);

      const confTd = document.createElement("td");
      confTd.append(el("span", `badge ${row.confidence_bucket}`, formatPromo(row.confidence_bucket)));
      tr.append(confTd);

      const promoTd = document.createElement("td");
      promoTd.append(el("span", `micro-pill ${normalize(row.promotion_note) === "ready to write" ? "stable" : "blocked"}`, formatPromo(row.promotion_note)));
      tr.append(promoTd);
      tableRoot.append(tr);

      if (state.expandedLedgerKey === key) {
        const detailTr = document.createElement("tr");
        detailTr.className = "detail-row";
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
    const hintRoot = document.getElementById("workpackMechanismHint");
    [whyRoot, orderRoot, priorityRoot, fillRoot, nextRoot].forEach(clear);

    const scopedPriorities = data.workpack.top_priorities.filter((item) =>
      item.title.toLowerCase().startsWith(mechanism.display_name.toLowerCase())
    );
    const priorities = state.showAllWorkpack || !scopedPriorities.length ? data.workpack.top_priorities : scopedPriorities;

    hintRoot.textContent = state.showAllWorkpack || !scopedPriorities.length
      ? `Showing the full workpack. ${mechanism.display_name} stays selected in Deep Dive and Evidence.`
      : `Showing priorities filtered to ${mechanism.display_name}.`;
    document.getElementById("toggleWorkpackScope").textContent = state.showAllWorkpack ? "Show selected mechanism" : "Show all priorities";

    data.workpack.why_now.forEach((item) => whyRoot.append(el("li", "", item)));
    data.workpack.fill_order.forEach((item) => orderRoot.append(el("li", "", item)));
    data.workpack.fill_targets.forEach((item) => fillRoot.append(el("li", "", item)));
    data.workpack.next_move.forEach((item) => nextRoot.append(el("li", "", item)));

    priorities.forEach((item) => {
      const card = el("div", "priority-item");
      card.append(el("h4", "", item.title));
      item.details.forEach((detail, idx) => {
        const cls = idx === 0 ? "priority-meta" : "muted";
        card.append(el("div", cls, detail));
      });
      priorityRoot.append(card);
    });

    if (!priorities.length) {
      priorityRoot.append(createEmptyState("No workpack priorities match the current mechanism."));
    }
  }

  function renderBridge() {
    const mechanism = mechanismById(state.selectedMechanism);
    const rows = mechanismBridgeRows(state.selectedMechanism);
    const root = document.getElementById("bridgeTable");
    const summaryRoot = document.getElementById("bridgeSummary");
    clear(root);
    clear(summaryRoot);

    summaryRoot.append(
      el(
        "div",
        "summary-inline-card",
        rows.length
          ? `${mechanism.display_name}: ${rows.length} translational bridge row(s) currently attached.`
          : `${mechanism.display_name}: no translational bridge rows are attached yet.`
      )
    );

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
      [
        mechanism.display_name,
        row.biomarker_seed,
        row.target_entity,
        row.compound_entity,
        row.trial_entity,
        row.evidence_tiers,
      ].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value || "—";
        tr.append(td);
      });
      root.append(tr);
    });
  }

  function renderSources() {
    const root = document.getElementById("dataSources");
    const paths = data.metadata.generated_from;
    const sourceList = [
      paths.index,
      paths.chapter_synthesis || paths.chapter,
      paths.ledger,
      paths.workpack,
      paths.bridge,
    ].filter(Boolean);
    root.textContent = `Built from ${sourceList.join(", ")}.`;
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
        const value = event.target.value;
        state.sidebarSearch = value;
        state.evidenceSearch = value;
        document.getElementById("evidenceSearch").value = value;
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
    renderChapter();
    renderMechanismDetail();
    renderEvidence();
    renderWorkpack();
    renderBridge();
    renderSources();
  }

  renderAll();
})();
