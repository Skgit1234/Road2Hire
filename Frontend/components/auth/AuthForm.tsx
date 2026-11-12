"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { registerUser, type ProfileUpdate } from "@/lib/api-client";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const isLogin = mode === "login";
  const { session, isRestoring, signIn, signOut, updateProfile } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [profileError, setProfileError] = useState("");
  const [profileMessage, setProfileMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setIsLoading(true);

    const form = event.currentTarget;
    const formData = new FormData(form);
    const email = String(formData.get("email") ?? "").trim();
    const password = String(formData.get("password") ?? "");

    try {
      if (isLogin) {
        const profile = await signIn({ email, password });
        setMessage(`Signed in as ${profile.email}.`);
      } else {
        const name = String(formData.get("name") ?? "").trim();
        const profile = await registerUser({ name, email, password });
        setMessage(`Account created for ${profile.email}. Sign in to continue.`);
        form.reset();
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The request could not be completed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitProfileUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setProfileError("");
    setProfileMessage("");
    setIsProfileLoading(true);
    const formData = new FormData(event.currentTarget);
    const name = String(formData.get("profile-name") ?? "").trim();
    const email = String(formData.get("profile-email") ?? "").trim();
    const updates: ProfileUpdate = {};
    if (name && name !== session.profile.name) updates.name = name;
    if (email && email !== session.profile.email) updates.email = email;

    try {
      if (Object.keys(updates).length === 0) throw new Error("Change your name or email before saving.");
      const profile = await updateProfile(updates);
      setProfileMessage(`Profile updated for ${profile.email}.`);
    } catch (requestError) {
      setProfileError(requestError instanceof Error ? requestError.message : "The profile could not be updated.");
    } finally {
      setIsProfileLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 pb-8 pt-16 sm:px-6 md:py-8 lg:px-8">
      <div className="mx-auto max-w-lg">
        <header className="mb-6">
          <p className="text-sm font-semibold text-primary">Road2Hire account</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            {isLogin ? "Sign in" : "Create your account"}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {isLogin ? "Sign in to load your backend profile." : "Register with your name, email, and password."}
          </p>
        </header>

        {isRestoring ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" role="status" aria-live="polite">
            <p className="text-sm text-slate-600">Restoring your session…</p>
          </section>
        ) : session && isLogin ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" aria-live="polite">
            <p className="font-semibold text-emerald-700">Signed in as {session.profile.name}.</p>
            <p className="mt-1 text-sm text-slate-600">{session.profile.email}</p>
            <form onSubmit={submitProfileUpdate} className="mt-5 space-y-3 border-t border-slate-200 pt-5">
              <h2 className="text-sm font-semibold text-slate-800">Update profile</h2>
              <label className="block text-sm font-medium text-slate-700">
                Name
                <input name="profile-name" type="text" autoComplete="name" defaultValue={session.profile.name} required maxLength={100} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Email
                <input name="profile-email" type="email" autoComplete="email" defaultValue={session.profile.email} required className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
              </label>
              {profileError && <p role="alert" className="text-sm text-rose-700">{profileError}</p>}
              {profileMessage && <p role="status" className="text-sm text-emerald-700">{profileMessage}</p>}
              <button type="submit" disabled={isProfileLoading} className="min-h-10 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60">
                {isProfileLoading ? "Saving…" : "Save profile"}
              </button>
            </form>
            <button type="button" onClick={signOut} className="mt-5 text-sm font-semibold text-indigo-700 underline">
              Sign out
            </button>
          </section>
        ) : (
          <form onSubmit={submit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            {!isLogin && (
              <label className="block text-sm font-medium text-slate-700">
                Name
                <input name="name" type="text" autoComplete="name" required maxLength={100} className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
              </label>
            )}
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input name="email" type="email" autoComplete="email" required className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Password
              <input name="password" type="password" autoComplete={isLogin ? "current-password" : "new-password"} required className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 px-3" />
            </label>

            {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
            {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}

            <button type="submit" disabled={isLoading} className="min-h-11 w-full rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-wait disabled:opacity-60">
              {isLoading ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
            </button>
          </form>
        )}

        <p className="mt-5 text-sm text-slate-600">
          {isLogin ? "New to Road2Hire? " : "Already have an account? "}
          <Link href={isLogin ? "/register" : "/login"} className="font-semibold text-indigo-700 underline">
            {isLogin ? "Create an account" : "Sign in"}
          </Link>
        </p>
        {!isLogin && message && (
          <p className="mt-2 text-sm">
            <Link href="/login" className="font-semibold text-indigo-700 underline">Continue to sign in</Link>
          </p>
        )}
        <p className="mt-5 text-xs leading-5 text-slate-500">
          Your sign-in stays active in this tab when you refresh. Signing out clears this tab&apos;s session.
        </p>
      </div>
    </main>
  );
}
