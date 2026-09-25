"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import ThemeToggle from "@/components/ThemeToggle";
import { ApiError, api, type DemoAccount } from "@/lib/api";

const ROLE_ORDER = ["exec", "director", "ram"] as const;
const ROLE_LABEL = { exec: "Executives", director: "Directors", ram: "Account managers (RAM)" };
const ROLE_HINT = {
  exec: "All territories, pricing visible",
  director: "Own region, no pricing",
  ram: "Own territory, no pricing",
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [demo, setDemo] = useState<{ password: string | null; accounts: DemoAccount[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.me().then(() => router.replace("/")).catch(() => {});
    api.demoAccounts().then(setDemo).catch(() => {});
  }, [router]);

  const signIn = async (e?: React.FormEvent, as?: { email: string; password: string }) => {
    e?.preventDefault();
    const creds = as ?? { email, password };
    setSubmitting(true);
    setError(null);
    try {
      await api.login(creds.email, creds.password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Invalid email or password." : "Sign-in failed. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col">
      <div className="flex justify-end p-3">
        <ThemeToggle />
      </div>
      <div className="mx-auto grid w-full max-w-5xl flex-1 gap-10 px-4 pb-12 md:grid-cols-[minmax(0,380px)_1fr] md:items-start md:pt-[8vh]">
        <form onSubmit={signIn} className="space-y-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">NovaPharma Analytics</h1>
            <p className="mt-1 text-fg-secondary">Ask questions about commercial data in plain English.</p>
          </div>
          <label className="block text-sm">
            <span className="text-fg-secondary">Email</span>
            <input
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 outline-none focus:border-fg-muted"
            />
          </label>
          <label className="block text-sm">
            <span className="text-fg-secondary">Password</span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 outline-none focus:border-fg-muted"
            />
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-accent px-3 py-2 font-medium text-accent-fg hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {demo && demo.accounts.length > 0 && (
          <section>
            <h2 className="font-medium">Demo accounts</h2>
            <p className="mt-1 text-sm text-fg-secondary">
              Pick a user to sign in as them. Each role sees different data.
              {demo.password && (
                <>
                  {" "}Shared password: <code className="rounded bg-bg-muted px-1.5 py-0.5 font-mono text-xs">{demo.password}</code>
                </>
              )}
            </p>
            <div className="mt-4 space-y-5">
              {ROLE_ORDER.map((role) => {
                const accounts = demo.accounts.filter((a) => a.role === role);
                if (!accounts.length) return null;
                return (
                  <div key={role}>
                    <div className="mb-2 text-sm">
                      <span className="font-medium">{ROLE_LABEL[role]}</span>
                      <span className="text-fg-muted"> · {ROLE_HINT[role]}</span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {accounts.map((a) => (
                        <button
                          key={a.email}
                          disabled={submitting || !demo.password}
                          onClick={() => {
                            setEmail(a.email);
                            if (demo.password) signIn(undefined, { email: a.email, password: demo.password });
                          }}
                          className="rounded-lg border border-border bg-bg-elevated px-3 py-2 text-left hover:border-fg-muted disabled:opacity-60"
                        >
                          <div className="truncate text-sm font-medium">{a.full_name}</div>
                          <div className="truncate text-xs text-fg-muted">{a.scope_label}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
