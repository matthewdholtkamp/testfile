import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  CircleAlert,
  Clock3,
  FileText,
  LoaderCircle,
  RefreshCw,
  ScrollText,
} from "lucide-react";
import fallbackData from "./data.json";

const GITHUB_OWNER = "matthewdholtkamp";
const GITHUB_REPO = "testfile";
const GITHUB_REF = "main";
const GITHUB_TOKEN_KEY = "atlas-github-token";
const GITHUB_STATE_FILE = "docs/command_snapshot.json";

type AnyRecord = Record<string, any>;
type SnapshotSource = "embedded" | "local" | "github";

function getInjectedPayload(): AnyRecord | null {
  const globalValue = (
    window as typeof window & { EMBEDDED_PAYLOAD?: AnyRecord }
  ).EMBEDDED_PAYLOAD;
  return globalValue && typeof globalValue === "object" ? globalValue : null;
}

function normalizeText(value: unknown): string {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function decodeBase64(value: string): string {
  return window.atob(value.replace(/\n/g, ""));
}

function formatRelativeTime(value: unknown): string {
  if (!value) return "Not available";
  const parsed = Date.parse(String(value));
  if (Number.isNaN(parsed)) return String(value);

  const diffMs = Date.now() - parsed;
  const diffMinutes = Math.floor(diffMs / 60_000);
  if (diffMinutes <= 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(parsed);
}

function formatDateTime(value: unknown): string {
  if (!value) return "Not available";
  const parsed = Date.parse(String(value));
  if (Number.isNaN(parsed)) return String(value);

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

function humanize(value: unknown): string {
  const text = String(value || "").replace(/[_-]+/g, " ").trim();
  if (!text) return "Not available";
  return text.replace(/\b\w/g, (character) => character.toUpperCase());
}

function fetchLocalSnapshot(): Promise<AnyRecord> {
  return fetch(`./command_snapshot.json?v=${Date.now()}`, {
    cache: "no-store",
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Could not load command snapshot (${response.status}).`);
    }
    return response.json();
  });
}

async function fetchGitHubSnapshot(token: string): Promise<AnyRecord> {
  const response = await fetch(
    `https://api.github.com/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/contents/${encodeURIComponent(GITHUB_STATE_FILE)}?ref=${encodeURIComponent(GITHUB_REF)}`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.message || `GitHub API error (${response.status}).`,
    );
  }

  const data = await response.json();
  return JSON.parse(decodeBase64(data.content || ""));
}

function encodeRepoPath(path: string): string {
  return path
    .split("/")
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

function getRepoTreeUrl(relativePath?: string): string {
  if (!relativePath) {
    return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/tree/${GITHUB_REF}`;
  }

  return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/tree/${GITHUB_REF}/${encodeRepoPath(relativePath)}`;
}

function getRepoBlobUrl(relativePath?: string): string {
  if (!relativePath) {
    return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/blob/${GITHUB_REF}`;
  }

  return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/blob/${GITHUB_REF}/${encodeRepoPath(relativePath)}`;
}

function getPackUrl(packKey?: string): string {
  if (!packKey) {
    return getRepoTreeUrl("outputs/manuscripts");
  }

  return getRepoTreeUrl(`outputs/manuscripts/${packKey}`);
}

function getDraftUrl(candidate: AnyRecord | null): string {
  const draftPath = candidate?.draft_output?.manuscript_draft_relative_path;
  if (draftPath) return getRepoBlobUrl(draftPath);

  const folderPath = candidate?.draft_output?.folder_relative_path;
  if (folderPath) return getRepoTreeUrl(folderPath);

  return getPackUrl(candidate?.pack_key);
}

function getPrimaryJournal(candidate: AnyRecord | null): AnyRecord | null {
  return candidate?.journal_targets?.primary?.journal || null;
}

function getLeadBlocker(candidate: AnyRecord | null): string {
  if (!candidate) return "No blocker named yet.";

  if (candidate?.top_blocker) return candidate.top_blocker;

  const blockedTask = Array.isArray(candidate?.task_ledger)
    ? candidate.task_ledger.find(
        (task: AnyRecord) => normalizeText(task?.status) === "blocked",
      )
    : null;

  return (
    blockedTask?.execution_note ||
    blockedTask?.rationale ||
    candidate?.journal_targets?.primary?.requirements?.reasons?.[0] ||
    "No blocker named yet."
  );
}

function getTaskStatusLine(candidate: AnyRecord | null): string {
  if (!candidate) return "No active manuscript status available.";

  const counts = candidate?.task_execution_summary?.status_counts || {};
  const parts = [
    candidate?.draft_status ? humanize(candidate.draft_status) : "Draft status not set",
    counts.running ? `${counts.running} running` : "",
    counts.blocked ? `${counts.blocked} blocked` : "",
    counts.satisfied ? `${counts.satisfied} satisfied` : "",
  ].filter(Boolean);

  return parts.join(" · ");
}

function getMetadataSummary(candidate: AnyRecord): string {
  const parts = [];

  if (candidate?.ready_for_metadata_only) parts.push("Only metadata remains");
  if (candidate?.missing_metadata_summary?.metadata_item_count) {
    parts.push(
      `${candidate.missing_metadata_summary.metadata_item_count} metadata items to finish`,
    );
  }
  parts.push(humanize(candidate?.generated_draft_status || "draft_generated"));
  if (candidate?.journal_targets?.primary?.requirements?.checked) {
    parts.push("Journal requirements verified");
  }

  return parts.join(" · ") || "Waiting on metadata prep";
}

function isMetadataReady(candidate: AnyRecord): boolean {
  return Boolean(candidate?.ready_for_metadata_only);
}

function dedupeCandidates(candidates: AnyRecord[]): AnyRecord[] {
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    const key = candidate?.candidate_id || candidate?.title;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function sourceLabel(source: SnapshotSource): string {
  if (source === "github") return `GitHub live · ${GITHUB_REF}`;
  if (source === "embedded") return "Embedded snapshot";
  return "Local snapshot";
}

function chipTone(
  tone: "neutral" | "accent" | "warning" | "danger" = "neutral",
): string {
  return {
    neutral: "desk-chip desk-chip-neutral",
    accent: "desk-chip desk-chip-accent",
    warning: "desk-chip desk-chip-warning",
    danger: "desk-chip desk-chip-danger",
  }[tone];
}

function StatusChip({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "warning" | "danger";
}) {
  return <span className={chipTone(tone)}>{children}</span>;
}

function ManuscriptRow({
  candidate,
  eyebrow,
  summary,
  secondaryLinks,
}: {
  candidate: AnyRecord;
  eyebrow: string;
  summary: string;
  secondaryLinks?: Array<{ href: string; label: string }>;
}) {
  const journal = getPrimaryJournal(candidate);
  const links = secondaryLinks?.filter(Boolean) || [];

  return (
    <li className="desk-list-row">
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0 space-y-2">
          <div className="desk-eyebrow">{eyebrow}</div>
          <a
            className="desk-link text-[1.1rem] font-semibold text-[var(--ink)]"
            href={getDraftUrl(candidate)}
            target="_blank"
            rel="noreferrer"
          >
            {candidate?.title || "Untitled manuscript"}
          </a>
          <p className="max-w-3xl text-sm leading-6 text-[var(--muted)]">
            {summary}
          </p>
        </div>
        <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-[var(--accent)]" />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs tracking-[0.08em] text-[var(--muted)] uppercase">
        <span>{humanize(candidate?.manuscript_gate_state || candidate?.queue_status)}</span>
        <span>{humanize(candidate?.draft_status)}</span>
        {journal?.name ? <span>{journal.name}</span> : null}
        <span>Updated {formatRelativeTime(candidate?.last_pack_refresh)}</span>
        {links.map((link) => (
          <a
            key={`${candidate?.candidate_id || candidate?.title}-${link.href}-${link.label}`}
            className="desk-link"
            href={link.href}
            target="_blank"
            rel="noreferrer"
          >
            {link.label}
          </a>
        ))}
      </div>
    </li>
  );
}

export default function App() {
  const initialPayload = (getInjectedPayload() || fallbackData) as AnyRecord;
  const [payload, setPayload] = useState<AnyRecord>(initialPayload);
  const [source, setSource] = useState<SnapshotSource>(
    getInjectedPayload() ? "embedded" : "local",
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [tokenDraft, setTokenDraft] = useState("");

  async function refreshSnapshot(nextToken = githubToken): Promise<void> {
    setRefreshing(true);
    setErrorMessage("");

    try {
      let nextPayload = initialPayload;
      let nextSource: SnapshotSource = getInjectedPayload() ? "embedded" : "local";

      try {
        nextPayload = await fetchLocalSnapshot();
        nextSource = "local";
      } catch {
        nextPayload = initialPayload;
      }

      setPayload(nextPayload);
      setSource(nextSource);

      if (nextToken) {
        const githubSnapshot = await fetchGitHubSnapshot(nextToken);
        setPayload(githubSnapshot);
        setSource("github");
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to refresh the manuscript snapshot.";
      setErrorMessage(message);
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }

  useEffect(() => {
    const storedToken = window.localStorage.getItem(GITHUB_TOKEN_KEY) || "";
    setGithubToken(storedToken);
    setTokenDraft(storedToken);
    async function initialize() {
      await refreshSnapshot(storedToken);
    }
    void initialize();
  }, []);

  async function handleTokenSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedToken = tokenDraft.trim();

    if (!trimmedToken) {
      window.localStorage.removeItem(GITHUB_TOKEN_KEY);
      setGithubToken("");
      await refreshSnapshot("");
      return;
    }

    window.localStorage.setItem(GITHUB_TOKEN_KEY, trimmedToken);
    setGithubToken(trimmedToken);
    await refreshSnapshot(trimmedToken);
  }

  async function handleUseLocalOnly() {
    window.localStorage.removeItem(GITHUB_TOKEN_KEY);
    setGithubToken("");
    setTokenDraft("");
    await refreshSnapshot("");
  }

  const manuscriptQueue = payload?.manuscript_queue || {};
  const activeCandidates = Array.isArray(manuscriptQueue?.active_candidates)
    ? manuscriptQueue.active_candidates
    : [];
  const watchlist = Array.isArray(manuscriptQueue?.watchlist)
    ? manuscriptQueue.watchlist
    : [];

  const allCandidates = useMemo(
    () => dedupeCandidates([...activeCandidates, ...watchlist]),
    [activeCandidates, watchlist],
  );

  const leadCandidate = useMemo(() => {
    const preferredTitle = payload?.goal_progress?.current_manuscript_candidate?.title;

    return (
      activeCandidates.find((candidate: AnyRecord) => candidate?.is_active_path) ||
      activeCandidates.find((candidate: AnyRecord) => candidate?.title === preferredTitle) ||
      allCandidates.find((candidate: AnyRecord) => candidate?.title === preferredTitle) ||
      activeCandidates[0] ||
      allCandidates[0] ||
      null
    );
  }, [activeCandidates, allCandidates, payload]);

  const metadataCandidates = useMemo(() => {
    const explicit = Array.isArray(manuscriptQueue?.ready_for_metadata_only_candidates)
      ? manuscriptQueue.ready_for_metadata_only_candidates
      : [];

    if (explicit.length) {
      return dedupeCandidates(explicit);
    }

    return dedupeCandidates(allCandidates).filter(isMetadataReady);
  }, [allCandidates, manuscriptQueue]);

  const queueCandidates = useMemo(() => {
    const leadId = leadCandidate?.candidate_id;
    return dedupeCandidates([
      ...activeCandidates.filter((candidate: AnyRecord) => candidate?.candidate_id !== leadId),
      ...watchlist,
    ]);
  }, [activeCandidates, leadCandidate, watchlist]);

  const activeCandidateIds = useMemo(
    () => new Set(activeCandidates.map((candidate: AnyRecord) => candidate?.candidate_id)),
    [activeCandidates],
  );

  const leadJournal = getPrimaryJournal(leadCandidate);
  const leadStory =
    payload?.goal_progress?.current_manuscript_candidate?.story ||
    payload?.current_direction?.reason ||
    leadCandidate?.theme_label ||
    "No lead manuscript story has been attached yet.";
  const leadSignals = [
    {
      label: "Manuscript gate",
      value: humanize(leadCandidate?.manuscript_gate_state),
    },
    {
      label: "Primary journal",
      value: leadJournal?.name || "Not set",
    },
    {
      label: "Draft readiness",
      value:
        typeof leadCandidate?.draft_readiness_bar?.score === "number"
          ? `${leadCandidate.draft_readiness_bar.score}/4`
          : "Not scored",
    },
    {
      label: "Last pack refresh",
      value: formatDateTime(leadCandidate?.last_pack_refresh),
    },
  ];

  const summary = manuscriptQueue?.summary || {};
  const snapshotUpdatedAt =
    manuscriptQueue?.generated_at || payload?.board_state?.snapshot_generated_at;

  if (loading) {
    return (
      <div className="desk-shell">
        <div className="desk-wrap flex min-h-screen items-center justify-center">
          <div className="flex items-center gap-3 text-sm tracking-[0.12em] uppercase text-[var(--muted)]">
            <LoaderCircle className="h-5 w-5 animate-spin text-[var(--accent)]" />
            Loading manuscript desk
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="desk-shell">
      <div className="desk-wrap">
        <header className="border-b border-[var(--line)] pb-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <div className="desk-eyebrow">Portal UI · Manuscript-first desk</div>
              <div className="space-y-3">
                <h1 className="desk-title text-4xl leading-none sm:text-5xl lg:text-6xl">
                  Current lead manuscript, without the cockpit.
                </h1>
                <p className="max-w-2xl text-base leading-7 text-[var(--muted)] sm:text-lg">
                  {payload?.program_status?.line ||
                    "This surface stays focused on the manuscript path, the blocker state, and the next papers moving through the queue."}
                </p>
              </div>
            </div>

            <div className="desk-sync-panel">
              <div className="flex flex-wrap items-center gap-2">
                <StatusChip tone={source === "github" ? "accent" : "neutral"}>
                  {sourceLabel(source)}
                </StatusChip>
                <StatusChip>{formatRelativeTime(snapshotUpdatedAt)}</StatusChip>
              </div>

              <button
                className="desk-button"
                type="button"
                onClick={() => void refreshSnapshot()}
                disabled={refreshing}
              >
                <RefreshCw className={refreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
                Refresh snapshot
              </button>

              <details className="desk-details">
                <summary>GitHub sync</summary>
                <form className="mt-4 space-y-3" onSubmit={(event) => void handleTokenSubmit(event)}>
                  <label className="space-y-2 text-sm text-[var(--muted)]">
                    <span className="block uppercase tracking-[0.14em] text-[11px] text-[var(--muted-strong)]">
                      Personal access token
                    </span>
                    <input
                      className="desk-input"
                      type="password"
                      value={tokenDraft}
                      onChange={(event) => setTokenDraft(event.target.value)}
                      placeholder="Paste token to load docs/command_snapshot.json from GitHub"
                    />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <button className="desk-button" type="submit" disabled={refreshing}>
                      Save and load
                    </button>
                    {githubToken ? (
                      <button
                        className="desk-button desk-button-muted"
                        type="button"
                        onClick={() => void handleUseLocalOnly()}
                        disabled={refreshing}
                      >
                        Use local snapshot
                      </button>
                    ) : null}
                  </div>
                </form>
              </details>
            </div>
          </div>
        </header>

        {errorMessage ? (
          <div className="mt-6 flex items-start gap-3 border border-[var(--danger-line)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger-ink)]">
            <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{errorMessage}</p>
          </div>
        ) : null}

        <main className="space-y-12 py-10">
          <section className="desk-lead-grid">
            <div className="space-y-8 border-b border-[var(--line)] pb-8 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-10">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusChip tone="accent">Current lead manuscript</StatusChip>
                  <StatusChip>{humanize(leadCandidate?.support_status)}</StatusChip>
                  <StatusChip>
                    {summary?.active_count || activeCandidates.length} active drafts
                  </StatusChip>
                </div>

                <div className="space-y-3">
                  <h2 className="desk-title text-3xl leading-tight sm:text-4xl">
                    {leadCandidate?.title || "No lead manuscript emitted"}
                  </h2>
                  <p className="max-w-3xl text-lg leading-8 text-[var(--muted)]">
                    {leadStory}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <a
                  className="desk-button"
                  href={getDraftUrl(leadCandidate)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <FileText className="h-4 w-4" />
                  Open generated draft
                </a>
                <a
                  className="desk-button desk-button-muted"
                  href={getPackUrl(leadCandidate?.pack_key)}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ScrollText className="h-4 w-4" />
                  Open evidence pack
                </a>
                {leadJournal?.homepage ? (
                  <a
                    className="desk-button desk-button-muted"
                    href={leadJournal.homepage}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ArrowUpRight className="h-4 w-4" />
                    Open journal target
                  </a>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {leadSignals.map((signal) => (
                  <div key={signal.label} className="border-t border-[var(--line)] pt-4">
                    <div className="desk-eyebrow">{signal.label}</div>
                    <p className="mt-2 text-base leading-7 text-[var(--ink)]">
                      {signal.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-6 lg:pl-2">
              <article className="border-t border-[var(--line)] pt-4">
                <div className="desk-eyebrow">Current status</div>
                <p className="mt-3 text-lg leading-8 text-[var(--ink)]">
                  {getTaskStatusLine(leadCandidate)}
                </p>
                <div className="mt-4 flex items-center gap-2 text-sm text-[var(--muted)]">
                  <Clock3 className="h-4 w-4" />
                  Task ledger updated {formatRelativeTime(leadCandidate?.task_execution_summary?.updated_at)}
                </div>
              </article>

              <article className="border-t border-[var(--line)] pt-4">
                <div className="desk-eyebrow">Current blocker</div>
                <p className="mt-3 text-lg leading-8 text-[var(--ink)]">
                  {getLeadBlocker(leadCandidate)}
                </p>
              </article>

              <article className="border-t border-[var(--line)] pt-4">
                <div className="desk-eyebrow">System note</div>
                <p className="mt-3 text-base leading-7 text-[var(--muted)]">
                  The system keeps running automatically from the repository snapshot. This desk is only for reading the manuscript state, not steering workflows.
                </p>
              </article>
            </div>
          </section>

          <section className="grid gap-10 lg:grid-cols-[1.2fr_0.85fr]">
            <div className="space-y-4">
              <div className="flex items-end justify-between gap-4 border-b border-[var(--line)] pb-3">
                <div>
                  <div className="desk-eyebrow">Active manuscript drafts</div>
                  <h3 className="mt-2 text-2xl leading-tight text-[var(--ink)]">
                    Papers already in motion.
                  </h3>
                </div>
                <div className="text-sm text-[var(--muted)]">
                  {summary?.active_count || activeCandidates.length} total
                </div>
              </div>

              <ul className="desk-list divide-y divide-transparent">
                {activeCandidates.length ? (
                  activeCandidates.map((candidate: AnyRecord, index: number) => (
                    <ManuscriptRow
                      key={candidate?.candidate_id || candidate?.title || index}
                      candidate={candidate}
                      eyebrow={candidate?.is_active_path ? "Lead path" : `Draft ${index + 1}`}
                      summary={
                        getTaskStatusLine(candidate) +
                        (getLeadBlocker(candidate)
                          ? ` · Blocker: ${getLeadBlocker(candidate)}`
                          : "")
                      }
                      secondaryLinks={[
                        { href: getPackUrl(candidate?.pack_key), label: "Evidence pack" },
                      ]}
                    />
                  ))
                ) : (
                  <li className="desk-empty-state">
                    No active manuscript drafts are attached in the latest snapshot.
                  </li>
                )}
              </ul>
            </div>

            <div className="space-y-4">
              <div className="border-b border-[var(--line)] pb-3">
                <div className="desk-eyebrow">Ready for metadata</div>
                <h3 className="mt-2 text-2xl leading-tight text-[var(--ink)]">
                  Files with enough structure to link out now.
                </h3>
              </div>

              <ul className="desk-list">
                {metadataCandidates.length ? (
                  metadataCandidates.map((candidate: AnyRecord, index: number) => {
                    const journal = getPrimaryJournal(candidate);
                    return (
                      <ManuscriptRow
                        key={candidate?.candidate_id || candidate?.title || index}
                        candidate={candidate}
                        eyebrow="Ready for metadata"
                        summary={getMetadataSummary(candidate)}
                        secondaryLinks={[
                          { href: getPackUrl(candidate?.pack_key), label: "Evidence pack" },
                          ...(journal?.homepage
                            ? [{ href: journal.homepage, label: journal.name }]
                            : []),
                        ]}
                      />
                    );
                  })
                ) : (
                  <li className="desk-empty-state">
                    No manuscript has crossed into metadata prep yet.
                  </li>
                )}
              </ul>
            </div>
          </section>

          <section className="space-y-4 border-t border-[var(--line)] pt-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="desk-eyebrow">Queue and watchlist</div>
                <h3 className="mt-2 text-2xl leading-tight text-[var(--ink)]">
                  Keep the manuscript line readable.
                </h3>
              </div>
              <div className="flex flex-wrap gap-2 text-sm text-[var(--muted)]">
                <span>{summary?.watchlist_count || watchlist.length} watchlist</span>
                <span>·</span>
                <span>{metadataCandidates.length} metadata-ready</span>
                <span>·</span>
                <span>
                  {summary?.ready_for_codex_draft_count || 0} draft-ready
                </span>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              {queueCandidates.length ? (
                queueCandidates.map((candidate: AnyRecord, index: number) => (
                  <article key={candidate?.candidate_id || candidate?.title || index} className="border-t border-[var(--line)] pt-4">
                    <div className="flex items-start justify-between gap-5">
                      <div className="min-w-0 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusChip
                            tone={
                              activeCandidateIds.has(candidate?.candidate_id)
                                ? "accent"
                                : "warning"
                            }
                          >
                            {activeCandidateIds.has(candidate?.candidate_id)
                              ? "Active draft"
                              : "Watchlist"}
                          </StatusChip>
                          <StatusChip>{humanize(candidate?.manuscript_gate_state)}</StatusChip>
                        </div>
                        <a
                          className="desk-link text-xl leading-tight text-[var(--ink)]"
                          href={getPackUrl(candidate?.pack_key)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {candidate?.title || "Untitled manuscript"}
                        </a>
                        <p className="text-sm leading-6 text-[var(--muted)]">
                          {candidate?.top_blocker ||
                            getLeadBlocker(candidate) ||
                            "No blocker named yet."}
                        </p>
                      </div>
                      <ScrollText className="mt-1 h-4 w-4 shrink-0 text-[var(--accent)]" />
                    </div>
                  </article>
                ))
              ) : (
                <div className="desk-empty-state lg:col-span-2">
                  The queue is clear right now. New watchlist items will appear here when the snapshot emits them.
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
