"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";

const navigation = [
  { name: "Dashboard", href: "/" },
  { name: "Resume", href: "/resume" },
  { name: "Skill Gap", href: "/skill-gap" },
  { name: "Career Readiness", href: "/career-readiness" },
  { name: "Learning Roadmap", href: "/learning-roadmap" },
  { name: "AI Career Assistant", href: "/career-assistant" },
  { name: "Sign in", href: "/login" },
];

const secondaryNavigation = [
  { name: "Calendar" },
  { name: "Saved Items" },
  { name: "Settings" },
  { name: "Help & Support" },
];

function NavIcon({ name, active = false }: { name: string; active?: boolean }) {
  const stroke = active ? "currentColor" : "currentColor";
  const sharedProps = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke,
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className: "h-4 w-4",
    "aria-hidden": true,
  };

  switch (name) {
    case "Dashboard":
      return (
        <svg {...sharedProps}>
          <path d="M4 11.5 12 4l8 7.5" />
          <path d="M6.5 9.5V18h11v-8.5" />
        </svg>
      );
    case "Resume":
      return (
        <svg {...sharedProps}>
          <path d="M7 4.5h6l4 4V18a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z" />
          <path d="M13 4.5v4h4" />
          <path d="M8.5 12.5h7M8.5 15.5h7" />
        </svg>
      );
    case "Skill Gap":
      return (
        <svg {...sharedProps}>
          <path d="M5 18.5V9.5M12 18.5V5.5M19 18.5v-8" />
          <path d="M3.5 18.5h17" />
        </svg>
      );
    case "Career Readiness":
      return (
        <svg {...sharedProps}>
          <path d="M4.5 15.5V9.5h3v6M10.5 15.5V6.5h3v9M16.5 15.5v-4h3v4" />
        </svg>
      );
    case "Learning Roadmap":
      return (
        <svg {...sharedProps}>
          <path d="M6 18V7.5A2.5 2.5 0 0 1 8.5 5H18" />
          <path d="M6 18a2.5 2.5 0 0 1 0-5h12" />
          <path d="M11 14.5h7M11 10.5h7" />
        </svg>
      );
    case "AI Career Assistant":
      return (
        <svg {...sharedProps}>
          <path d="M12 3.5a8.5 8.5 0 0 1 8 5.5 8.5 8.5 0 0 1-8 13 8.5 8.5 0 0 1-8-13 8.5 8.5 0 0 1 8-5.5Z" />
          <path d="M8 12.5h8M12 8.5v8" />
        </svg>
      );
    case "Calendar":
      return (
        <svg {...sharedProps}>
          <rect x="3.5" y="5.5" width="17" height="15" rx="2" />
          <path d="M7.5 3.5v4M16.5 3.5v4M3.5 9.5h17" />
        </svg>
      );
    case "Saved Items":
      return (
        <svg {...sharedProps}>
          <path d="M7 4.5h10a2 2 0 0 1 2 2v13l-7-4-7 4v-13a2 2 0 0 1 2-2Z" />
        </svg>
      );
    case "Settings":
      return (
        <svg {...sharedProps}>
          <path d="M12 3.5v3M12 17.5v3M4.5 12h3M16.5 12h3M6.3 6.3l2.1 2.1M15.6 15.6l2.1 2.1M17.7 6.3l-2.1 2.1M8.4 15.6l-2.1 2.1" />
          <circle cx="12" cy="12" r="3.2" />
        </svg>
      );
    case "Help & Support":
      return (
        <svg {...sharedProps}>
          <circle cx="12" cy="12" r="8.5" />
          <path d="M9.5 9a2.5 2.5 0 1 1 4.1 2c-1 .9-1.6 1.4-1.6 2.7" />
          <path d="M12 17.5h.01" />
        </svg>
      );
    default:
      return (
        <svg {...sharedProps}>
          <circle cx="12" cy="12" r="8.5" />
        </svg>
      );
  }
}

export default function Sidebar() {
  const { session, signOut } = useAuth();
  const pathname = usePathname();
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isMobileViewport, setIsMobileViewport] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const shouldRestoreFocus = useRef(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const updateViewport = () => setIsMobileViewport(mediaQuery.matches);
    updateViewport();
    mediaQuery.addEventListener("change", updateViewport);
    return () => mediaQuery.removeEventListener("change", updateViewport);
  }, []);

  useEffect(() => {
    if (!isMobileViewport) return;
    if (isMobileSidebarOpen) {
      sidebarRef.current?.querySelector<HTMLElement>("[data-mobile-first-focus]")?.focus();
    } else if (shouldRestoreFocus.current) {
      toggleRef.current?.focus();
      shouldRestoreFocus.current = false;
    }
  }, [isMobileSidebarOpen, isMobileViewport]);

  useEffect(() => {
    if (!isMobileViewport || !isMobileSidebarOpen) return;

    function handleDrawerKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMobileSidebar();
        return;
      }

      if (event.key !== "Tab") return;
      const sidebarLinks = Array.from(
        sidebarRef.current?.querySelectorAll<HTMLElement>("a[href], button:not(:disabled)") ?? [],
      );
      const focusable = [toggleRef.current, ...sidebarLinks].filter(
        (element): element is HTMLElement => element !== null,
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }

    document.addEventListener("keydown", handleDrawerKeyDown);
    return () => document.removeEventListener("keydown", handleDrawerKeyDown);
  }, [isMobileSidebarOpen, isMobileViewport]);

  function closeMobileSidebar() {
    shouldRestoreFocus.current = true;
    setIsMobileSidebarOpen(false);
  }

  const getIsActive = (href: string) =>
    pathname === href || (href !== "/" && pathname.startsWith(href));

  return (
    <>
      <button
        ref={toggleRef}
        type="button"
        aria-label={isMobileSidebarOpen ? "Close navigation" : "Open navigation"}
        aria-expanded={isMobileSidebarOpen}
        aria-controls="sidebar-navigation"
        aria-haspopup="dialog"
        onClick={() => {
          if (isMobileSidebarOpen) closeMobileSidebar();
          else setIsMobileSidebarOpen(true);
        }}
        className="fixed left-4 top-4 z-50 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-slate-100 shadow-lg transition hover:bg-slate-800 md:hidden"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
          <path d="M4 7.5h16M4 12h16M4 16.5h16" strokeLinecap="round" />
        </svg>
      </button>

      {isMobileSidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation overlay"
          aria-hidden="true"
          tabIndex={-1}
          onClick={closeMobileSidebar}
          className="fixed inset-0 z-30 bg-slate-950/35 md:hidden"
        />
      ) : null}

      <aside
        ref={sidebarRef}
        id="sidebar-navigation"
        role={isMobileViewport ? "dialog" : "complementary"}
        aria-label={isMobileViewport ? "Mobile navigation" : undefined}
        aria-modal={isMobileViewport ? true : undefined}
        aria-hidden={isMobileViewport && !isMobileSidebarOpen}
        inert={isMobileViewport && !isMobileSidebarOpen}
        className={`fixed left-0 top-0 z-40 h-screen w-[250px] transform border-r border-white/10 bg-[#111827] text-slate-200 transition-transform duration-200 ease-out ${
          isMobileSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-[72px] items-center gap-3 border-b border-white/10 px-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary shadow-lg shadow-indigo-500/20">
              <div className="h-4 w-4 rounded-md bg-white/90" />
            </div>

            <Link href="/" className="flex flex-col leading-tight" data-mobile-first-focus>
              <span className="text-[1.75rem] font-bold tracking-tight text-white">
                Road2Hire
              </span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-slate-300">
                AI Career Coach
              </span>
            </Link>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Sidebar navigation">
            <div className="space-y-1.5">
              {navigation.map((item) => {
                const active = getIsActive(item.href);

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => {
                      if (isMobileViewport) closeMobileSidebar();
                    }}
                    aria-current={active ? "page" : undefined}
                    className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-primary text-white shadow-sm"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    <span
                      className={`flex h-6 w-6 items-center justify-center rounded-md ${
                        active ? "bg-white/10 text-white" : "bg-slate-800 text-slate-300 group-hover:bg-slate-700"
                      }`}
                    >
                      <NavIcon name={item.name} active={active} />
                    </span>
                    <span>{item.name === "Sign in" && session ? "Account" : item.name}</span>
                    {item.name === "AI Career Assistant" ? (
                      <span className="ml-auto rounded-full bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                        New
                      </span>
                    ) : null}
                  </Link>
                );
              })}
            </div>

            <div className="mt-6 space-y-1.5 border-t border-white/10 pt-4">
              {secondaryNavigation.map((item) => {
                return (
                  <button
                    key={item.name}
                    type="button"
                    disabled
                    title={`${item.name} is not available in this prototype`}
                    aria-label={`${item.name}, coming soon`}
                    className="group flex w-full cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-slate-400 opacity-70"
                  >
                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-800 text-slate-300 group-hover:bg-slate-700">
                      <NavIcon name={item.name} />
                    </span>
                    <span>{item.name}</span>
                    <span className="ml-auto text-[10px] font-semibold uppercase tracking-wide text-slate-500">Soon</span>
                  </button>
                );
              })}
            </div>
          </nav>

          <div className="border-t border-white/10 p-3">
            <div className="flex items-center gap-3 rounded-xl bg-slate-800/70 p-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-indigo-500 text-sm font-semibold text-white">
                A
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-semibold text-white">
                    {session?.profile.name ?? "Arjun Mehta"}
                  </p>
                </div>
                <p className="truncate text-[11px] text-slate-300">
                  {session?.profile.email ?? "Frontend Developer"}
                </p>
              </div>
            </div>
            {session && (
              <button
                type="button"
                onClick={signOut}
                className="mt-2 w-full rounded-lg px-3 py-2 text-left text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white"
              >
                Sign out
              </button>
            )}

            <div className="mt-3 rounded-xl bg-slate-800/70 p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Upgrade to Pro</p>
              <p className="mt-2 text-xs leading-5 text-slate-300">
                Unlock advanced insights & more personalized guidance.
              </p>
              <button
                type="button"
                disabled
                title="Upgrade is not available in this prototype"
                className="mt-3 w-full cursor-not-allowed rounded-lg bg-slate-700 px-3 py-2 text-sm font-semibold text-slate-300 opacity-75"
              >
                Upgrade unavailable
              </button>
            </div>
          </div>
        </div>
     </aside>
    </>
  );
}
