(function () {
  const data = window.ATLAS_VIEWER_DATA;
  if (!data) {
    document.body.innerHTML = "<pre>Atlas viewer data was not found.</pre>";
    return;
  }

  const state = {
    selectedMechanism:
      data.mechanisms.find((item) => item.display_name === data.summary.lead_mechanism)?.id ||
      data.mechanisms[0]?.id,
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

  function renderSummary() {
    document.getElementById("leadMechanism").textContent = data.summary.lead_mechanism;
    document.getElementById("leadHint").textContent = data.summary.top_priority
      ? `Next manual priority: ${data.summary.top_priority}`
      : "Starter atlas synthesis";
    document.getElementById("heroSummary").textContent =
      `${data.summary.lead_mechanism} is the current lead chapter. ` +
      `${data.summary.stable_rows} ledger rows are stable, ${data.summary.provisional_rows} are provisional, and ${data.summary.blocked_rows} rows still need cleanup before they are fully writing-grade.`;

    const summaryCards = [
      ["Lead Mechanism", data.summary.lead_mechanism],
      ["Stable Ledger Rows", String(data.summary.stable_rows)],
      ["Provisional Rows", String(data.summary.provisional_rows)],
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
      const button = el("button", state.selectedMechanism === mechanism.id ? "is-active" : "");
      button.innerHTML = `
        <div>${mechanism.display_name}</div>
        <div class="muted">${mechanism.promotion_status} · ${mechanism.papers} papers</div>
      `;
      button.addEventListener("click", () => {
        state.selectedMechanism = mechanism.id;
        renderAll();
      });
      nav.append(button);
    });

    const mechanismCards = document.getElementById("mechanismCards");
    clear(mechanismCards);
    data.mechanisms.forEach((mechanism) => {
      const card = el("div", "card");
      const header = el("div", "mechanism-card-header");
      const titleBlock = el("div");
      titleBlock.append(el("h3", "", mechanism.display_name));
      const subtitle = el("div", "muted", `Queue burden ${mechanism.queue_burden} · ${mechanism.papers} papers`);
      titleBlock.append(subtitle);
      const pill = el("span", `status-pill ${mechanism.promotion_status}`, mechanism.promotion_status);
      header.append(titleBlock, pill);
      card.append(header);

      const meta = el("div", "mechanism-meta");
      [
        ["Papers", mechanism.papers],
        ["Queue", mechanism.queue_burden],
        ["Targets", mechanism.target_rows],
        ["Trials", mechanism.trial_rows],
        ["10x", mechanism.genomics_rows],
      ].forEach(([label, value]) => {
        const block = el("div", "meta-block");
        block.append(el("div", "meta-label", label));
        block.append(el("div", "meta-value", String(value)));
        meta.append(block);
      });
      card.append(meta);
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
  }

  function renderMechanismDetail() {
    const mechanism = mechanismById(state.selectedMechanism);
    document.getElementById("selectedMechanismTitle").textContent = mechanism.display_name;
    const root = document.getElementById("mechanismDetail");
    clear(root);

    const overviewCard = el("div", "panel");
    const header = el("div", "detail-card-header");
    const left = el("div");
    left.append(el("h3", "", mechanism.display_name));
    left.append(el("div", "muted", mechanism.top_bullets[2] || ""));
    const pill = el("span", `status-pill ${mechanism.promotion_status}`, mechanism.promotion_status);
    header.append(left, pill);
    overviewCard.append(header);
    const grid = el("div", "panel-grid two");
    const overview = el("div", "detail-section");
    overview.append(el("h3", "", "Overview"));
    const overviewList = el("ul", "bullet-list");
    mechanism.overview.forEach((item) => overviewList.append(el("li", "", item)));
    overview.append(overviewList);
    const gaps = el("div", "detail-section");
    gaps.append(el("h3", "", "Open Questions / Evidence Gaps"));
    const gapList = el("ul", "bullet-list");
    mechanism.gaps.forEach((item) => gapList.append(el("li", "", item)));
    gaps.append(gapList);
    grid.append(overview, gaps);
    overviewCard.append(grid);
    root.append(overviewCard);

    const anchorsCard = el("div", "panel");
    anchorsCard.append(el("h3", "", "Weighted Anchor Papers"));
    anchorsCard.append(renderTable(
      mechanism.anchor_papers,
      ["PMID", "Source Quality", "Quality Bucket", "Avg Depth", "Example Claim"]
    ));
    root.append(anchorsCard);

    const layersCard = el("div", "panel");
    layersCard.append(el("h3", "", "Strongest Atlas Layers"));
    layersCard.append(renderTable(
      mechanism.atlas_layers,
      ["Atlas Layer", "Papers", "Full-text-like", "Abstract-only", "Avg Depth", "Anchor PMIDs"]
    ));
    root.append(layersCard);

    const queueCard = el("div", "panel");
    const queueGrid = el("div", "panel-grid two");
    const contradictions = el("div", "detail-section");
    contradictions.append(el("h3", "", "Contradiction / Tension"));
    const contradictionList = el("ul", "bullet-list");
    (mechanism.contradictions.length ? mechanism.contradictions : ["No contradiction or tension cues were detected."])
      .forEach((item) => contradictionList.append(el("li", "", item)));
    contradictions.append(contradictionList);
    const queue = el("div", "detail-section");
    queue.append(el("h3", "", "Remaining Work Queue"));
    const queueList = el("ul", "bullet-list");
    mechanism.work_queue.forEach((item) => queueList.append(el("li", "", item)));
    queue.append(queueList);
    queueGrid.append(contradictions, queue);
    queueCard.append(queueGrid);
    root.append(queueCard);
  }

  function renderLedger() {
    const rows = mechanismLedgerRows(state.selectedMechanism);
    const badgeRoot = document.getElementById("ledgerBadges");
    const tableRoot = document.getElementById("ledgerTable");
    clear(badgeRoot);
    clear(tableRoot);

    const confidenceCounts = rows.reduce((acc, row) => {
      acc[row.confidence_bucket] = (acc[row.confidence_bucket] || 0) + 1;
      return acc;
    }, {});
    Object.entries(confidenceCounts).forEach(([label, count]) => {
      const badge = el("span", `badge ${label}`, `${label} · ${count}`);
      badgeRoot.append(badge);
    });

    rows.forEach((row) => {
      const tr = document.createElement("tr");
      [
        row.atlas_layer,
        row.proposed_narrative_claim,
        row.supporting_pmids,
        row.source_quality_mix,
        row.confidence_bucket,
        row.promotion_note,
      ].forEach((value) => {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      });
      tableRoot.append(tr);
    });
  }

  function renderWorkpack() {
    const whyRoot = document.getElementById("workpackWhy");
    const orderRoot = document.getElementById("workpackOrder");
    const priorityRoot = document.getElementById("workpackPriorities");
    const fillRoot = document.getElementById("fillTargets");
    const nextRoot = document.getElementById("nextMove");
    [whyRoot, orderRoot, priorityRoot, fillRoot, nextRoot].forEach(clear);

    data.workpack.why_now.forEach((item) => whyRoot.append(el("li", "", item)));
    data.workpack.fill_order.forEach((item) => orderRoot.append(el("li", "", item)));
    data.workpack.fill_targets.forEach((item) => fillRoot.append(el("li", "", item)));
    data.workpack.next_move.forEach((item) => nextRoot.append(el("li", "", item)));

    data.workpack.top_priorities.forEach((item) => {
      const card = el("div", "priority-item");
      card.append(el("h4", "", item.title));
      item.details.forEach((detail, idx) => {
        const cls = idx === 0 ? "priority-meta" : "muted";
        card.append(el("div", cls, detail));
      });
      priorityRoot.append(card);
    });
  }

  function renderBridge() {
    const rows = mechanismBridgeRows(state.selectedMechanism);
    const root = document.getElementById("bridgeTable");
    clear(root);
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      [
        row.canonical_mechanism,
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

  function renderTable(rows, headers) {
    const wrap = el("div", "table-wrap");
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    headers.forEach((header) => trHead.append(el("th", "", header)));
    thead.append(trHead);
    table.append(thead);
    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      headers.forEach((header) => {
        const td = document.createElement("td");
        td.textContent = row[header] || "—";
        tr.append(td);
      });
      tbody.append(tr);
    });
    table.append(tbody);
    wrap.append(table);
    return wrap;
  }

  function renderSources() {
    const root = document.getElementById("dataSources");
    const paths = data.metadata.generated_from;
    root.textContent =
      `Built from ${paths.index}, ${paths.chapter}, ${paths.ledger}, ${paths.workpack}, and ${paths.bridge}.`;
  }

  function renderAll() {
    renderSummary();
    renderChapter();
    renderMechanismDetail();
    renderLedger();
    renderWorkpack();
    renderBridge();
    renderSources();
  }

  renderAll();
})();
