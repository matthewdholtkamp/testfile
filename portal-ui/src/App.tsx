import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clock3,
  ExternalLink,
  FileText,
  KeyRound,
  LayoutDashboard,
  Loader2,
  MessageSquareText,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from "lucide-react";
import { cn } from "./lib/utils";
import fallbackData from "./data.json";

const GITHUB_OWNER = "matthewdholtkamp";
const GITHUB_REPO = "testfile";
const GITHUB_REF = "main";
const GITHUB_APPLY_WORKFLOW = "cockpit_apply_decision.yml";
const GITHUB_CLARIFY_WORKFLOW = "cockpit_clarify_question.yml";
const GITHUB_TOKEN_KEY = "atlas-github-token";

const GITHUB_STATE_FILES = {
  commandSnapshot: "docs/command_snapshot.json",
  directionRegistry: "outputs/state/engine_direction_registry.json",
  decisionLog: "outputs/state/decision_log.jsonl",
  actionStatus: "outputs/state/engine_action_status.json",
  lastApply: "outputs/state/engine_last_apply_response.json",
  lastClarify: "outputs/state/engine_last_clarify_response.json",
};

type AnyRecord = Record<string, any>;
type RemoteState = {
  commandSnapshot: AnyRecord;
  directionRegistry: AnyRecord;
  decisionHistory: AnyRecord[];
  actionStatus: AnyRecord;
  lastApplyResponse: AnyRecord;
  lastClarifyResponse: AnyRecord;
};

type PendingConfirmation = {
  decisionId: string;
  decisionJson: string;
  freeText: string;
  note: string;
  explanation: string;
  summary: string;
};

type BoardRuntimeState = {
  mismatch: boolean;
  mismatchReasons: string[];
  snapshotAge: string;
  liveSteeringAge: string;
  liveActionAge: string;
  steeringAwareAutomation: boolean;
  liveActionsEnabled: boolean;
};

type DispatchState = "idle" | "working" | "success" | "error";

function getInjectedPayload(): AnyRecord | null {
  const globalValue = (
    window as typeof window & { EMBEDDED_PAYLOAD?: AnyRecord }
  ).EMBEDDED_PAYLOAD;
  return globalValue && typeof globalValue === "object" ? globalValue : null;
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function normalizeText(value: unknown): string {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function createRequestId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function decodeBase64(value: string): string {
  return window.atob(value.replace(/\n/g, ""));
}

function buildDecisionList(payload: AnyRecord | null): AnyRecord[] {
  if (!payload) return [];
  const primary = payload.primary_decision ? [payload.primary_decision] : [];
  const secondary = Array.isArray(payload.secondary_decisions)
    ? payload.secondary_decisions
    : [];
  return primary
    .concat(secondary)
    .filter((decision) => decision && decision.decision_id);
}

function buildSelectedOptions(
  payload: AnyRecord | null,
  previous: Record<string, string> = {},
): Record<string, string> {
  const next = { ...previous };
  for (const decision of buildDecisionList(payload)) {
    if (!next[decision.decision_id]) {
      next[decision.decision_id] =
        decision.recommended_option_id || decision.options?.[0]?.id || "";
    }
  }
  return next;
}

function formatAge(value: unknown): string {
  if (!value) return "Not available";
  const text = String(value);
  const parsed = Date.parse(text);
  if (Number.isNaN(parsed)) return text;
  const diffMs = Date.now() - parsed;
  if (diffMs < 60_000) return "Just now";
  const diffMinutes = Math.floor(diffMs / 60_000);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function freezeDecisionPacket(decision: AnyRecord | null): string {
  if (!decision) return "";
  try {
    return JSON.stringify(decision);
  } catch {
    return "";
  }
}

function getPackUrl(packKey: string): string {
  return `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/tree/${GITHUB_REF}/outputs/manuscripts/${packKey}`;
}

function getTaskSummary(candidate: AnyRecord): string {
  const counts = candidate?.task_execution_summary?.status_counts || {};
  const parts = [
    counts.running ? `${counts.running} running` : "",
    counts.blocked ? `${counts.blocked} blocked` : "",
    counts.satisfied ? `${counts.satisfied} satisfied` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No manuscript tasks emitted yet";
}

function getTopBlocker(candidate: AnyRecord): string {
  const blockedTask = Array.isArray(candidate?.task_ledger)
    ? candidate.task_ledger.find((task: AnyRecord) => task.status === "blocked")
    : null;
  if (blockedTask?.execution_note) return blockedTask.execution_note;
  if (blockedTask?.rationale) return blockedTask.rationale;
  return (
    candidate?.journal_targets?.primary?.requirements?.reasons?.[0] ||
    candidate?.source_row?.blockers ||
    "No active blocker named yet."
  );
}

function journalStateLabel(candidate: AnyRecord): string {
  return candidate?.journal_targets?.primary?.requirements?.checked
    ? "Verified requirements"
    : "Shortlist only";
}

function overlayPayloadWithGitHubState(
  basePayload: AnyRecord | null,
  remoteState: RemoteState,
): AnyRecord {
  const payload: AnyRecord = deepClone(
    (basePayload || getInjectedPayload() || fallbackData) as AnyRecord,
  );
  const registry = remoteState.directionRegistry || {};
  const history = Array.isArray(remoteState.decisionHistory)
    ? remoteState.decisionHistory.slice().reverse().slice(0, 8)
    : [];
  const actionStatus = remoteState.actionStatus || null;

  payload.board_state = payload.board_state || {};
  payload.control_state = payload.control_state || {};
  payload.control_state.actionable = true;
  payload.control_state.preset_questions = payload.control_state
    .preset_questions || [
    "What have we discovered so far?",
    "Why is this recommended?",
    "What happens if I choose the second option?",
    "What paper story is emerging?",
  ];

  if (registry.active_path_label) {
    payload.current_direction = {
      label: registry.active_path_label,
      reason:
        registry.active_direction_reason ||
        payload.current_direction?.reason ||
        payload.program_status?.current_direction_line ||
        "",
    };
  }
  if (registry.active_path_id) {
    payload.board_state.active_decision_id = registry.active_path_id;
    payload.board_state.active_decision_label =
      registry.active_path_label ||
      payload.board_state.active_decision_label ||
      "";
  }
  if (registry.last_updated) {
    payload.board_state.steering_registry_last_updated = registry.last_updated;
  }
  if (registry.current_manuscript_candidate?.title) {
    payload.goal_progress = payload.goal_progress || {};
    payload.goal_progress.current_manuscript_candidate =
      registry.current_manuscript_candidate;
  }
  if (registry.next_paper_opportunity?.title) {
    payload.goal_progress = payload.goal_progress || {};
    payload.goal_progress.next_paper_opportunity =
      registry.next_paper_opportunity;
  }
  if (history.length) {
    payload.decision_history = history;
  }
  if (actionStatus) {
    payload.live_action_status = actionStatus;
    payload.board_state.action_status_timestamp =
      actionStatus.timestamp ||
      payload.board_state.action_status_timestamp ||
      "";
  }
  return payload;
}

function computeBoardRuntimeState(
  payload: AnyRecord | null,
  remoteState: RemoteState | null,
  controlMode: "snapshot" | "github",
): BoardRuntimeState {
  const boardState = payload?.board_state || {};
  const registry = remoteState?.directionRegistry || {};
  const liveAction =
    remoteState?.actionStatus || payload?.live_action_status || {};
  const visibleIds = Array.isArray(boardState.visible_decision_ids)
    ? boardState.visible_decision_ids.map(normalizeText)
    : buildDecisionList(payload).map((decision) =>
        normalizeText(decision.decision_id),
      );
  const publishedDirection = normalizeText(payload?.current_direction?.label);
  const liveDirection = normalizeText(registry.active_path_label);
  const liveActiveId = normalizeText(registry.active_path_id);
  const mismatchReasons: string[] = [];

  if (controlMode === "github") {
    if (
      publishedDirection &&
      liveDirection &&
      publishedDirection !== liveDirection
    ) {
      mismatchReasons.push(
        `Published direction is ${payload?.current_direction?.label || "unknown"}, but live steering says ${registry.active_path_label || "unknown"}.`,
      );
    }
    if (
      liveActiveId &&
      visibleIds.length &&
      !visibleIds.includes(liveActiveId)
    ) {
      mismatchReasons.push(
        "The live active decision is not visible in the published three-card slate.",
      );
    }
  }

  return {
    mismatch: mismatchReasons.length > 0,
    mismatchReasons,
    snapshotAge: formatAge(boardState.snapshot_generated_at),
    liveSteeringAge: formatAge(
      boardState.steering_registry_last_updated || registry.last_updated,
    ),
    liveActionAge: formatAge(
      boardState.action_status_timestamp || liveAction.timestamp,
    ),
    steeringAwareAutomation: Boolean(boardState.steering_aware_automation),
    liveActionsEnabled:
      controlMode === "github" && mismatchReasons.length === 0,
  };
}

async function fetchLocalSnapshot(): Promise<AnyRecord> {
  const response = await fetch(`./command_snapshot.json?v=${Date.now()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Could not load command snapshot (${response.status}).`);
  }
  return response.json();
}

async function githubApi(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers || {});
  headers.set("Accept", "application/vnd.github+json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`https://api.github.com${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.message || `GitHub API error (${response.status})`,
    );
  }
  return response;
}

async function fetchGitHubJson(
  token: string,
  path: string,
  fallbackValue: AnyRecord | null = null,
): Promise<AnyRecord> {
  try {
    const response = await githubApi(
      token,
      `/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/contents/${path}?ref=${encodeURIComponent(GITHUB_REF)}`,
    );
    const data = await response.json();
    return JSON.parse(decodeBase64(data.content));
  } catch (error) {
    if (fallbackValue !== null) return fallbackValue;
    throw error;
  }
}

async function fetchGitHubJsonl(
  token: string,
  path: string,
  fallbackValue: AnyRecord[] = [],
): Promise<AnyRecord[]> {
  try {
    const response = await githubApi(
      token,
      `/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/contents/${path}?ref=${encodeURIComponent(GITHUB_REF)}`,
    );
    const data = await response.json();
    return decodeBase64(data.content)
      .split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch {
    return fallbackValue;
  }
}

async function loadGitHubRemoteState(token: string): Promise<RemoteState> {
  const [
    commandSnapshot,
    directionRegistry,
    decisionHistory,
    actionStatus,
    lastApplyResponse,
    lastClarifyResponse,
  ] = await Promise.all([
    fetchGitHubJson(token, GITHUB_STATE_FILES.commandSnapshot, {}),
    fetchGitHubJson(token, GITHUB_STATE_FILES.directionRegistry, {}),
    fetchGitHubJsonl(token, GITHUB_STATE_FILES.decisionLog, []),
    fetchGitHubJson(token, GITHUB_STATE_FILES.actionStatus, {}),
    fetchGitHubJson(token, GITHUB_STATE_FILES.lastApply, {}),
    fetchGitHubJson(token, GITHUB_STATE_FILES.lastClarify, {}),
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

async function dispatchGitHubWorkflow(
  token: string,
  workflowFile: string,
  inputs: Record<string, string>,
): Promise<void> {
  await githubApi(
    token,
    `/repos/${encodeURIComponent(GITHUB_OWNER)}/${encodeURIComponent(GITHUB_REPO)}/actions/workflows/${encodeURIComponent(workflowFile)}/dispatches`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref: GITHUB_REF,
        inputs,
      }),
    },
  );
}

async function waitForGitHubResponse(
  token: string,
  path: string,
  requestId: string,
  timeoutMs = 120000,
): Promise<AnyRecord> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const response = await fetchGitHubJson(token, path, {});
    if (response && response.request_id === requestId) {
      return response;
    }
    await sleep(4000);
  }
  throw new Error(
    "GitHub control timed out while waiting for the workflow response.",
  );
}

function statusTone(score: number): string {
  if (score >= 3) return "bg-emerald-400";
  if (score >= 2) return "bg-amber-300";
  return "bg-slate-500";
}

function ScoreRail({
  label,
  score,
  percent,
}: {
  label: string;
  score?: number;
  percent?: number;
}) {
  const safeScore = typeof score === "number" ? score : 0;
  const safePercent =
    typeof percent === "number" ? percent : (safeScore / 4) * 100;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-[#9fb4c8]">
        <span>{label}</span>
        <span className="font-bold text-white">{safeScore}/4</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/8">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            statusTone(safeScore),
          )}
          style={{ width: `${safePercent}%` }}
        />
      </div>
    </div>
  );
}

function StatusPill({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "muted" | "accent" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    muted: "bg-white/6 text-[#9fb4c8] border-white/10",
    accent: "bg-[#9fd7bd]/12 text-[#9fd7bd] border-[#9fd7bd]/20",
    success: "bg-emerald-400/12 text-emerald-200 border-emerald-300/20",
    warning: "bg-amber-300/12 text-amber-100 border-amber-200/20",
    danger: "bg-rose-300/12 text-rose-100 border-rose-200/20",
  }[tone];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em]",
        toneClass,
      )}
    >
      {children}
    </span>
  );
}

export default function App() {
  const [basePayload, setBasePayload] = useState<AnyRecord>(
    getInjectedPayload() || fallbackData,
  );
  const [payload, setPayload] = useState<AnyRecord>(
    getInjectedPayload() || fallbackData,
  );
  const [remoteState, setRemoteState] = useState<RemoteState | null>(null);
  const [controlMode, setControlMode] = useState<"snapshot" | "github">(
    "snapshot",
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [activeDecisionId, setActiveDecisionId] = useState("");
  const [selectedOptions, setSelectedOptions] = useState<
    Record<string, string>
  >({});
  const [actionNote, setActionNote] = useState("");
  const [freeTextInstruction, setFreeTextInstruction] = useState("");
  const [pendingConfirmation, setPendingConfirmation] =
    useState<PendingConfirmation | null>(null);

  const [githubToken, setGithubToken] = useState("");
  const [tokenDraft, setTokenDraft] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [dispatchState, setDispatchState] = useState<DispatchState>("idle");
  const [actionMessage, setActionMessage] = useState("");

  const [question, setQuestion] = useState("");
  const [clarifyState, setClarifyState] = useState<DispatchState>("idle");
  const [clarifyResponse, setClarifyResponse] = useState<AnyRecord | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      setLoading(true);
      try {
        const snapshot = await fetchLocalSnapshot().catch(
          () => getInjectedPayload() || fallbackData,
        );
        if (cancelled) return;
        setBasePayload(snapshot);
        setPayload(snapshot);
        setActionMessage(
          "Using the published command snapshot. Connect GitHub control to apply decisions from the page.",
        );
        const savedToken = window.localStorage.getItem(GITHUB_TOKEN_KEY) || "";
        setGithubToken(savedToken);
        setTokenDraft(savedToken);
        if (savedToken) {
          await refreshGitHubState(savedToken, snapshot, cancelled);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void initialize();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const decisions = buildDecisionList(payload);
    if (!decisions.length) {
      setActiveDecisionId("");
      return;
    }
    setSelectedOptions((previous) => buildSelectedOptions(payload, previous));
    setActiveDecisionId((previous) =>
      decisions.some((decision) => decision.decision_id === previous)
        ? previous
        : decisions[0].decision_id,
    );
  }, [payload]);

  const decisions = useMemo(() => buildDecisionList(payload), [payload]);
  const activeDecision = useMemo(
    () =>
      decisions.find((decision) => decision.decision_id === activeDecisionId) ||
      decisions[0] ||
      null,
    [decisions, activeDecisionId],
  );
  const otherDecisions = decisions.filter(
    (decision) => decision.decision_id !== activeDecision?.decision_id,
  );
  const runtimeState = useMemo(
    () => computeBoardRuntimeState(payload, remoteState, controlMode),
    [payload, remoteState, controlMode],
  );
  const manuscriptQueue = payload.manuscript_queue || {
    active_candidates: [],
    watchlist: [],
    publication_tracker: [],
  };
  const presetQuestions = payload.control_state?.preset_questions || [];
  const publishedCandidate =
    payload.goal_progress?.current_manuscript_candidate;
  const boardModeLabel =
    controlMode === "github" ? "GitHub control" : "Published snapshot";

  async function refreshGitHubState(
    token: string,
    preferredBase?: AnyRecord,
    cancelled = false,
  ) {
    setRefreshing(true);
    try {
      const remote = await loadGitHubRemoteState(token);
      if (cancelled) return;
      const nextBase = remote.commandSnapshot?.primary_decision
        ? remote.commandSnapshot
        : preferredBase || basePayload;
      const overlaid = overlayPayloadWithGitHubState(nextBase, remote);
      setBasePayload(nextBase);
      setRemoteState(remote);
      setPayload(overlaid);
      setControlMode("github");
      const runtime = computeBoardRuntimeState(overlaid, remote, "github");
      setActionMessage(
        runtime.mismatch
          ? "GitHub control is connected, but the published board is behind the live steering state. Wait for publish or refresh before applying a new action."
          : "GitHub control is connected. Decisions and clarify questions now dispatch through GitHub Actions.",
      );
    } catch (error) {
      if (!cancelled) {
        setRemoteState(null);
        setControlMode("snapshot");
        setActionMessage(
          error instanceof Error
            ? error.message
            : "GitHub control could not be loaded. Staying on the published snapshot.",
        );
      }
    } finally {
      if (!cancelled) {
        setRefreshing(false);
      }
    }
  }

  async function handleRefresh() {
    if (githubToken) {
      await refreshGitHubState(githubToken);
      return;
    }
    setRefreshing(true);
    try {
      const snapshot = await fetchLocalSnapshot().catch(
        () => getInjectedPayload() || fallbackData,
      );
      setBasePayload(snapshot);
      setPayload(snapshot);
      setRemoteState(null);
      setControlMode("snapshot");
      setActionMessage("Published snapshot refreshed.");
    } finally {
      setRefreshing(false);
    }
  }

  function handleSaveToken() {
    const nextToken = tokenDraft.trim();
    if (!nextToken) return;
    setGithubToken(nextToken);
    window.localStorage.setItem(GITHUB_TOKEN_KEY, nextToken);
    setSettingsOpen(false);
    void refreshGitHubState(nextToken);
  }

  function handleDisconnectGitHub() {
    window.localStorage.removeItem(GITHUB_TOKEN_KEY);
    setGithubToken("");
    setTokenDraft("");
    setRemoteState(null);
    setControlMode("snapshot");
    setPayload(basePayload);
    setActionMessage(
      "GitHub control disconnected. The page is back to snapshot-only mode.",
    );
  }

  async function handleApplySelectedOption() {
    if (!activeDecision) return;
    if (!githubToken) {
      setSettingsOpen(true);
      return;
    }
    if (!runtimeState.liveActionsEnabled) {
      setActionMessage(
        "Live actions are disabled while the board is out of sync. Refresh and wait for publish before applying another change.",
      );
      return;
    }

    const optionId = selectedOptions[activeDecision.decision_id];
    const selectedOption = activeDecision.options?.find(
      (option: AnyRecord) => option.id === optionId,
    );
    if (!selectedOption) return;

    setDispatchState("working");
    setActionMessage("Dispatching the selected option through GitHub Actions…");
    setPendingConfirmation(null);

    try {
      const requestId = createRequestId("apply");
      await dispatchGitHubWorkflow(githubToken, GITHUB_APPLY_WORKFLOW, {
        request_id: requestId,
        decision_id: activeDecision.decision_id,
        decision_json: freezeDecisionPacket(activeDecision),
        option_id: selectedOption.id,
        free_text: "",
        note: actionNote,
        confirmed: "false",
      });
      const result = await waitForGitHubResponse(
        githubToken,
        GITHUB_STATE_FILES.lastApply,
        requestId,
      );
      if (result?.ok === false) {
        throw new Error(
          result.error_message ||
            result.error ||
            "The decision could not be applied.",
        );
      }
      await refreshGitHubState(githubToken, result.payload || payload);
      setDispatchState("success");
      setActionNote("");
      setFreeTextInstruction("");
      setActionMessage(
        result?.triggered_action?.message || "Decision applied successfully.",
      );
    } catch (error) {
      setDispatchState("error");
      setActionMessage(
        error instanceof Error
          ? error.message
          : "The decision could not be applied.",
      );
    }
  }

  async function handleApplyFreeText(
    confirmed = false,
    pending = pendingConfirmation,
  ) {
    if (!activeDecision || !githubToken) {
      setSettingsOpen(true);
      return;
    }
    const instruction = confirmed
      ? pending?.freeText || ""
      : freeTextInstruction.trim();
    const note = confirmed ? pending?.note || "" : actionNote;
    if (!instruction) return;
    if (!runtimeState.liveActionsEnabled) {
      setActionMessage(
        "Live actions are disabled while the board is out of sync. Refresh and wait for publish before applying another change.",
      );
      return;
    }

    setDispatchState("working");
    setActionMessage(
      confirmed
        ? "Applying the confirmed interpretation…"
        : "Interpreting and dispatching your instruction…",
    );

    try {
      const requestId = createRequestId("apply");
      await dispatchGitHubWorkflow(githubToken, GITHUB_APPLY_WORKFLOW, {
        request_id: requestId,
        decision_id: confirmed
          ? pending?.decisionId || activeDecision.decision_id
          : activeDecision.decision_id,
        decision_json: confirmed
          ? pending?.decisionJson || freezeDecisionPacket(activeDecision)
          : freezeDecisionPacket(activeDecision),
        option_id: "",
        free_text: instruction,
        note,
        confirmed: confirmed ? "true" : "false",
      });
      const result = await waitForGitHubResponse(
        githubToken,
        GITHUB_STATE_FILES.lastApply,
        requestId,
      );
      if (result?.ok === false) {
        throw new Error(
          result.error_message ||
            result.error ||
            "The instruction could not be applied.",
        );
      }
      if (result?.needs_confirmation && !confirmed) {
        const proposed = result?.interpreted_decision?.matched_option_id || "";
        if (proposed) {
          setSelectedOptions((previous) => ({
            ...previous,
            [activeDecision.decision_id]: proposed,
          }));
        }
        setPendingConfirmation({
          decisionId: activeDecision.decision_id,
          decisionJson: freezeDecisionPacket(activeDecision),
          freeText: instruction,
          note,
          explanation:
            result?.interpreted_decision?.explanation ||
            "The machine needs confirmation before acting on that write-in.",
          summary: proposed
            ? `The board thinks you mean “${proposed}.”`
            : "The board could not map that instruction cleanly enough to act without confirmation.",
        });
        setDispatchState("idle");
        setActionMessage(
          result?.interpreted_decision?.explanation ||
            "The instruction needs confirmation before it can be applied.",
        );
        return;
      }
      await refreshGitHubState(githubToken, result.payload || payload);
      setPendingConfirmation(null);
      setFreeTextInstruction("");
      setActionNote("");
      setDispatchState("success");
      setActionMessage(
        result?.triggered_action?.message ||
          "Instruction applied successfully.",
      );
    } catch (error) {
      setDispatchState("error");
      setActionMessage(
        error instanceof Error
          ? error.message
          : "The instruction could not be applied.",
      );
    }
  }

  async function handleClarify(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed) return;
    if (!githubToken) {
      setSettingsOpen(true);
      return;
    }

    setClarifyState("working");
    setClarifyResponse({
      answer: "Working through the current repo state…",
      evidence_chain: [
        "The clarify workflow is running through GitHub Actions.",
      ],
      implication:
        "This answer will stay tied to the current decision context.",
      recommended_follow_up:
        "Use the result to decide whether you want to apply the current option or shift lanes.",
    });

    try {
      const requestId = createRequestId("clarify");
      await dispatchGitHubWorkflow(githubToken, GITHUB_CLARIFY_WORKFLOW, {
        request_id: requestId,
        question: trimmed,
        decision_id: activeDecision?.decision_id || "",
      });
      const result = await waitForGitHubResponse(
        githubToken,
        GITHUB_STATE_FILES.lastClarify,
        requestId,
      );
      setClarifyResponse(result);
      setClarifyState("success");
      await refreshGitHubState(githubToken);
    } catch (error) {
      setClarifyState("error");
      setClarifyResponse({
        answer:
          error instanceof Error
            ? error.message
            : "The clarify workflow could not complete.",
        evidence_chain: [
          "GitHub control did not return a clarification response in time.",
        ],
        implication: "The decision state did not change.",
        recommended_follow_up:
          "Try again after checking the Actions tab or reconnecting GitHub control.",
      });
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0b1117] text-[#edf4fb]">
        <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-[#9fb4c8]">
          <Loader2 className="h-5 w-5 animate-spin text-[#9fd7bd]" />
          Loading command cockpit…
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b1117] px-6 py-8 text-[#edf4fb] md:px-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="flex flex-col gap-5 border-b border-white/8 pb-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <StatusPill tone={controlMode === "github" ? "success" : "muted"}>
                {boardModeLabel}
              </StatusPill>
              <StatusPill
                tone={
                  runtimeState.steeringAwareAutomation ? "accent" : "warning"
                }
              >
                {runtimeState.steeringAwareAutomation
                  ? "Steering-aware automation"
                  : "Snapshot only"}
              </StatusPill>
              {runtimeState.mismatch && (
                <StatusPill tone="danger">Board mismatch</StatusPill>
              )}
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-white via-[#edf4fb] to-[#9fd7bd] bg-clip-text text-3xl font-extrabold tracking-tight text-transparent md:text-4xl">
                TBI Engine Command Cockpit
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-[#9fb4c8]">
                The engine state is still coming from the repo. This frontend is
                only the presentation layer, now wired directly to the live
                command snapshot and GitHub control path.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => void handleRefresh()}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:border-[#9fd7bd]/40 hover:bg-white/10"
            >
              {refreshing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh state
            </button>
            {githubToken ? (
              <button
                onClick={handleDisconnectGitHub}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:border-rose-200/40 hover:bg-rose-200/10"
              >
                <X className="h-4 w-4" />
                Disconnect GitHub control
              </button>
            ) : (
              <button
                onClick={() => setSettingsOpen(true)}
                className="inline-flex items-center gap-2 rounded-2xl border border-[#9fd7bd]/20 bg-[#9fd7bd]/10 px-4 py-3 text-sm font-semibold text-[#9fd7bd] transition hover:bg-[#9fd7bd]/16"
              >
                <KeyRound className="h-4 w-4" />
                Connect GitHub control
              </button>
            )}
          </div>
        </header>

        <div className="grid gap-8 xl:grid-cols-[1.45fr_0.75fr]">
          <main className="space-y-8">
            <section className="overflow-hidden rounded-[28px] border border-[#9fd7bd]/18 bg-gradient-to-br from-[#121c26] via-[#172430] to-[#121c26] p-8 shadow-[0_28px_80px_rgba(0,0,0,0.35)]">
              <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-5">
                  <div className="flex flex-wrap items-center gap-3 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                    <span>Program status</span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 tracking-[0.18em] text-[#9fb4c8]">
                      Snapshot age {runtimeState.snapshotAge}
                    </span>
                    {controlMode === "github" && (
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 tracking-[0.18em] text-[#9fb4c8]">
                        Live steering {runtimeState.liveSteeringAge}
                      </span>
                    )}
                  </div>
                  <div>
                    <h2 className="max-w-3xl text-3xl font-bold leading-tight text-white md:text-4xl">
                      {payload.program_status?.line}
                    </h2>
                    <p className="mt-4 max-w-3xl text-base leading-8 text-[#9fb4c8]">
                      {payload.program_status?.paragraph}
                    </p>
                  </div>

                  {runtimeState.mismatch && (
                    <div className="rounded-2xl border border-rose-200/20 bg-rose-200/8 p-5">
                      <div className="flex items-center gap-2 text-sm font-bold text-rose-100">
                        <ShieldAlert className="h-4 w-4" />
                        Board mismatch detected
                      </div>
                      <ul className="mt-3 space-y-2 text-sm leading-6 text-[#d9e4ef]">
                        {runtimeState.mismatchReasons.map((reason) => (
                          <li key={reason} className="flex gap-2">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-rose-200" />
                            <span>{reason}</span>
                          </li>
                        ))}
                        <li className="flex gap-2">
                          <span className="mt-2 h-1.5 w-1.5 rounded-full bg-rose-200" />
                          <span>
                            Hard refresh the page, reconnect GitHub control if
                            needed, and wait for the publish workflow to finish.
                          </span>
                        </li>
                      </ul>
                    </div>
                  )}

                  <div className="rounded-2xl border border-white/10 bg-black/15 p-5">
                    <div className="text-xs font-bold uppercase tracking-[0.22em] text-[#9fd7bd]">
                      Current direction
                    </div>
                    <div className="mt-3 text-xl font-bold text-white">
                      {payload.current_direction?.label ||
                        "No active direction emitted"}
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                      {payload.current_direction?.reason ||
                        payload.program_status?.current_direction_line ||
                        "No direction rationale is available in the current snapshot."}
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-white/10 bg-black/15 p-5">
                    <div className="text-xs font-bold uppercase tracking-[0.22em] text-[#9fd7bd]">
                      Board health
                    </div>
                    <div className="mt-4 space-y-4">
                      <div>
                        <div className="text-sm text-[#9fb4c8]">
                          Live action age
                        </div>
                        <div className="mt-1 text-lg font-semibold text-white">
                          {runtimeState.liveActionAge}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-[#9fb4c8]">
                          Action state
                        </div>
                        <div className="mt-1 text-lg font-semibold text-white">
                          {runtimeState.liveActionsEnabled
                            ? "Live actions enabled"
                            : "Read-only until sync is clean"}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-black/15 p-5">
                    <div className="text-xs font-bold uppercase tracking-[0.22em] text-[#9fd7bd]">
                      Current manuscript target
                    </div>
                    <div className="mt-3 text-lg font-semibold text-white">
                      {publishedCandidate?.title ||
                        "No manuscript target emitted"}
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                      {publishedCandidate?.story ||
                        "The steering registry has not attached a manuscript story to this path yet."}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <section className="space-y-5 rounded-[28px] border border-white/10 bg-[#121c26] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.25)]">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <div className="flex items-center gap-3 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                    <BookOpen className="h-4 w-4" />
                    Manuscript queue
                  </div>
                  <h3 className="mt-3 text-2xl font-bold text-white">
                    Output lanes forming under the current engine state
                  </h3>
                  <p className="mt-2 max-w-3xl text-sm leading-7 text-[#9fb4c8]">
                    The queue is reading directly from Phase 8. It shows which
                    papers are active now, what journal each one is leaning
                    toward, and what is still blocking the pack from becoming
                    draft-ready.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
                  <div className="text-xs uppercase tracking-[0.22em] text-[#9fb4c8]">
                    Queue status
                  </div>
                  <div className="mt-1 text-lg font-bold text-white">
                    {manuscriptQueue.summary?.active_count || 0} active ·{" "}
                    {manuscriptQueue.summary?.watchlist_count || 0} watchlist ·{" "}
                    {manuscriptQueue.summary?.ready_for_codex_draft_count || 0}{" "}
                    draft-ready
                  </div>
                </div>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                {(manuscriptQueue.active_candidates || []).map(
                  (candidate: AnyRecord) => (
                    <article
                      key={candidate.candidate_id}
                      className="rounded-[24px] border border-[#9fd7bd]/16 bg-gradient-to-b from-[#172430] to-[#121c26] p-6"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusPill
                              tone={
                                candidate.is_active_path ? "success" : "accent"
                              }
                            >
                              {candidate.is_active_path
                                ? "Active path"
                                : "Candidate"}
                            </StatusPill>
                            <StatusPill
                              tone={
                                journalStateLabel(candidate) ===
                                "Verified requirements"
                                  ? "success"
                                  : "warning"
                              }
                            >
                              {journalStateLabel(candidate)}
                            </StatusPill>
                          </div>
                          <h4 className="mt-4 text-xl font-bold text-white">
                            {candidate.title}
                          </h4>
                          <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                            Gate state:{" "}
                            <span className="font-semibold text-white">
                              {candidate.manuscript_gate_state || "not scored"}
                            </span>
                          </p>
                        </div>
                        <a
                          href={getPackUrl(candidate.pack_key)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:border-[#9fd7bd]/40 hover:bg-white/10"
                        >
                          Open pack
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </div>

                      <div className="mt-6 space-y-4">
                        <ScoreRail
                          label="Scientific strength"
                          score={candidate.scientific_strength_bar?.score}
                          percent={candidate.scientific_strength_bar?.percent}
                        />
                        <ScoreRail
                          label="Journal fit"
                          score={candidate.journal_fit_bar?.score}
                          percent={candidate.journal_fit_bar?.percent}
                        />
                        <ScoreRail
                          label="Draft readiness"
                          score={candidate.draft_readiness_bar?.score}
                          percent={candidate.draft_readiness_bar?.percent}
                        />
                      </div>

                      <div className="mt-6 grid gap-4 md:grid-cols-2">
                        <div className="rounded-2xl border border-white/8 bg-black/15 p-4">
                          <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fb4c8]">
                            Primary journal
                          </div>
                          <div className="mt-2 text-base font-semibold text-white">
                            {candidate.journal_targets?.primary?.journal
                              ?.name || "Not selected"}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-[#9fb4c8]">
                            {candidate.draft_status ||
                              "No draft status emitted."}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-white/8 bg-black/15 p-4">
                          <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fb4c8]">
                            Task summary
                          </div>
                          <div className="mt-2 text-base font-semibold text-white">
                            {getTaskSummary(candidate)}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-[#9fb4c8]">
                            Last pack refresh{" "}
                            {candidate.last_pack_refresh || "unknown"}.
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-rose-200/12 bg-rose-200/5 p-4">
                        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-rose-100">
                          <ShieldAlert className="h-4 w-4" />
                          Top blocker
                        </div>
                        <p className="mt-2 text-sm leading-7 text-[#d9e4ef]">
                          {getTopBlocker(candidate)}
                        </p>
                      </div>

                      <div className="mt-4 rounded-2xl border border-white/8 bg-black/15 p-4 text-sm text-[#9fb4c8]">
                        Evidence bundle:{" "}
                        {candidate.evidence_bundle_summary?.reference_count ||
                          0}{" "}
                        references ·{" "}
                        {candidate.evidence_bundle_summary?.claim_count || 0}{" "}
                        claims ·{" "}
                        {candidate.evidence_bundle_summary?.figure_count || 0}{" "}
                        figures ·{" "}
                        {candidate.evidence_bundle_summary
                          ?.section_packet_count || 0}{" "}
                        section packets.
                      </div>
                    </article>
                  ),
                )}
              </div>

              <details className="rounded-[24px] border border-white/10 bg-black/10 p-5">
                <summary className="cursor-pointer list-none text-sm font-bold uppercase tracking-[0.22em] text-[#9fd7bd]">
                  Watchlist
                </summary>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {(manuscriptQueue.watchlist || []).map(
                    (candidate: AnyRecord) => (
                      <div
                        key={candidate.candidate_id}
                        className="rounded-2xl border border-white/8 bg-[#172430]/70 p-5"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <StatusPill tone="muted">Watchlist</StatusPill>
                          <StatusPill
                            tone={
                              journalStateLabel(candidate) ===
                              "Verified requirements"
                                ? "success"
                                : "warning"
                            }
                          >
                            {journalStateLabel(candidate)}
                          </StatusPill>
                        </div>
                        <h4 className="mt-4 text-lg font-semibold text-white">
                          {candidate.title}
                        </h4>
                        <p className="mt-2 text-sm leading-6 text-[#9fb4c8]">
                          Primary journal:{" "}
                          {candidate.journal_targets?.primary?.journal?.name ||
                            "Not selected"}
                          .
                        </p>
                        <div className="mt-4 space-y-3">
                          <ScoreRail
                            label="Scientific strength"
                            score={candidate.scientific_strength_bar?.score}
                            percent={candidate.scientific_strength_bar?.percent}
                          />
                          <ScoreRail
                            label="Journal fit"
                            score={candidate.journal_fit_bar?.score}
                            percent={candidate.journal_fit_bar?.percent}
                          />
                          <ScoreRail
                            label="Draft readiness"
                            score={candidate.draft_readiness_bar?.score}
                            percent={candidate.draft_readiness_bar?.percent}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </details>

              <details className="rounded-[24px] border border-white/10 bg-black/10 p-5">
                <summary className="cursor-pointer list-none text-sm font-bold uppercase tracking-[0.22em] text-[#9fd7bd]">
                  Publication tracker
                </summary>
                <div className="mt-4 space-y-3 text-sm text-[#9fb4c8]">
                  {(manuscriptQueue.publication_tracker || []).length ? (
                    (manuscriptQueue.publication_tracker || []).map(
                      (item: AnyRecord) => (
                        <div
                          key={`${item.candidate_id}-${item.status || "status"}`}
                          className="rounded-2xl border border-white/8 bg-[#172430]/70 p-4"
                        >
                          <div className="font-semibold text-white">
                            {item.title || item.candidate_id}
                          </div>
                          <div className="mt-1">
                            {item.status || "Status not set yet"}
                          </div>
                        </div>
                      ),
                    )
                  ) : (
                    <div className="rounded-2xl border border-white/8 bg-[#172430]/70 p-4">
                      No manuscripts have been moved into the submission tracker
                      yet. Once a paper leaves the active queue, it will show
                      here with its manual publication status.
                    </div>
                  )}
                </div>
              </details>
            </section>

            {activeDecision && (
              <section className="overflow-hidden rounded-[28px] border border-[#9fd7bd]/18 bg-gradient-to-b from-[#121c26] to-[#172430] shadow-[0_24px_70px_rgba(0,0,0,0.28)]">
                <div className="border-b border-white/8 px-8 py-6">
                  <div className="flex flex-wrap items-center gap-3 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                    <LayoutDashboard className="h-4 w-4" />
                    Active decision
                    <StatusPill tone="accent">
                      {activeDecision.decision_family_label}
                    </StatusPill>
                    <StatusPill
                      tone={
                        activeDecision.support_status === "supported"
                          ? "success"
                          : "warning"
                      }
                    >
                      {activeDecision.support_status || "not specified"}
                    </StatusPill>
                  </div>
                  <h3 className="mt-4 text-2xl font-bold text-white md:text-3xl">
                    {activeDecision.title}
                  </h3>
                  <p className="mt-3 max-w-4xl text-base leading-8 text-[#9fb4c8]">
                    {activeDecision.human_question}
                  </p>
                </div>

                <div className="grid gap-6 px-8 py-8 lg:grid-cols-2">
                  <div className="rounded-2xl border border-[#9fd7bd]/15 bg-[#9fd7bd]/6 p-5">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-[#9fd7bd]">
                      <CheckCircle2 className="h-4 w-4" />
                      What we know
                    </div>
                    <ul className="mt-4 space-y-3 text-sm leading-7 text-[#d9e4ef]">
                      {(activeDecision.what_we_know || []).map(
                        (item: string) => (
                          <li key={item} className="flex gap-3">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#9fd7bd]" />
                            <span>{item}</span>
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                  <div className="rounded-2xl border border-amber-200/15 bg-amber-200/5 p-5">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-amber-100">
                      <ShieldAlert className="h-4 w-4" />
                      What is uncertain
                    </div>
                    <ul className="mt-4 space-y-3 text-sm leading-7 text-[#d9e4ef]">
                      {(activeDecision.what_is_uncertain || []).map(
                        (item: string) => (
                          <li key={item} className="flex gap-3">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-amber-200" />
                            <span>{item}</span>
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                </div>

                <div className="space-y-4 px-8 pb-8">
                  <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fd7bd]">
                    Choose an option
                  </div>
                  {(activeDecision.options || []).map((option: AnyRecord) => {
                    const selected =
                      selectedOptions[activeDecision.decision_id] === option.id;
                    const recommended =
                      option.id === activeDecision.recommended_option_id;
                    return (
                      <button
                        key={option.id}
                        onClick={() =>
                          setSelectedOptions((previous) => ({
                            ...previous,
                            [activeDecision.decision_id]: option.id,
                          }))
                        }
                        className={cn(
                          "w-full rounded-[22px] border px-5 py-5 text-left transition",
                          selected
                            ? "border-[#9fd7bd]/45 bg-[#9fd7bd]/12 shadow-[0_0_30px_rgba(159,215,189,0.08)]"
                            : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/7",
                        )}
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div className="flex items-start gap-4">
                            <div
                              className={cn(
                                "mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2",
                                selected
                                  ? "border-[#9fd7bd]"
                                  : "border-white/30",
                              )}
                            >
                              {selected && (
                                <div className="h-2.5 w-2.5 rounded-full bg-[#9fd7bd]" />
                              )}
                            </div>
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="text-lg font-bold text-white">
                                  {option.label}
                                </h4>
                                {recommended && (
                                  <StatusPill tone="accent">
                                    Recommended
                                  </StatusPill>
                                )}
                              </div>
                              <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                                {option.what_it_steers}
                              </p>
                            </div>
                          </div>
                          <div className="rounded-2xl border border-white/8 bg-black/15 px-4 py-3 text-sm text-[#9fb4c8] md:max-w-sm">
                            <div>
                              <span className="font-semibold text-white">
                                Immediate action:
                              </span>{" "}
                              {option.immediate_action}
                            </div>
                            <div className="mt-2">
                              <span className="font-semibold text-white">
                                Mode:
                              </span>{" "}
                              <code className="rounded bg-white/8 px-2 py-1 text-[#9fd7bd]">
                                {option.immediate_action_mode}
                              </code>
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div className="border-t border-white/8 bg-[#121c26]/85 px-8 py-6 backdrop-blur-xl">
                  <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fd7bd]">
                          Operator note
                        </label>
                        <textarea
                          value={actionNote}
                          onChange={(event) =>
                            setActionNote(event.target.value)
                          }
                          rows={3}
                          className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-[#9fd7bd]/35"
                          placeholder="Optional note to attach to the workflow dispatch."
                        />
                      </div>
                      {activeDecision.write_in_allowed && (
                        <div>
                          <label className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fd7bd]">
                            Custom instruction
                          </label>
                          <textarea
                            value={freeTextInstruction}
                            onChange={(event) =>
                              setFreeTextInstruction(event.target.value)
                            }
                            rows={3}
                            className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-[#9fd7bd]/35"
                            placeholder="Write a custom instruction if none of the canonical options capture what you want."
                          />
                        </div>
                      )}
                      {pendingConfirmation && (
                        <div className="rounded-2xl border border-amber-200/20 bg-amber-200/8 p-4 text-sm text-[#d9e4ef]">
                          <div className="font-semibold text-amber-100">
                            Confirmation needed
                          </div>
                          <p className="mt-2 leading-7">
                            {pendingConfirmation.summary}
                          </p>
                          <p className="mt-2 leading-7 text-[#9fb4c8]">
                            {pendingConfirmation.explanation}
                          </p>
                          <button
                            onClick={() => void handleApplyFreeText(true)}
                            className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-amber-200/20 bg-amber-200/12 px-4 py-2 text-sm font-semibold text-amber-50 transition hover:bg-amber-200/18"
                          >
                            Confirm and apply
                            <ArrowRight className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col justify-between gap-4 rounded-[24px] border border-white/10 bg-black/15 p-5">
                      <div>
                        <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fd7bd]">
                          Ready state
                        </div>
                        <p className="mt-3 text-sm leading-7 text-[#9fb4c8]">
                          {selectedOptions[activeDecision.decision_id]
                            ? `Ready to dispatch ${selectedOptions[activeDecision.decision_id]} for ${activeDecision.title}.`
                            : "Select one of the options above before dispatching."}
                        </p>
                        <p className="mt-3 text-sm leading-7 text-[#d9e4ef]">
                          {actionMessage}
                        </p>
                      </div>

                      <div className="space-y-3">
                        <button
                          onClick={() => void handleApplySelectedOption()}
                          disabled={
                            !selectedOptions[activeDecision.decision_id] ||
                            dispatchState === "working"
                          }
                          className={cn(
                            "flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold transition",
                            !selectedOptions[activeDecision.decision_id] ||
                              dispatchState === "working"
                              ? "cursor-not-allowed bg-white/5 text-white/35"
                              : "bg-[#9fd7bd] text-[#071017] hover:bg-[#b0e8ce]",
                          )}
                        >
                          {dispatchState === "working" ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Zap className="h-4 w-4" />
                          )}
                          Apply selected option
                        </button>
                        <button
                          onClick={() => void handleApplyFreeText(false)}
                          disabled={
                            !freeTextInstruction.trim() ||
                            dispatchState === "working"
                          }
                          className={cn(
                            "flex w-full items-center justify-center gap-2 rounded-2xl border px-5 py-3 text-sm font-bold transition",
                            !freeTextInstruction.trim() ||
                              dispatchState === "working"
                              ? "cursor-not-allowed border-white/8 bg-white/5 text-white/35"
                              : "border-white/10 bg-white/6 text-white hover:border-[#9fd7bd]/35 hover:bg-white/10",
                          )}
                        >
                          <Sparkles className="h-4 w-4" />
                          Interpret custom instruction
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            )}

            <section className="space-y-5 rounded-[28px] border border-white/10 bg-[#121c26] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.25)]">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                  Other decisions
                </div>
                <h3 className="mt-3 text-2xl font-bold text-white">
                  Nearby choices that still matter
                </h3>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {otherDecisions.map((decision) => (
                  <button
                    key={decision.decision_id}
                    onClick={() => setActiveDecisionId(decision.decision_id)}
                    className="rounded-[22px] border border-white/10 bg-[#172430]/70 p-5 text-left transition hover:border-[#9fd7bd]/28 hover:bg-[#172430]"
                  >
                    <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#9fb4c8]">
                      {decision.decision_family_label}
                    </div>
                    <div className="mt-3 text-lg font-semibold text-white">
                      {decision.title}
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                      {decision.why_now}
                    </p>
                    <div className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[#9fd7bd]">
                      Load decision
                      <ChevronRight className="h-4 w-4" />
                    </div>
                  </button>
                ))}
              </div>
            </section>
          </main>

          <aside className="space-y-6">
            <section className="rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.24)]">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                <ShieldCheck className="h-4 w-4" />
                Control state
              </div>
              <div className="mt-4 space-y-4 text-sm leading-7 text-[#9fb4c8]">
                <div>
                  <div className="font-semibold text-white">
                    {controlMode === "github"
                      ? "Connected to GitHub control"
                      : "Reading the published snapshot"}
                  </div>
                  <div className="mt-1">
                    {runtimeState.liveActionsEnabled
                      ? "The board is in sync, so apply and clarify actions are available."
                      : "Actions stay disabled until GitHub control is connected and the board is not mismatched."}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-black/15 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[#9fb4c8]">
                    Current direction
                  </div>
                  <div className="mt-2 text-base font-semibold text-white">
                    {payload.current_direction?.label || "No direction emitted"}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/8 bg-black/15 p-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[#9fb4c8]">
                    Support links
                  </div>
                  <div className="mt-3 space-y-3">
                    {(payload.support_links || [])
                      .slice(0, 4)
                      .map((link: AnyRecord) => (
                        <a
                          key={link.href}
                          href={link.href}
                          className="block rounded-2xl border border-white/8 bg-white/5 p-3 transition hover:border-[#9fd7bd]/25 hover:bg-white/8"
                        >
                          <div className="flex items-center justify-between gap-3 text-sm font-semibold text-white">
                            <span>{link.label}</span>
                            <ExternalLink className="h-4 w-4 text-[#9fd7bd]" />
                          </div>
                          <div className="mt-1 text-xs leading-6 text-[#9fb4c8]">
                            {link.detail}
                          </div>
                        </a>
                      ))}
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.24)]">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                <MessageSquareText className="h-4 w-4" />
                Ask the board
              </div>
              <div className="mt-4 space-y-3">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-[#9fd7bd]/35"
                  placeholder="Ask a plain-English question about the current state, decision, or paper path."
                />
                <div className="flex flex-wrap gap-2">
                  {presetQuestions.slice(0, 4).map((preset: string) => (
                    <button
                      key={preset}
                      onClick={() => {
                        setQuestion(preset);
                        void handleClarify(preset);
                      }}
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-[#9fb4c8] transition hover:border-[#9fd7bd]/25 hover:bg-white/10 hover:text-white"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => void handleClarify(question)}
                  disabled={!question.trim() || clarifyState === "working"}
                  className={cn(
                    "flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-bold transition",
                    !question.trim() || clarifyState === "working"
                      ? "cursor-not-allowed bg-white/5 text-white/35"
                      : "bg-[#9fd7bd] text-[#071017] hover:bg-[#b0e8ce]",
                  )}
                >
                  {clarifyState === "working" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Run clarify workflow
                </button>
              </div>

              {clarifyResponse && (
                <div className="mt-5 rounded-2xl border border-white/8 bg-black/15 p-4 text-sm leading-7 text-[#9fb4c8]">
                  <div className="font-semibold text-white">
                    {clarifyResponse.answer}
                  </div>
                  {Array.isArray(clarifyResponse.evidence_chain) &&
                    clarifyResponse.evidence_chain.length > 0 && (
                      <ul className="mt-3 space-y-2">
                        {clarifyResponse.evidence_chain.map((item: string) => (
                          <li key={item} className="flex gap-2">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#9fd7bd]" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  {clarifyResponse.implication && (
                    <p className="mt-3">
                      Implication: {clarifyResponse.implication}
                    </p>
                  )}
                  {clarifyResponse.recommended_follow_up && (
                    <p className="mt-2">
                      Follow-up: {clarifyResponse.recommended_follow_up}
                    </p>
                  )}
                </div>
              )}
            </section>

            {Array.isArray(payload.decision_history) &&
              payload.decision_history.length > 0 && (
                <section className="rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.24)]">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                    <Clock3 className="h-4 w-4" />
                    System log
                  </div>
                  <div className="mt-5 space-y-4 border-l border-white/8 pl-5">
                    {payload.decision_history
                      .slice(0, 5)
                      .map((item: AnyRecord) => (
                        <div
                          key={`${item.timestamp}-${item.decision_id}`}
                          className="relative"
                        >
                          <span className="absolute -left-[1.62rem] top-2 h-2.5 w-2.5 rounded-full bg-[#9fd7bd] ring-4 ring-[#121c26]" />
                          <div className="text-[11px] font-mono uppercase tracking-[0.16em] text-[#9fb4c8]">
                            {formatAge(item.timestamp)}
                          </div>
                          <div className="mt-1 font-semibold text-white">
                            {item.decision_title}
                          </div>
                          <div className="mt-1 text-xs text-[#9fd7bd]">
                            {item.interpreted_intent}
                          </div>
                        </div>
                      ))}
                  </div>
                </section>
              )}

            <section className="rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.24)]">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                <Activity className="h-4 w-4" />
                Goal progress
              </div>
              <div className="mt-5 space-y-5">
                {(payload.goal_progress?.stages || []).map(
                  (stage: AnyRecord) => (
                    <div
                      key={stage.label}
                      className="rounded-2xl border border-white/8 bg-black/15 p-4"
                    >
                      <div className="flex items-end justify-between gap-3">
                        <div className="font-semibold text-white">
                          {stage.label}
                        </div>
                        <div className="text-xs text-[#9fb4c8]">
                          {stage.completed}/{stage.total}
                        </div>
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/8">
                        <div
                          className="h-full rounded-full bg-[#9fd7bd]"
                          style={{ width: `${stage.percent || 0}%` }}
                        />
                      </div>
                      <div className="mt-4 space-y-2 text-sm text-[#9fb4c8]">
                        {(stage.checkpoints || [])
                          .slice(0, 4)
                          .map((checkpoint: AnyRecord) => (
                            <div
                              key={checkpoint.label}
                              className="flex items-center gap-2"
                            >
                              {checkpoint.complete ? (
                                <CheckCircle2 className="h-4 w-4 text-[#9fd7bd]" />
                              ) : (
                                <Circle className="h-4 w-4 opacity-40" />
                              )}
                              <span>{checkpoint.label}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  ),
                )}
              </div>
            </section>

            <section className="rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_18px_44px_rgba(0,0,0,0.24)]">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                <FileText className="h-4 w-4" />
                Discovery summary
              </div>
              <div className="mt-4 space-y-4 text-sm leading-7 text-[#9fb4c8]">
                <div>
                  <div className="font-semibold text-white">Major findings</div>
                  <ul className="mt-2 space-y-2">
                    {(payload.discovery_summary?.major_findings || [])
                      .slice(0, 3)
                      .map((item: string) => (
                        <li key={item} className="flex gap-2">
                          <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#9fd7bd]" />
                          <span>{item}</span>
                        </li>
                      ))}
                  </ul>
                </div>
                <div className="border-t border-white/8 pt-4">
                  <div className="font-semibold text-white">
                    Current unknowns
                  </div>
                  <ul className="mt-2 space-y-2">
                    {(payload.discovery_summary?.current_unknowns || [])
                      .slice(0, 3)
                      .map((item: string) => (
                        <li key={item} className="flex gap-2">
                          <span className="mt-2 h-1.5 w-1.5 rounded-full bg-amber-200" />
                          <span>{item}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>

      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#071017]/80 px-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-[28px] border border-white/10 bg-[#121c26] p-6 shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.24em] text-[#9fd7bd]">
                  <KeyRound className="h-4 w-4" />
                  GitHub control
                </div>
                <h3 className="mt-3 text-2xl font-bold text-white">
                  Connect the public cockpit to GitHub Actions
                </h3>
                <p className="mt-2 text-sm leading-7 text-[#9fb4c8]">
                  Use a fine-grained personal access token with Actions
                  read/write and Contents read/write on{" "}
                  <code className="rounded bg-white/8 px-1.5 py-0.5 text-[#9fd7bd]">
                    {GITHUB_OWNER}/{GITHUB_REPO}
                  </code>
                  . The token stays in this browser only.
                </p>
              </div>
              <button
                onClick={() => setSettingsOpen(false)}
                className="rounded-full border border-white/10 bg-white/5 p-2 text-[#9fb4c8] transition hover:bg-white/10 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-6 space-y-4">
              <input
                type="password"
                value={tokenDraft}
                onChange={(event) => setTokenDraft(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition focus:border-[#9fd7bd]/35"
                placeholder="Paste your fine-grained GitHub token"
              />
              <div className="flex flex-wrap justify-end gap-3">
                <button
                  onClick={() => setSettingsOpen(false)}
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveToken}
                  disabled={!tokenDraft.trim()}
                  className={cn(
                    "rounded-2xl px-4 py-3 text-sm font-semibold transition",
                    tokenDraft.trim()
                      ? "bg-[#9fd7bd] text-[#071017] hover:bg-[#b0e8ce]"
                      : "cursor-not-allowed bg-white/5 text-white/35",
                  )}
                >
                  Save and connect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
