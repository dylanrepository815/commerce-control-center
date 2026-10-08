"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Command, ShieldCheck, ArrowRight } from "lucide-react";
import { post } from "@/lib/api";
import { ErrorBox } from "@/components/ui";
export default function Login() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login-page">
      <div className="login-story">
        <span className="brand-mark">
          <Command size={28} />
        </span>
        <div>
          <div className="eyebrow">COMMERCE CONTROL CENTER</div>
          <h1>
            Your company.
            <br />
            Your decisions.
          </h1>
          <p>
            A focused workspace for AI-assisted research,
            <br />
            with you in control of every important step.
          </p>
        </div>
        <span>
          <ShieldCheck size={18} /> Research with AI. Approve as Owner.
        </span>
      </div>
      <div className="login-panel">
        <form
          className="login-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            const data = new FormData(e.currentTarget);
            try {
              await post("/auth/login", {
                email: data.get("email"),
                password: data.get("password"),
              });
              router.push("/");
              router.refresh();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="eyebrow">OWNER WORKSPACE</div>
          <h2>Welcome back</h2>
          <p>Sign in to your control center.</p>
          <ErrorBox error={error} />
          <label>
            Email address
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              placeholder="owner@company.com"
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              placeholder="Enter your password"
            />
          </label>
          <button className="button primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
            <ArrowRight size={17} />
          </button>
          <div className="setup-note">
            First time here? Create the initial Owner using the setup command in
            the README. There is no public registration.
          </div>
        </form>
      </div>
    </div>
  );
}
