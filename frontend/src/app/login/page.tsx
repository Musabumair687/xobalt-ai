"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, storeAccessToken } from "@/lib/api";

type LoginResponse = {
  access_token: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Login failed (HTTP ${response.status}).`);
      }

      const result = await response.json() as LoginResponse;
      storeAccessToken(result.access_token);
      router.replace("/");
    } catch (loginError) {
      setError(
        loginError instanceof Error
          ? loginError.message
          : "Could not connect to the backend.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-12">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-3xl border border-borderLine bg-card p-8 shadow-sm"
      >
        <div className="mb-8">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Xobalt AI</p>
          <h1 className="mt-3 text-2xl font-bold text-textPrimary">Sign in to your workspace</h1>
          <p className="mt-2 text-sm text-textSecondary">
            Use the account provisioned for your organization.
          </p>
        </div>

        <label className="mb-5 block text-sm font-semibold text-textPrimary">
          Email
          <input
            autoComplete="username"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-xl border border-borderLine bg-background px-4 py-3 text-sm outline-none focus:border-accent"
          />
        </label>

        <label className="mb-5 block text-sm font-semibold text-textPrimary">
          Password
          <input
            autoComplete="current-password"
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-xl border border-borderLine bg-background px-4 py-3 text-sm outline-none focus:border-accent"
          />
        </label>

        {error && (
          <p role="alert" className="mb-5 rounded-xl bg-red-400/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-accent px-4 py-3 text-sm font-bold text-card transition-opacity hover:opacity-90 disabled:cursor-wait disabled:opacity-60"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
