"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, getCurrentProfile, loginUser, updateCurrentProfile, type AuthUser, type LoginRequest, type ProfileUpdate } from "@/lib/api-client";

const ACCESS_TOKEN_KEY = "road2hire_access_token";

type AuthSession = {
  profile: AuthUser;
  accessToken: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  isRestoring: boolean;
  restoreError: string | null;
  signIn: (credentials: LoginRequest) => Promise<AuthUser>;
  updateProfile: (updates: ProfileUpdate) => Promise<AuthUser>;
  signOut: () => void;
  retrySessionRestore: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      setIsRestoring(true);
      setRestoreError(null);

      let token: string | null;
      try {
        token = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
      } catch {
        if (!cancelled) {
          setSession(null);
          setRestoreError("This browser could not read the saved session. Enable session storage or sign in again.");
        }
        if (!cancelled) setIsRestoring(false);
        return;
      }

      if (!token) {
        if (!cancelled) setSession(null);
        if (!cancelled) setIsRestoring(false);
        return;
      }

      try {
        const profile = await getCurrentProfile(token);

        if (!cancelled) setSession({ profile, accessToken: token });
      } catch (error) {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          try {
            window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
          } catch {
            // The rejected token cannot be reused; storage may also be unavailable.
          }
          if (!cancelled) setSession(null);
        } else if (!cancelled) {
          setRestoreError("Your saved session could not be checked because the service is unavailable. Retry, or sign in again.");
        }
      } finally {
        if (!cancelled) setIsRestoring(false);
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, [restoreAttempt]);

  async function signIn(credentials: LoginRequest) {
    const token = await loginUser(credentials);
    const profile = await getCurrentProfile(token.access_token);

    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token.access_token);
    setRestoreError(null);
    setSession({ profile, accessToken: token.access_token });

    return profile;
  }

  async function updateProfile(updates: ProfileUpdate) {
    if (!session) throw new Error("Sign in to update your profile.");

    const profile = await updateCurrentProfile(updates, session.accessToken);
    setSession((current) => current ? { ...current, profile } : current);

    return profile;
  }

  function signOut() {
    try {
      window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    } catch {
      // Clear in-memory authentication even when browser storage is unavailable.
    }
    setRestoreError(null);
    setSession(null);
  }

  function retrySessionRestore() {
    setRestoreError(null);
    setIsRestoring(true);
    setRestoreAttempt((attempt) => attempt + 1);
  }

  return (
    <AuthContext.Provider value={{
      session,
      isRestoring,
      restoreError,
      signIn,
      updateProfile,
      signOut,
      retrySessionRestore,
    }}>
      <SessionRestoreBoundary>{children}</SessionRestoreBoundary>
    </AuthContext.Provider>
  );
}

function SessionRestoreBoundary({ children }: { children: ReactNode }) {
  const { isRestoring, restoreError, retrySessionRestore, signOut } = useAuth();

  if (isRestoring) {
    return (
      <main className="min-h-screen bg-background px-4 py-16 sm:px-6" role="status" aria-live="polite">
        <div className="mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-700 shadow-sm">
          Restoring your session…
        </div>
      </main>
    );
  }

  if (restoreError) {
    return (
      <main className="min-h-screen bg-background px-4 py-16 sm:px-6">
        <section className="mx-auto max-w-lg rounded-2xl border border-amber-200 bg-white p-6 shadow-sm" aria-labelledby="session-restore-error-heading">
          <h1 id="session-restore-error-heading" className="text-xl font-semibold text-slate-900">Session could not be restored</h1>
          <p className="mt-2 text-sm leading-6 text-amber-900" role="alert">{restoreError}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button type="button" onClick={retrySessionRestore} className="min-h-11 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
              Retry session check
            </button>
            <button type="button" onClick={signOut} className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-2">
              Clear session and sign in
            </button>
          </div>
        </section>
      </main>
    );
  }

  return children;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
