"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  FolderKanban,
  ShieldCheck,
  Bot,
  Activity,
  Settings,
  LogOut,
  Command,
  ChevronRight,
  Menu,
} from "lucide-react";
import { api, post } from "@/lib/api";
const nav = [
  ["Dashboard", "/", LayoutDashboard],
  ["Projects", "/projects", FolderKanban],
  ["Approvals", "/approvals", ShieldCheck],
  ["Agents", "/agents", Bot],
  ["Activity", "/activity", Activity],
  ["Settings", "/settings", Settings],
] as const;
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname(),
    router = useRouter();
  const [email, setEmail] = useState("");
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (path !== "/login")
      api<{ email: string }>("/auth/me")
        .then((u) => {
          setEmail(u.email);
          api<{ storage_backend: string }>("/settings")
            .then((s) => setPreview(s.storage_backend === "sqlite-preview"))
            .catch((e) => setError(e.message));
        })
        .catch((e) => setError(e.message));
  }, [path]);
  if (path === "/login") return children;
  return (
    <div className="app">
      <aside className={`sidebar ${open ? "mobile-open" : ""}`}>
        <Link href="/" className="brand">
          <span className="brand-mark">
            <Command size={21} />
          </span>
          <div>
            Commerce<span>CONTROL CENTER</span>
          </div>
        </Link>
        <div className="workspace">
          <span className="workspace-dot" />
          Owner workspace<span className="version">V1</span>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([label, href, Icon]) => (
            <Link
              onClick={() => setOpen(false)}
              key={href}
              href={href}
              className={
                (href === "/" ? path === "/" : path.startsWith(href))
                  ? "active"
                  : ""
              }
            >
              <Icon size={19} />
              {label}
              {label === "Dashboard" && <span className="nav-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="authority">
            <ShieldCheck size={18} />
            <div>
              <strong>Human authority, always</strong>
              <p>AI researches. You decide.</p>
            </div>
          </div>
          <div className="owner">
            <span className="avatar">O</span>
            <div>
              <strong>Owner</strong>
              <span title={email}>{email || "Authenticating…"}</span>
            </div>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={async () => {
                try {
                  await post("/auth/logout");
                  router.push("/login");
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div>
            <button
              className="mobile-toggle icon-button"
              aria-label="Toggle navigation"
              onClick={() => setOpen(!open)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {nav.find(
                ([, href]) => href !== "/" && path.startsWith(href),
              )?.[0] || "Dashboard"}
            </strong>
          </div>
          <span className="owner-pill">
            <ShieldCheck size={14} /> Owner access
          </span>
        </header>
        <main>
          {preview && (
            <div className="preview-banner">
              LOCAL PREVIEW · SQLite storage · Docker / PostgreSQL has not been
              verified on this machine.
            </div>
          )}
          {error ? (
            <div role="alert" className="error">
              {error}
            </div>
          ) : null}
          {email ? (
            children
          ) : (
            <div className="loading">Connecting to your workspace…</div>
          )}
        </main>
        <footer>
          Commerce Control Center{" "}
          <span>V1 · Self-hosted · Owner controlled</span>
        </footer>
      </div>
    </div>
  );
}
