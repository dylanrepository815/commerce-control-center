"use client";
import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowDownUp,
  FlaskConical,
  FileSearch,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import {
  api,
  post,
  Project,
  Run,
  Candidate,
  Settings,
  Event,
  date,
} from "@/lib/api";
import {
  PageTitle,
  Badge,
  DemoBanner,
  Empty,
  ErrorBox,
  Modal,
} from "@/components/ui";
type Report = {
  candidate: Candidate;
  is_demo: boolean;
  rule_version: string;
  evidence: {
    id: string;
    provider: string;
    check_type: string;
    findings: string;
    verified: boolean;
    source_reference: string;
    observed_at: string;
    categories: string[];
  }[];
};
export default function ProjectDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [project, setProject] = useState<Project | null>(null),
    [runs, setRuns] = useState<Run[]>([]),
    [settings, setSettings] = useState<Settings | null>(null),
    [events, setEvents] = useState<Event[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [selection, setSelection] = useState<Candidate | null>(null),
    [report, setReport] = useState<Report | null>(null),
    [ack, setAck] = useState(false),
    [sort, setSort] = useState<keyof Candidate>("domain_score"),
    [asc, setAsc] = useState(false),
    [runId, setRunId] = useState("");
  const load = useCallback(async () => {
    const [p, r, s, e] = await Promise.all([
      api<Project>(`/projects/${id}`),
      api<Run[]>(`/projects/${id}/research`),
      api<Settings>("/settings"),
      api<Event[]>(`/activity?project_id=${id}&limit=10`),
    ]);
    setProject(p);
    setRuns(r);
    setSettings(s);
    setEvents(e);
  }, [id]);
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);
  const run = runs.find((r) => r.id === runId) || runs[0];
  const current = run?.id === runs[0]?.id;
  const sorted = (run?.candidates || [])
    .filter((c) => c.final_status !== "FAIL")
    .sort((a, b) => {
      const left = a[sort],
        right = b[sort];
      const n =
        typeof left === "number" && typeof right === "number"
          ? left - right
          : String(left ?? "").localeCompare(String(right ?? ""));
      return asc ? n : -n;
    })
    .slice(0, 20);
  const sortBy = (key: keyof Candidate) => {
    if (sort === key) setAsc(!asc);
    else {
      setSort(key);
      setAsc(key === "domain");
    }
  };
  async function openReport(c: Candidate) {
    try {
      setReport(await api<Report>(`/candidates/${c.id}/report`));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!project)
    return (
      <>
        <ErrorBox error={error} />
        <p className="muted">Loading project…</p>
      </>
    );
  return (
    <>
      <Link className="back-link" href="/projects">
        <ArrowLeft size={15} />
        All projects
      </Link>
      <PageTitle
        eyebrow="PROJECT DETAIL"
        title={project.name}
        description={`${project.market} · ${project.niche}`}
        action={<Badge value={project.status} />}
      />
      <ErrorBox error={error} />
      <div className="project-meta">
        <span>
          Project ID <code>{project.id}</code>
        </span>
        <span>Created {date(project.created_at)}</span>
      </div>
      <div className="steps">
        {["DOMAIN_RESEARCH", "DOMAIN_SELECTION", "BRAND_PENDING"].map(
          (s, i) => (
            <div key={s} className={project.status === s ? "current" : ""}>
              <span>{i + 1}</span>
              {s.replaceAll("_", " ").toLowerCase()}
            </div>
          ),
        )}
      </div>
      {project.selected_domain && (
        <section className="selected-domain">
          <ShieldCheck size={25} />
          <div>
            <div className="eyebrow">
              OWNER APPROVED
              {runs.find((r) =>
                r.candidates.some((c) => c.domain === project.selected_domain),
              )?.is_demo
                ? " · SYNTHETIC DEMO"
                : ""}
            </div>
            <h2>{project.selected_domain}</h2>
            <p>
              Approved {project.approved_at ? date(project.approved_at) : ""} ·
              Owner {project.approved_by}
            </p>
            <small>
              Brand pending. V1 stops here; no purchase has been made.
            </small>
          </div>
        </section>
      )}
      <section className="card">
        <div className="card-heading">
          <div>
            <h2>Domain research</h2>
            <p>Evidence first. Owner approval always.</p>
          </div>
          {project.status === "DOMAIN_RESEARCH" &&
            settings?.fixtures_enabled && (
              <button
                className="button secondary"
                disabled={busy || runs.some((r) => r.state === "RUNNING")}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await post(`/projects/${id}/research/fixture`);
                    setRunId("");
                    await load();
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <FlaskConical size={17} />
                {busy ? "Running fixture…" : "Run demo research"}
              </button>
            )}
          {project.status !== "BRAND_PENDING" &&
            (project.status === "DOMAIN_SELECTION" ||
              runs.some((r) => r.state === "RUNNING")) && (
              <button
                className="button secondary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setError("");
                  try {
                    await post(`/projects/${id}/research/retry`);
                    await load();
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Restart research
              </button>
            )}
        </div>
        {run ? (
          <>
            <div className="research-toolbar">
              <select
                aria-label="Research run"
                value={run.id}
                onChange={(e) => setRunId(e.target.value)}
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {date(r.created_at)} ·{" "}
                    {r.is_demo ? "DEMO" : "Submitted evidence"} · {r.state}
                  </option>
                ))}
              </select>
              <span className="muted">
                {run.candidates.length} / 20 candidates · Rules{" "}
                {run.rule_version}
              </span>
            </div>
            {run.is_demo && (
              <div className="padded-x">
                <DemoBanner />
              </div>
            )}
            {run.failure && (
              <div className="padded-x">
                <ErrorBox error={run.failure} />
              </div>
            )}
            {run.state === "RUNNING" ? (
              <p className="padded">Research run is in progress.</p>
            ) : sorted.length ? (
              <div className="table-scroll">
                <table className="domain-table">
                  <thead>
                    <tr>
                      {[
                        ["Domain", "domain"],
                        ["Domain Score", "domain_score"],
                        ["ScamAdviser", "scamadviser_score"],
                        ["History", "history_status"],
                        ["Backlinks", "backlink_status"],
                        ["Safety", "safety_status"],
                        ["Niche Fit", "niche_fit_score"],
                        ["Status", "final_status"],
                      ].map(([label, key]) => (
                        <th
                          key={key}
                          aria-sort={
                            sort === key
                              ? asc
                                ? "ascending"
                                : "descending"
                              : "none"
                          }
                        >
                          <button
                            className="sort"
                            onClick={() => sortBy(key as keyof Candidate)}
                          >
                            {label}
                            <ArrowDownUp size={12} />
                          </button>
                        </th>
                      ))}
                      <th>Warnings</th>
                      <th>View Report</th>
                      <th>Select Domain</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((c) => (
                      <tr key={c.id}>
                        <td>
                          <strong>{c.domain}</strong>
                          {run.is_demo && (
                            <span className="cell-sub demo-text">DEMO</span>
                          )}
                        </td>
                        <td>
                          <span className="score">
                            {c.domain_score}
                            <small>/100</small>
                          </span>
                        </td>
                        <td>{c.scamadviser_score ?? "Unknown"}</td>
                        <td>
                          <Badge value={c.history_status} />
                        </td>
                        <td>
                          <Badge value={c.backlink_status} />
                        </td>
                        <td>
                          <Badge value={c.safety_status} />
                        </td>
                        <td>{c.niche_fit_score ?? "Unknown"}</td>
                        <td>
                          <Badge value={c.final_status} />
                        </td>
                        <td>
                          <span className="warning-text">
                            {c.warnings.join("; ") || "None"}
                          </span>
                        </td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => openReport(c)}
                          >
                            <FileSearch size={15} />
                            Report
                          </button>
                        </td>
                        <td>
                          <button
                            className="button compact secondary"
                            disabled={
                              c.final_status !== "PASS" ||
                              project.status !== "DOMAIN_SELECTION" ||
                              !current
                            }
                            onClick={() => {
                              setSelection(c);
                              setAck(false);
                              setError("");
                            }}
                          >
                            Select
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty title="No eligible candidates">
                This run has no PASS or REVIEW results.
              </Empty>
            )}
            {!!run.candidates.filter((c) => c.final_status === "FAIL")
              .length && (
              <details className="failed-results">
                <summary>
                  Rejected candidates (
                  {
                    run.candidates.filter((c) => c.final_status === "FAIL")
                      .length
                  }
                  )
                </summary>
                {run.candidates
                  .filter((c) => c.final_status === "FAIL")
                  .map((c) => (
                    <div key={c.id}>
                      <strong>{c.domain}</strong>
                      <Badge value="FAIL" />
                      <p>{c.rejection_reasons.join("; ")}</p>
                      <button
                        className="text-button"
                        onClick={() => openReport(c)}
                      >
                        View rejection report
                      </button>
                    </div>
                  ))}
              </details>
            )}
          </>
        ) : (
          <Empty title="Ready for domain research">
            {settings?.fixtures_enabled
              ? "Use “Run demo research” to explore the workflow with clearly labeled synthetic data."
              : "No live provider is configured. An authorized research agent can submit evidence through the API."}
          </Empty>
        )}
      </section>
      <section className="card project-activity">
        <div className="card-heading">
          <h2>Project activity</h2>
          <Link href={`/activity?project=${id}`}>Full audit log</Link>
        </div>
        <div className="timeline">
          {events.map((e) => (
            <div key={e.id}>
              <span className="timeline-dot" />
              <strong>
                {e.action.replaceAll(".", " ").replaceAll("_", " ")}
              </strong>
              <small>
                {date(e.created_at)} · {e.actor_type}
              </small>
            </div>
          ))}
        </div>
      </section>
      {selection && (
        <Modal
          title="Confirm domain selection"
          onClose={() => {
            if (!busy) setSelection(null);
          }}
        >
          <ErrorBox error={error} />
          {run?.is_demo && <DemoBanner />}
          <p>
            You are approving <strong>{selection.domain}</strong> as the final
            domain for <strong>{project.name}</strong>.
          </p>
          <div className="approval-summary">
            <Badge value={selection.final_status} />
            <span>
              Domain Score <strong>{selection.domain_score}/100</strong>
            </span>
            <span>
              ScamAdviser <strong>{selection.scamadviser_score}/100</strong>
            </span>
          </div>
          <p>
            This records your Owner approval and moves the project to{" "}
            <strong>Brand Pending</strong>. No domain is purchased.
          </p>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            <span>
              {run?.is_demo
                ? "I understand this is synthetic demo research and confirm this demo selection."
                : "I have reviewed the evidence and confirm this domain selection."}
            </span>
          </label>
          <div className="form-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setSelection(null)}
            >
              Cancel
            </button>
            <button
              className="button primary"
              disabled={!ack || busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await post(`/projects/${id}/select-domain`, {
                    candidate_id: selection.id,
                    confirmed: true,
                    demo_acknowledged: !!run?.is_demo,
                  });
                  setSelection(null);
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Approving…" : "Confirm as Owner"}
            </button>
          </div>
        </Modal>
      )}
      {report && (
        <Modal title={report.candidate.domain} onClose={() => setReport(null)}>
          {report.is_demo && <DemoBanner />}
          <div className="approval-summary">
            <Badge value={report.candidate.final_status} />
            <span>Domain Score: {report.candidate.domain_score}/100</span>
            <span>Rules {report.rule_version}</span>
          </div>
          <dl className="report-details">
            <dt>Source</dt>
            <dd>{report.candidate.source}</dd>
            <dt>Researched</dt>
            <dd>{date(report.candidate.research_timestamp)}</dd>
            <dt>Historical categories</dt>
            <dd>
              {report.candidate.historical_categories.join(", ") ||
                "None recorded"}
            </dd>
            <dt>Acquisition price</dt>
            <dd>
              {report.candidate.acquisition_price === null
                ? "Unknown"
                : `${report.candidate.acquisition_price} ${report.candidate.currency}`}
            </dd>
            <dt>Acquisition URL</dt>
            <dd>
              {report.candidate.acquisition_url ? (
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href={report.candidate.acquisition_url}
                >
                  View source <ExternalLink size={13} />
                </a>
              ) : (
                "Not available"
              )}
            </dd>
          </dl>
          {report.candidate.warnings.map((w, i) => (
            <p className="warning-note" key={i}>
              {w}
            </p>
          ))}
          {report.candidate.rejection_reasons.map((w, i) => (
            <p className="error" key={i}>
              {w}
            </p>
          ))}
          <h3>Research evidence</h3>
          {report.evidence.map((e) => (
            <article className="evidence" key={e.id}>
              <div>
                <strong>{e.check_type.replace("_", " ")}</strong>
                <Badge
                  value={
                    report.is_demo
                      ? "DEMO"
                      : e.verified
                        ? "VERIFIED"
                        : "UNVERIFIED"
                  }
                />
              </div>
              <p>{e.findings}</p>
              <small>
                {e.provider} · {date(e.observed_at)}
              </small>
              <code>{e.source_reference}</code>
            </article>
          ))}
        </Modal>
      )}
    </>
  );
}
