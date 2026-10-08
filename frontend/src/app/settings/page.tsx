"use client";
import { useEffect, useState } from "react";
import { api, Settings } from "@/lib/api";
import { PageTitle, Badge, ErrorBox } from "@/components/ui";
export default function Configuration() {
  const [settings, setSettings] = useState<Settings | null>(null),
    [error, setError] = useState(""),
    [email, setEmail] = useState("");
  useEffect(() => {
    Promise.all([
      api<Settings>("/settings"),
      api<{ email: string }>("/auth/me"),
    ])
      .then(([s, u]) => {
        setSettings(s);
        setEmail(u.email);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="WORKSPACE CONFIGURATION"
        title="Settings"
        description="Your account, research policy and integration status."
      />
      <ErrorBox error={error} />
      {settings && (
        <div className="settings-grid">
          <section className="card settings-card">
            <h2>Owner account</h2>
            <dl>
              <dt>Email</dt>
              <dd>{email}</dd>
              <dt>Role</dt>
              <dd>
                <Badge value="OWNER" />
              </dd>
              <dt>Approval authority</dt>
              <dd>Owner only · PASS candidates only</dd>
            </dl>
          </section>
          <section className="card settings-card">
            <h2>Research policy</h2>
            <dl>
              <dt>ScamAdviser minimum</dt>
              <dd>{settings.scamadviser_minimum}/100</dd>
              <dt>Candidates per run</dt>
              <dd>Maximum {settings.candidate_limit}</dd>
              <dt>Evaluation version</dt>
              <dd>{settings.rule_version}</dd>
              <dt>REVIEW / FAIL selection</dt>
              <dd>Blocked</dd>
            </dl>
          </section>
          <section className="card settings-card">
            <h2>Data sources</h2>
            <dl>
              <dt>Live providers</dt>
              <dd>Not configured</dd>
              <dt>Development fixtures</dt>
              <dd>
                <Badge
                  value={settings.fixtures_enabled ? "ENABLED" : "DISABLED"}
                />
              </dd>
            </dl>
            <p className="muted">
              Fixture data is synthetic. Legitimate provider integrations can be
              added through the backend interface.
            </p>
          </section>
          <section className="card settings-card">
            <h2>Security</h2>
            <dl>
              <dt>Database</dt>
              <dd>
                {settings.storage_backend === "sqlite-preview"
                  ? "SQLite (local preview only)"
                  : "PostgreSQL"}
              </dd>
              <dt>Purchases and payments</dt>
              <dd>Unavailable</dd>
              <dt>Secure cookie flag</dt>
              <dd>
                {settings.cookie_secure
                  ? "Enabled (HTTPS)"
                  : "Disabled (local HTTP)"}
              </dd>
              <dt>Secrets</dt>
              <dd>Server environment only</dd>
            </dl>
            <p className="muted">
              Configuration is managed by the server operator. Agents cannot
              edit these rules.
            </p>
          </section>
        </div>
      )}
    </>
  );
}
