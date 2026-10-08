"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck, ArrowRight } from "lucide-react";
import { api, Approval, Project, Run, date } from "@/lib/api";
import { PageTitle, Badge, Empty, ErrorBox } from "@/components/ui";
export default function Approvals() {
  const [items, setItems] = useState<Approval[]>([]),
    [projects, setProjects] = useState<Project[]>([]),
    [demo, setDemo] = useState<Record<string, boolean>>({}),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api<Approval[]>("/approvals"), api<Project[]>("/projects")])
      .then(async ([a, p]) => {
        setItems(a);
        setProjects(p);
        const histories = await Promise.all(
          [...new Set(a.map((x) => x.project_id))].map((id) =>
            api<Run[]>(`/projects/${id}/research`),
          ),
        );
        setDemo(
          Object.fromEntries(histories.flat().map((r) => [r.id, r.is_demo])),
        );
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="HUMAN AUTHORITY"
        title="Approvals"
        description="Important decisions stay with you. Only PASS domains can be approved."
      />
      <ErrorBox error={error} />
      <section className="decision-strip">
        <ShieldCheck size={25} />
        <div>
          <h3>Evidence before approval</h3>
          <p>Open a project to review its report and confirm your selection.</p>
        </div>
      </section>
      <section className="card">
        {loading ? (
          <p className="padded">Loading approvals…</p>
        ) : items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Decision</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>
                        {projects.find((p) => p.id === a.project_id)?.name ||
                          a.project_id}
                      </strong>
                      {demo[a.run_id] && (
                        <span className="cell-sub demo-text">
                          SYNTHETIC DEMO RESEARCH
                        </span>
                      )}
                    </td>
                    <td>Domain selection</td>
                    <td>
                      <Badge value={a.state} />
                    </td>
                    <td>{date(a.created_at)}</td>
                    <td>
                      <Link
                        className="text-button"
                        href={`/projects/${a.project_id}`}
                      >
                        {a.state === "PENDING" ? "Review" : "View decision"}
                        <ArrowRight size={15} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No decisions waiting">
            Approvals appear when research produces PASS or REVIEW candidates.
          </Empty>
        )}
      </section>
    </>
  );
}
