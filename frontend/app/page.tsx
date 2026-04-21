"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Sparkles,
  TrendingDown,
  Zap,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";

/* ── type definitions ─────────────────────────────────────── */

type FunnelDatum = {
  stage: string;
  value: number | string;
  status: string;
};

type AuditReport = {
  overall_score: number;
  funnel_data: FunnelDatum[];
  top_recommendations: string[];
};

type AuditResponse = {
  status: string;
  screenshot: string;
  report: AuditReport;
  email_sent?: boolean;
  email_message?: string | null;
};

/* ── premium blue color palette for chart bars ────────────── */

const STAGE_COLORS: Record<string, string> = {
  good: "#2563eb",    // vivid blue
  warning: "#f59e0b", // amber
  danger: "#ef4444",  // red
};

function normalizeStatus(status: string): keyof typeof STAGE_COLORS {
  const normalized = status.toLowerCase();
  if (normalized.includes("good") || normalized.includes("strong")) return "good";
  if (normalized.includes("warn") || normalized.includes("medium")) return "warning";
  return "danger";
}

function normalizeFunnelValue(value: number | string): number {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return 0;
    return Math.min(100, Math.max(0, value));
  }

  const match = String(value).match(/-?\d+(\.\d+)?/);
  if (!match) return 0;
  const parsed = Number(match[0]);
  if (!Number.isFinite(parsed)) return 0;
  return Math.min(100, Math.max(0, parsed));
}

/* ── Custom chart tooltip ─────────────────────────────────── */

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; payload: FunnelDatum }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  const statusKey = normalizeStatus(d.payload.status);
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 shadow-xl">
      <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-[var(--foreground)]">
        {d.value}<span className="text-sm font-normal text-[var(--muted-foreground)]">/100</span>
      </p>
      <span
        className="mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
        style={{
          background: STAGE_COLORS[statusKey] + "18",
          color: STAGE_COLORS[statusKey],
        }}
      >
        {d.payload.status}
      </span>
    </div>
  );
}

/* ── Score ring component ─────────────────────────────────── */

function ScoreRing({ score }: { score: number }) {
  const radius = 52;
  const stroke = 8;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const scoreColor =
    score >= 70 ? "#2563eb" : score >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative flex items-center justify-center">
      <svg width={128} height={128} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={64}
          cy={64}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        {/* Progress arc */}
        <circle
          cx={64}
          cy={64}
          r={radius}
          fill="none"
          stroke={scoreColor}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-extrabold" style={{ color: scoreColor }}>
          {score}
        </span>
        <span className="text-[11px] font-medium text-[var(--muted-foreground)]">/ 100</span>
      </div>
    </div>
  );
}

/* ── Main page ────────────────────────────────────────────── */

export default function Home() {
  const [url, setUrl] = useState("https://www.notion.so");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<AuditResponse | null>(null);
  const [sendEmail, setSendEmail] = useState(true);
  const [reportMessage, setReportMessage] = useState<string | null>(null);

  const screenshotSrc = useMemo(() => {
    if (!auditData?.screenshot) return null;
    return `data:image/png;base64,${auditData.screenshot}`;
  }, [auditData]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setReportMessage(null);
    if (sendEmail) {
      setReportMessage("We will send you an email once the task is done and share the report.");
    }
    setIsLoading(true);
    setAuditData(null);

    try {
      const response = await fetch("/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, send_email: sendEmail }),
      });

      const payload = (await response.json()) as AuditResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(
          (payload as { detail?: string }).detail || "Audit failed. Please try another URL."
        );
      }

      setAuditData(payload as AuditResponse);
      if (sendEmail) {
        const auditPayload = payload as AuditResponse;
        if (!auditPayload.email_sent && auditPayload.email_message) {
          setError(auditPayload.email_message);
        }
      }
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Unexpected error occurred while running audit.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  /* -- derived stats ------------------------------------------------ */
  const strongCount = auditData
    ? auditData.report.funnel_data.filter((i) => normalizeStatus(i.status) === "good").length
    : 0;
  const attentionCount = auditData
    ? auditData.report.funnel_data.filter((i) => normalizeStatus(i.status) !== "good").length
    : 0;
  const chartData = useMemo(
    () =>
      (auditData?.report.funnel_data ?? []).map((item) => ({
        ...item,
        value: normalizeFunnelValue(item.value),
      })),
    [auditData]
  );

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--background)] px-4 py-8 md:px-8 lg:py-12">
      {/* Decorative gradient blobs */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[600px] w-[900px] rounded-full bg-[radial-gradient(ellipse,rgba(59,130,246,0.10)_0%,transparent_70%)] blur-2xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[400px] w-[500px] rounded-full bg-[radial-gradient(ellipse,rgba(37,99,235,0.08)_0%,transparent_70%)] blur-3xl" />

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-col gap-7">
        {/* ── Header + Form ───────────────────────────────── */}
        <section className="glass-card animate-fade-in-up rounded-2xl p-6 shadow-lg md:p-8">
          <div className="mb-5 flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-white shadow-md">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-[var(--foreground)] md:text-3xl">
                Conversion Funnel Analyzer
              </h1>
              <p className="mt-1 max-w-xl text-sm leading-relaxed text-[var(--muted-foreground)]">
                Enter a landing page URL to inspect funnel leaks, score performance, and get
                actionable recommendations.
              </p>
            </div>
          </div>

          <label className="mt-3 inline-flex items-center gap-3 text-sm font-medium text-[var(--foreground)]">
            <button
              type="button"
              role="switch"
              aria-checked={sendEmail}
              onClick={() => setSendEmail((prev) => !prev)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                sendEmail ? "bg-[var(--primary)]" : "bg-[var(--muted)]"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  sendEmail ? "translate-x-5" : "translate-x-1"
                }`}
              />
            </button>
            Email the report to batmantanmay22@gmail.com after audit
          </label>
          <form onSubmit={handleSubmit} className="mt-3 flex flex-col gap-3 md:flex-row">
            <input
              id="audit-url-input"
              className="h-11 flex-1 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 text-sm font-medium text-[var(--foreground)] outline-none placeholder:text-[var(--muted-foreground)] transition-all duration-200 focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/25"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example.com"
              required
              type="url"
            />
            <Button
              id="audit-submit-btn"
              type="submit"
              disabled={isLoading}
              className="h-11 cursor-pointer rounded-xl bg-[var(--primary)] px-6 text-sm font-semibold text-white shadow-md transition-all duration-200 hover:brightness-110 hover:shadow-lg disabled:opacity-60 md:w-48"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Run Audit
                </>
              )}
            </Button>
          </form>

          {error && (
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-300/40 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error}</p>
            </div>
          )}
          {reportMessage && (
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-emerald-300/40 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{reportMessage}</p>
            </div>
          )}
        </section>

        {/* ── Loading State ───────────────────────────────── */}
        {isLoading && (
          <section className="glass-card animate-fade-in-up rounded-2xl py-16 text-center shadow-lg">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-[var(--primary)]" />
            <p className="mt-4 text-base font-semibold text-[var(--foreground)]">
              Analyzing your funnel…
            </p>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              This may take a moment while we capture and evaluate your page.
            </p>
            <div className="mx-auto mt-6 h-1.5 w-56 overflow-hidden rounded-full bg-[var(--muted)]">
              <div className="animate-shimmer h-full w-full rounded-full" />
            </div>
          </section>
        )}

        {/* ── Results ─────────────────────────────────────── */}
        {auditData && (
          <>
            {/* ── KPI Cards ────────────────────────────────── */}
            <section className="grid gap-5 md:grid-cols-3">
              <article className="glass-card animate-fade-in-up stagger-1 rounded-2xl p-6 shadow-lg">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                    Overall Score
                  </p>
                </div>
                <div className="mt-4 flex justify-center">
                  <ScoreRing score={auditData.report.overall_score} />
                </div>
              </article>

              <article className="glass-card animate-fade-in-up stagger-2 rounded-2xl p-6 shadow-lg">
                <p className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Strong Stages
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <p className="text-5xl font-extrabold text-[#2563eb]">
                    {strongCount}
                  </p>
                  <p className="mb-1 text-sm text-[var(--muted-foreground)]">
                    / {auditData.report.funnel_data.length}
                  </p>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                  <div
                    className="h-full rounded-full bg-[#2563eb] transition-all duration-700"
                    style={{
                      width: `${(strongCount / Math.max(auditData.report.funnel_data.length, 1)) * 100}%`,
                    }}
                  />
                </div>
                <p className="mt-2 text-xs text-[var(--muted-foreground)]">Marked good / strong</p>
              </article>

              <article className="glass-card animate-fade-in-up stagger-3 rounded-2xl p-6 shadow-lg">
                <p className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  Needs Attention
                </p>
                <div className="mt-4 flex items-end gap-2">
                  <p className="text-5xl font-extrabold text-[#f59e0b]">
                    {attentionCount}
                  </p>
                  <p className="mb-1 text-sm text-[var(--muted-foreground)]">
                    / {auditData.report.funnel_data.length}
                  </p>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                  <div
                    className="h-full rounded-full bg-[#f59e0b] transition-all duration-700"
                    style={{
                      width: `${(attentionCount / Math.max(auditData.report.funnel_data.length, 1)) * 100}%`,
                    }}
                  />
                </div>
                <p className="mt-2 text-xs text-[var(--muted-foreground)]">Warning or danger stages</p>
              </article>
            </section>

            {/* ── Chart + Recommendations ──────────────────── */}
            <section className="grid gap-6 lg:grid-cols-5">
              {/* Chart — spans 3 cols */}
              <article className="glass-card animate-fade-in-up stagger-4 rounded-2xl p-6 shadow-lg lg:col-span-3">
                <div className="mb-5 flex items-center justify-between">
                  <h2 className="text-lg font-bold text-[var(--foreground)]">
                    Funnel Stage Performance
                  </h2>
                  <div className="flex items-center gap-1.5 rounded-full bg-[var(--accent)] px-3 py-1 text-xs font-medium text-[var(--primary)]">
                    <TrendingDown className="h-3.5 w-3.5" />
                    Drop-off risk indicator
                  </div>
                </div>
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      margin={{ top: 8, right: 8, left: -12, bottom: 4 }}
                    >
                      <defs>
                        {/* Gradient definitions for each status color */}
                        <linearGradient id="grad-good" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#3b82f6" stopOpacity={1} />
                          <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0.85} />
                        </linearGradient>
                        <linearGradient id="grad-warning" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#fbbf24" stopOpacity={1} />
                          <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.85} />
                        </linearGradient>
                        <linearGradient id="grad-danger" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#f87171" stopOpacity={1} />
                          <stop offset="100%" stopColor="#ef4444" stopOpacity={0.85} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="4 4"
                        stroke="var(--border)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="stage"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 12, fill: "var(--muted-foreground)", fontWeight: 500 }}
                        dy={8}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tickLine={false}
                        axisLine={false}
                        tick={{ fontSize: 12, fill: "var(--muted-foreground)", fontWeight: 500 }}
                        dx={-4}
                      />
                      <Tooltip
                        content={<ChartTooltip />}
                        cursor={{ fill: "var(--accent)", radius: 8, opacity: 0.5 }}
                      />
                      <Bar dataKey="value" radius={[10, 10, 4, 4]} barSize={48} minPointSize={6}>
                        {chartData.map((item, index) => {
                          const k = normalizeStatus(item.status);
                          return (
                            <Cell
                              key={`${item.stage}-${index}`}
                              fill={`url(#grad-${k})`}
                              style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.08))" }}
                            />
                          );
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                {/* Chart legend */}
                <div className="mt-4 flex flex-wrap gap-4">
                  {[
                    { label: "Good", color: "#2563eb" },
                    { label: "Warning", color: "#f59e0b" },
                    { label: "Danger", color: "#ef4444" },
                  ].map((l) => (
                    <div key={l.label} className="flex items-center gap-1.5 text-xs font-medium text-[var(--muted-foreground)]">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: l.color }}
                      />
                      {l.label}
                    </div>
                  ))}
                </div>
              </article>

              {/* Recommendations — spans 2 cols */}
              <article className="glass-card animate-fade-in-up stagger-5 rounded-2xl p-6 shadow-lg lg:col-span-2">
                <div className="mb-4 flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <h2 className="text-lg font-bold text-[var(--foreground)]">
                    Top Recommendations
                  </h2>
                </div>

                <div className="max-h-[380px] space-y-3 overflow-y-auto pr-1">
                  {auditData.report.top_recommendations.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--accent)]/40 p-3.5 transition-colors duration-200 hover:bg-[var(--accent)]"
                    >
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
                      <div className="prose-recommendations min-w-0 flex-1">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {item}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            {/* ── Visit Site ──────────────────────────────── */}
            <section className="glass-card animate-fade-in-up stagger-6 rounded-2xl p-6 shadow-lg">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-[var(--foreground)]">
                  Audited Page
                </h2>
                <a
                  id="visit-site-link"
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white shadow-md transition-all duration-200 hover:brightness-110 hover:shadow-lg"
                >
                  <ExternalLink className="h-4 w-4" />
                  Visit Site
                </a>
              </div>
              <p className="mt-1 truncate text-sm text-[var(--muted-foreground)]">{url}</p>
            </section>

            {/* ── Screenshot ───────────────────────────────── */}
            <section className="glass-card animate-fade-in-up stagger-7 rounded-2xl p-6 shadow-lg">
              <h2 className="mb-4 text-lg font-bold text-[var(--foreground)]">
                Captured Page Screenshot
              </h2>
              {screenshotSrc ? (
                <div className="max-h-[600px] overflow-y-auto rounded-xl border border-[var(--border)] shadow-md">
                  <img
                    src={screenshotSrc}
                    alt="Captured audited page"
                    className="w-full object-cover"
                  />
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">No screenshot available.</p>
              )}
            </section>
          </>
        )}

        {/* ── Empty state ─────────────────────────────────── */}
        {!auditData && !isLoading && (
          <section className="glass-card animate-fade-in-up rounded-2xl border-2 border-dashed border-[var(--border)] py-16 text-center shadow-sm">
            <BarChart3 className="mx-auto h-12 w-12 text-[var(--primary)] opacity-30" />
            <p className="mt-4 text-base font-semibold text-[var(--foreground)]">
              No audit results yet
            </p>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Run an audit to visualize your funnel performance and recommendations.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
