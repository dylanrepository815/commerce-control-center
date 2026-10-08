"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus,
  ArrowUpRight,
  FolderKanban,
  Search,
  ShieldCheck,
  CheckCheck,
  ArrowRight,
} from "lucide-react";
import { api, Project, Approval, Event, date } from "@/lib/api";
import { PageTitle, ProjectTable, Empty, ErrorBox } from "@/components/ui";
export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]),
    [approvals, setApprovals] = useState<Approval[]>([]),
    [events, setEvents] = useState<Event[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([
      api<Project[]>("/projects"),
      api<Approval[]>("/approvals"),
      api<Event[]>("/activity?limit=5"),
    ])
      .then(([p, a, e]) => {
        setProjects(p);
        setApprovals(a);
        setEvents(e);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const pending = approvals.filter((a) => a.state === "PENDING").length;
  return (
    <>
      <PageTitle
        eyebrow="YOUR OPERATIONS, AT A GLANCE"
        title="Dashboard"
        description="A clear view of your projects and the decisions that move them forward."
        action={
          <Link className="button primary" href="/projects/new">
            <Plus size={18} />
            New project
          </Link>
        }
      />
      <ErrorBox error={error} />
      <div className="stats">
        {[
          [
            "Total projects",
            projects.length,
            FolderKanban,
            "All projects in your workspace",
          ],
          [
            "In research",
            projects.filter((p) => p.status === "DOMAIN_RESEARCH").length,
            Search,
            "Preparing the right foundation",
          ],
          [
            "Awaiting decision",
            pending,
            ShieldCheck,
            "Your approval is required",
          ],
          [
            "Domains selected",
            projects.filter((p) => p.status === "BRAND_PENDING").length,
            CheckCheck,
            "Ready for the next stage",
          ],
        ].map(([name, count, Icon, note]) => {
          const Symbol = Icon as typeof Plus;
          return (
            <div className="stat" key={String(name)}>
              <div>
                {String(name)}
                <Symbol size={19} />
              </div>
              <strong>{loading ? "—" : String(count)}</strong>
              <small>{String(note)}</small>
            </div>
          );
        })}
      </div>
      <section className="decision-strip">
        <div className="decision-icon">
          <ShieldCheck size={24} />
        </div>
        <div>
          <h3>
            {pending
              ? `${pending} ${pending === 1 ? "project needs" : "projects need"} your review`
              : "You have the final say"}
          </h3>
          <p>
            {pending
              ? "Review the research and confirm a PASS domain when you are ready."
              : "Agents can research and recommend. Only you can approve a final domain."}
          </p>
        </div>
        <Link href="/approvals">
          Review approvals <ArrowRight size={17} />
        </Link>
      </section>
      <div className="dashboard-grid">
        <section className="card">
          <div className="card-heading">
            <h2>
              Recent projects <span className="count">{projects.length}</span>
            </h2>
            <Link href="/projects">
              View all <ArrowUpRight size={15} />
            </Link>
          </div>
          {loading ? (
            <p className="padded muted">Loading projects…</p>
          ) : projects.length ? (
            <ProjectTable projects={projects.slice(0, 5)} />
          ) : (
            <Empty title="Start with your first project">
              Define a market and niche, then explore domain research.
              <br />
              <Link className="button secondary" href="/projects/new">
                Create a project <ArrowRight size={16} />
              </Link>
            </Empty>
          )}
        </section>
        <section className="card">
          <div className="card-heading">
            <h2>Recent activity</h2>
            <Link href="/activity">
              <ArrowUpRight size={17} />
              <span className="sr-only">View activity</span>
            </Link>
          </div>
          {events.length ? (
            <div className="timeline">
              {events.map((e) => (
                <div key={e.id}>
                  <span
                    className={`timeline-dot ${e.outcome === "FAILURE" ? "failed" : ""}`}
                  />
                  <strong>
                    {e.action.replaceAll(".", " ").replaceAll("_", " ")}
                  </strong>
                  <small>
                    {e.actor_type} · {date(e.created_at)}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="A clear audit trail">
              Important actions will appear here.
            </Empty>
          )}
        </section>
      </div>
      <div className="workflow-note">
        <span className="eyebrow">THE V1 WORKFLOW</span>
        <div>
          <span>
            01 <strong>Domain research</strong>
          </span>
          <ArrowRight size={16} />
          <span>
            02 <strong>Owner selection</strong>
          </span>
          <ArrowRight size={16} />
          <span>
            03 <strong>Brand pending</strong>
          </span>
        </div>
      </div>
    </>
  );
}
