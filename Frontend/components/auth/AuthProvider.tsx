"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getCurrentProfile, loginUser, updateCurrentProfile, type AuthUser, type LoginRequest, type ProfileUpdate } from "@/lib/api-client";

const ACCESS_TOKEN_KEY = "road2hire_access_token";

type AuthSession = {
  profile: AuthUser;
  accessToken: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  isRestoring: boolean;
  signIn: (credentials: LoginRequest) => Promise<AuthUser>;
  updateProfile: (updates: ProfileUpdate) => Promise<AuthUser>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      try {
        const token = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);

        if (!token) return;

        const profile = await getCurrentProfile(token);

        if (!cancelled) {
          setSession({ profile, accessToken: token });
        }
      } catch {
        try {
          window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
        } catch {
          // Storage may be unavailable in restricted browser contexts.
        }
        if (!cancelled) setSession(null);
      } finally {
        if (!cancelled) setIsRestoring(false);
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  async function signIn(credentials: LoginRequest) {
    const token = await loginUser(credentials);
    const profile = await getCurrentProfile(token.access_token);

    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token.access_token);
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
    } finally {
      setSession(null);
    }
  }

  return (
    <AuthContext.Provider value={{ session, isRestoring, signIn, updateProfile, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}