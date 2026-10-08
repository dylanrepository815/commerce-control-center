"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Search, ShieldCheck } from "lucide-react";
import { post, Project } from "@/lib/api";
import { PageTitle, ErrorBox } from "@/components/ui";
export default function NewProject() {
  const router = useRouter(),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <>
      <Link className="back-link" href="/projects">
        <ArrowLeft size={15} />
        All projects
      </Link>
      <PageTitle
        eyebrow="BUILD SOMETHING NEW"
        title="New project"
        description="Set the direction. Your research starts here."
      />
      <div className="form-grid">
        <form
          className="card project-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            const data = new FormData(e.currentTarget);
            try {
              const p = await post<Project>("/projects", {
                name: data.get("name"),
                market: data.get("market"),
                niche: data.get("niche"),
              });
              router.push(`/projects/${p.id}`);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Project details</h2>
          <p className="muted">Give your project a clear starting point.</p>
          <ErrorBox error={error} />
          <label>
            Project name
            <input
              name="name"
              required
              maxLength={150}
              placeholder="e.g. Everyday Essentials"
            />
          </label>
          <label>
            Market / Country
            <input
              name="market"
              required
              maxLength={100}
              placeholder="e.g. Netherlands"
            />
            <small>The market this business will serve.</small>
          </label>
          <label>
            Niche
            <input
              name="niche"
              required
              maxLength={200}
              placeholder="e.g. Sustainable home accessories"
            />
            <small>A focused niche helps guide domain research.</small>
          </label>
          <div className="form-actions">
            <Link className="button secondary" href="/projects">
              Cancel
            </Link>
            <button className="button primary" disabled={busy}>
              {busy ? "Creating…" : "Create project"}
              <ArrowRight size={17} />
            </button>
          </div>
        </form>
        <aside className="info-card">
          <Search size={25} />
          <h3>What happens next?</h3>
          <p>
            Your project begins in <strong>Domain Research</strong>. Review
            candidates, inspect the evidence and choose a domain that passes
            every required check.
          </p>
          <hr />
          <ShieldCheck size={22} />
          <h3>Your decision, on record</h3>
          <p>
            Only the Owner can confirm a PASS domain. Every approval is recorded
            in the activity log.
          </p>
        </aside>
      </div>
    </>
  );
}
