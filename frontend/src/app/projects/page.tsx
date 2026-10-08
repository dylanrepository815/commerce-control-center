"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search } from "lucide-react";
import { api, Project } from "@/lib/api";
import { PageTitle, ProjectTable, Empty, ErrorBox } from "@/components/ui";
export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]),
    [query, setQuery] = useState(""),
    [status, setStatus] = useState("ALL"),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    api<Project[]>("/projects")
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const filtered = projects.filter(
    (p) =>
      (status === "ALL" || p.status === status) &&
      `${p.name} ${p.market} ${p.niche}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        eyebrow="PROJECTS / CRM"
        title="Projects"
        description="Every venture starts with a market, a niche and a good foundation."
        action={
          <Link className="button primary" href="/projects/new">
            <Plus size={18} />
            New project
          </Link>
        }
      />
      <ErrorBox error={error} />
      <section className="card">
        <div className="toolbar">
          <label className="search">
            <Search size={18} />
            <input
              aria-label="Search projects"
              placeholder="Search projects, markets or niches…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="ALL">All statuses</option>
            {["DOMAIN_RESEARCH", "DOMAIN_SELECTION", "BRAND_PENDING"].map(
              (s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ),
            )}
          </select>
        </div>
        {loading ? (
          <p className="padded">Loading projects…</p>
        ) : filtered.length ? (
          <ProjectTable projects={filtered} />
        ) : (
          <Empty
            title={
              projects.length
                ? "No matching projects"
                : "Your next venture starts here"
            }
          >
            {projects.length
              ? "Try a different search or status."
              : "Create your first project to get started."}
          </Empty>
        )}
      </section>
    </>
  );
}
