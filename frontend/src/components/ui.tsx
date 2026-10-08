"use client";
import { useEffect, useRef } from "react";
import { FlaskConical, X, ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { Project, date } from "@/lib/api";
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value.toLowerCase()}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function DemoBanner() {
  return (
    <div className="demo-banner">
      <FlaskConical size={19} />
      <div>
        <strong>Synthetic demo research</strong>
        <span>
          These .example domains, scores and evidence are fixtures. No live
          provider was queried. They are not verified acquisition opportunities.
        </span>
      </div>
    </div>
  );
}
export function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div role="alert" className="error">
      {error}
    </div>
  ) : null;
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">◇</div>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function ProjectTable({ projects }: { projects: Project[] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Project</th>
            <th>Market</th>
            <th>Status</th>
            <th>Created</th>
            <th>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.id}>
              <td>
                <Link className="project-name" href={`/projects/${p.id}`}>
                  {p.name}
                </Link>
                <span className="cell-sub">{p.niche}</span>
              </td>
              <td>{p.market}</td>
              <td>
                <Badge value={p.status} />
              </td>
              <td className="muted">{date(p.created_at)}</td>
              <td>
                <Link aria-label={`Open ${p.name}`} href={`/projects/${p.id}`}>
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const prior = document.activeElement as HTMLElement;
    return () => {
      ref.current?.close();
      prior?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
