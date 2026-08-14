"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FormField, Input } from "@/components/ui/FormField";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-8">
      <p className="font-mono text-xs uppercase tracking-widest text-text-muted">#00 — ACCESS</p>
      <h1 className="font-display text-3xl font-bold leading-none text-text-primary">Log in</h1>
      <p className="mt-2 text-sm text-text-muted">Monitor and diagnose your HVAC fleet.</p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <FormField label="Email" htmlFor="email">
          <Input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </FormField>
        <FormField label="Password" htmlFor="password">
          <Input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </FormField>
        {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
        <Button type="submit" disabled={submitting} className="mt-2 w-full">
          {submitting ? "Logging in…" : "Log in"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-text-muted">
        No account?{" "}
        <Link href="/signup" className="font-medium text-accent-brand-ink hover:underline">
          Sign up
        </Link>
      </p>
    </Card>
  );
}
