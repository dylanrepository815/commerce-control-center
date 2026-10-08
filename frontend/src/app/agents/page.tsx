"use client";
import { useEffect, useState } from "react";
import { Bot, LockKeyhole } from "lucide-react";
import { api } from "@/lib/api";
import { PageTitle, Badge, ErrorBox } from "@/components/ui";
type Agent = {
  id: string;
  key: string;
  name: string;
  enabled: boolean;
  capabilities: string[];
};
export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    api<Agent[]>("/agents")
      .then(setAgents)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="BOUNDED CAPABILITIES"
        title="Agents"
        description="Registered agents and the permissions that define their work."
      />
      <ErrorBox error={error} />
      <div className="agent-grid">
        {agents.map((a) => (
          <section className="card agent-card" key={a.id}>
            <div className="agent-top">
              <span className="agent-icon">
                <Bot size={27} />
              </span>
              <Badge value={a.enabled ? "ENABLED" : "DISABLED"} />
            </div>
            <h2>{a.name}</h2>
            <p>
              Research domain candidates, submit evidence and recommend options
              for Owner review.
            </p>
            <div className="capabilities">
              {a.capabilities.map((c) => (
                <code key={c}>{c}</code>
              ))}
            </div>
            <hr />
            <small>
              {a.enabled
                ? "Credentials are scoped to a specific project."
                : "Registered interface only. No live AI or provider is configured."}
            </small>
          </section>
        ))}
      </div>
      <div className="policy-note">
        <LockKeyhole size={20} />
        <div>
          <strong>Restricted by the backend</strong>
          <p>
            Agents cannot approve domains, make purchases, enter payment
            details, start paid advertising or modify security rules.
          </p>
        </div>
      </div>
    </>
  );
}
