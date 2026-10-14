"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, KeyRound, Save } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Category = "llm" | "discovery" | "enrichment" | "verification" | "email" | "calendar";
type ProviderMap = Record<Category, string>;
type OptionMap = Record<string, string | number>;

type Integration = {
  id: Category;
  name: string;
  type: string;
  provider: string;
  status: "mock" | "configured" | "not_configured";
  credential_source: "organization" | "environment" | "none";
  purpose: string;
};

type SettingsResponse = {
  integrations: Integration[];
  integration_config: { providers: ProviderMap; options: OptionMap };
  available_providers: Record<Category, string[]>;
  credential_configured: Record<string, boolean>;
  can_manage_integrations: boolean;
};

const categoryLabels: Record<Category, string> = {
  llm: "Language model",
  discovery: "Company discovery",
  enrichment: "Contact enrichment",
  verification: "Email verification",
  email: "Outbound email",
  calendar: "Calendar",
};

const secretFor: Partial<Record<Category, Record<string, string>>> = {
  llm: { gemini: "gemini_api_key", groq: "groq_api_key" },
  discovery: { serpapi: "serpapi_api_key", tavily: "tavily_api_key" },
  enrichment: { apollo: "apollo_api_key", hunter: "hunter_api_key" },
  verification: { hunter: "hunter_api_key" },
  email: { resend: "resend_api_key", smtp: "smtp_password" },
  calendar: {
    google: "google_calendar_client_secret",
  },
};

const optionLabels: Record<string, string> = {
  llm_model: "Model",
  calendar_id: "Google Calendar ID",
  google_calendar_client_id: "Google OAuth client ID",
  resend_from_email: "From email",
  smtp_host: "SMTP host",
  smtp_port: "SMTP port",
  smtp_user: "SMTP username",
  smtp_from_email: "SMTP from email",
};

function categoryOptions(category: Category, provider: string): string[] {
  if (category === "llm") return ["llm_model"];
  if (category === "calendar" && provider === "google") {
    return ["calendar_id", "google_calendar_client_id"];
  }
  if (category === "email" && provider === "resend") return ["resend_from_email"];
  if (category === "email" && provider === "smtp") {
    return ["smtp_host", "smtp_port", "smtp_user", "smtp_from_email"];
  }
  return [];
}

function secretLabels(secretName: string): string {
  const labels: Record<string, string> = {
    gemini_api_key: "Gemini API key",
    groq_api_key: "Groq API key",
    serpapi_api_key: "SerpAPI key",
    tavily_api_key: "Tavily API key",
    apollo_api_key: "Apollo API key",
    hunter_api_key: "Hunter API key",
    resend_api_key: "Resend API key",
    smtp_password: "SMTP password or app password",
    google_calendar_client_secret: "Google OAuth client secret",
    google_calendar_refresh_token: "Google OAuth refresh token",
  };
  return labels[secretName] ?? "Credential";
}

export function IntegrationConfigurationPanel() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [providers, setProviders] = useState<ProviderMap | null>(null);
  const [options, setOptions] = useState<OptionMap>({});
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [editedSecrets, setEditedSecrets] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await apiFetch("/api/v1/settings/status");
        if (!response.ok) throw new Error(`Could not load settings (HTTP ${response.status}).`);
        const value = await response.json() as SettingsResponse;
        if (!active) return;
        setSettings(value);
        setProviders(value.integration_config.providers);
        setOptions(value.integration_config.options);
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Could not load integration settings.");
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  const integrationById = useMemo(
    () => new Map(settings?.integrations.map((integration) => [integration.id, integration]) ?? []),
    [settings],
  );

  function updateOption(key: string, value: string | number) {
    setOptions((current) => ({ ...current, [key]: value }));
  }

  function updateSecret(key: string, value: string) {
    setSecrets((current) => ({ ...current, [key]: value }));
    setEditedSecrets((current) => new Set(current).add(key));
  }

  async function saveIntegrations(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!providers) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const secretUpdates = Object.fromEntries(
        [...editedSecrets].map((key) => [key, secrets[key] ?? ""]),
      );
      const response = await apiFetch("/api/v1/settings/integrations", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ providers, options, secrets: secretUpdates }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Could not save integrations (HTTP ${response.status}).`);
      }
      const value = await response.json() as SettingsResponse;
      setSettings(value);
      setProviders(value.integration_config.providers);
      setOptions(value.integration_config.options);
      setSecrets({});
      setEditedSecrets(new Set());
      setSaved(true);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save integrations.");
    } finally {
      setSaving(false);
    }
  }

  function renderOption(key: string) {
    const isNumber = key === "smtp_port";
    return (
      <label key={key} className="block text-xs font-semibold text-textPrimary">
        {optionLabels[key]}
        <input
          type={isNumber ? "number" : "text"}
          min={isNumber ? 1 : undefined}
          max={isNumber ? 65535 : undefined}
          value={options[key] ?? ""}
          onChange={(event) => updateOption(
            key,
            isNumber ? Number(event.target.value) : event.target.value,
          )}
          className="mt-2 w-full rounded-xl border border-borderLine bg-card px-3 py-2.5 text-sm outline-none focus:border-accent"
        />
      </label>
    );
  }

  function renderSecret(key: string) {
    const configured = settings?.credential_configured[key] ?? false;
    return (
      <div key={key}>
        <label className="block text-xs font-semibold text-textPrimary">
          {secretLabels(key)}
          <input
            type="password"
            autoComplete="new-password"
            value={secrets[key] ?? ""}
            placeholder={configured ? "Saved securely — enter a new value to replace" : "Not configured"}
            onChange={(event) => updateSecret(key, event.target.value)}
            className="mt-2 w-full rounded-xl border border-borderLine bg-card px-3 py-2.5 text-sm outline-none focus:border-accent"
          />
        </label>
        {configured && (
          <button
            type="button"
            onClick={() => updateSecret(key, "")}
            className="mt-1 text-[11px] font-semibold text-red-400 hover:underline"
          >
            Remove saved credential
          </button>
        )}
      </div>
    );
  }

  if (!providers) {
    return (
      <section className="rounded-[2rem] border border-borderLine bg-card p-8">
        <h2 className="text-xl font-bold text-textPrimary">Integration configuration</h2>
        <p className="mt-3 text-sm text-textSecondary">{error ?? "Loading provider settings…"}</p>
      </section>
    );
  }

  const categories = Object.keys(categoryLabels) as Category[];

  return (
    <section className="rounded-[2rem] border border-borderLine bg-card p-8 shadow-sm">
      <div className="mb-6 flex items-start gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accentLight text-accent">
          <KeyRound className="h-4 w-4" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-textPrimary">Integrations</h2>
          <p className="mt-1 text-xs text-textSecondary">
            Configure providers for this organization. Credentials are encrypted by the backend and never returned to the browser.
          </p>
        </div>
      </div>

      {!settings?.can_manage_integrations && (
        <p className="mb-5 rounded-xl bg-amber-500/10 p-4 text-sm text-amber-500">
          Only organization owners and admins can change integration settings.
        </p>
      )}
      {error && (
        <p role="alert" className="mb-5 rounded-xl bg-red-400/10 p-4 text-sm text-red-400">
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="mb-5 flex items-center gap-2 rounded-xl bg-success/10 p-4 text-sm text-success">
          <CheckCircle2 className="h-4 w-4" /> Integration settings saved.
        </p>
      )}

      <form onSubmit={saveIntegrations} className="space-y-5">
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {categories.map((category) => {
            const provider = providers[category];
            const integration = integrationById.get(category);
            const secretKey = secretFor[category]?.[provider];
            const specialSecrets = category === "calendar" && provider === "google"
              ? ["google_calendar_client_secret", "google_calendar_refresh_token"]
              : [];
            const optionsForCategory = categoryOptions(category, provider);
            return (
              <article key={category} className="rounded-2xl border border-borderLine bg-background p-5">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-textPrimary">{categoryLabels[category]}</h3>
                    <p className="mt-1 text-[11px] text-textSecondary">{integration?.purpose}</p>
                  </div>
                  <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold ${
                    integration?.status === "configured"
                      ? "bg-success/10 text-success"
                      : integration?.status === "mock"
                        ? "bg-accentLight text-accent"
                        : "bg-red-400/10 text-red-400"
                  }`}>
                    {integration?.status === "configured"
                      ? `Configured · ${integration.credential_source}`
                      : integration?.status === "mock"
                        ? "Mock mode"
                        : "Needs configuration"}
                  </span>
                </div>

                <label className="block text-xs font-semibold text-textPrimary">
                  Provider
                  <select
                    value={provider}
                    onChange={(event) => setProviders((current) => current
                      ? { ...current, [category]: event.target.value }
                      : current)}
                    className="mt-2 w-full rounded-xl border border-borderLine bg-card px-3 py-2.5 text-sm outline-none focus:border-accent"
                  >
                    {(settings?.available_providers[category] ?? []).map((value) => (
                      <option key={value} value={value}>{value.toUpperCase()}</option>
                    ))}
                  </select>
                </label>

                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {optionsForCategory.map(renderOption)}
                  {secretKey && renderSecret(secretKey)}
                  {specialSecrets.map(renderSecret)}
                  {category === "email" && provider === "smtp" && renderSecret("smtp_password")}
                </div>

                {category === "calendar" && provider === "google" && (
                  <p className="mt-3 text-[11px] text-textSecondary">
                    Google Calendar requires an OAuth client ID, client secret, and refresh token from your Google Cloud OAuth setup.
                  </p>
                )}
              </article>
            );
          })}
        </div>

        <div className="flex flex-col justify-between gap-4 border-t border-borderLine pt-5 sm:flex-row sm:items-center">
          <p className="max-w-2xl text-[11px] text-textSecondary">
            Application encryption key must be configured by the operator. Use HTTPS in production and restrict credentials to trusted organization admins.
          </p>
          <button
            type="submit"
            disabled={saving || !settings?.can_manage_integrations}
            className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-xs font-bold text-card hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save integrations"}
          </button>
        </div>
      </form>
    </section>
  );
}
