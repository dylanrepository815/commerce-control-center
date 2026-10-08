"use client";
import { useEffect, useState } from "react";
import { api, Event, Project, date } from "@/lib/api";
import { PageTitle, Badge, Empty, ErrorBox } from "@/components/ui";
export default function Activity() {
  const [events, setEvents] = useState<Event[]>([]),
    [projects, setProjects] = useState<Project[]>([]),
    [project, setProject] = useState(""),
    [offset, setOffset] = useState(0),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    setProject(
      new URLSearchParams(window.location.search).get("project") || "",
    );
    api<Project[]>("/projects")
      .then(setProjects)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setLoading(true);
    api<Event[]>(
      `/activity?offset=${offset}&limit=30${project ? `&project_id=${project}` : ""}`,
    )
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [project, offset]);
  return (
    <>
      <PageTitle
        eyebrow="TRANSPARENCY BY DEFAULT"
        title="Activity log"
        description="A chronological record of actions, research, approvals and errors."
      />
      <ErrorBox error={error} />
      <section className="card">
        <div className="toolbar">
          <strong>Audit trail</strong>
          <select
            aria-label="Filter activity by project"
            value={project}
            onChange={(e) => {
              setProject(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All projects and system events</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        {loading ? (
          <p className="padded">Loading activity…</p>
        ) : events.length ? (
          <div className="audit-list">
            {events.map((e) => (
              <details key={e.id}>
                <summary>
                  <span className="audit-mark" />
                  <div>
                    <strong>
                      {e.action.replaceAll(".", " ").replaceAll("_", " ")}
                    </strong>
                    <small>
                      {e.actor_type} ·{" "}
                      {e.project_id
                        ? projects.find((p) => p.id === e.project_id)?.name ||
                          e.project_id
                        : "System"}
                      {e.details.is_demo ? " · DEMO" : ""}
                    </small>
                  </div>
                  <Badge value={e.outcome} />
                  <time>{date(e.created_at)}</time>
                </summary>
                <div className="audit-detail">
                  <p>
                    Actor: <code>{e.actor_id}</code>
                  </p>
                  <p>
                    Request: <code>{e.request_id}</code>
                  </p>
                  <pre>{JSON.stringify(e.details, null, 2)}</pre>
                </div>
              </details>
            ))}
          </div>
        ) : (
          <Empty title="No events in this view">
            Try another project filter.
          </Empty>
        )}
        <div className="pagination">
          <button
            className="button secondary compact"
            disabled={offset === 0 || loading}
            onClick={() => setOffset(Math.max(0, offset - 30))}
          >
            Previous
          </button>
          <span>Page {offset / 30 + 1}</span>
          <button
            className="button secondary compact"
            disabled={events.length < 30 || loading}
            onClick={() => setOffset(offset + 30)}
          >
            Next
          </button>
        </div>
      </section>
    </>
  );
}
