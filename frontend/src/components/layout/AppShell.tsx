"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import Dropdown from "react-bootstrap/Dropdown";

import { api } from "@/lib/api";
import { type Lang, usePrefs } from "@/lib/prefs";
import { useDashboard, useMaterials } from "@/lib/queries";

function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const pathname = usePathname();
  const { data: materials } = useMaterials();
  const { data: dash } = useDashboard();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation">
      <Link className="brand" href="/" onClick={onNavigate}>
        <span className="brand-mark">
          <i className="bi bi-mortarboard-fill" />
        </span>
        <span>StudyDesk</span>
      </Link>
      <nav className="sidebar-scroll">
        <div className="nav-heading">MAIN</div>
        <Link className={`side-link ${isActive("/") ? "active" : ""}`} href="/" onClick={onNavigate}>
          <i className="bi bi-speedometer2" />
          <span>Dashboard</span>
        </Link>
        <Link className={`side-link ${isActive("/review") ? "active" : ""}`} href="/review" onClick={onNavigate}>
          <i className="bi bi-arrow-repeat" />
          <span>Review</span>
          {!!dash?.due.total && <span className="count">{dash.due.total}</span>}
        </Link>
        <div className="nav-heading">LIBRARY</div>
        <Link className={`side-link ${pathname === "/materials" ? "active" : ""}`} href="/materials" onClick={onNavigate}>
          <i className="bi bi-collection" />
          <span>Study materials</span>
        </Link>
        {!!materials?.length && (
          <div className="sub-nav">
            {materials.map((m) => (
              <Link
                key={m.slug}
                href={`/materials/${m.slug}`}
                className={pathname.startsWith(`/materials/${m.slug}`) || pathname.startsWith(`/chapters/${m.slug}/`) ? "active" : ""}
                onClick={onNavigate}
                title={m.title}
              >
                {m.title}
              </Link>
            ))}
          </div>
        )}
      </nav>
      {dash && (
        <div className="sidebar-foot">
          <div className="d-flex justify-content-between small mb-1">
            <span className="fw-semibold">
              <i className="bi bi-stars text-warning me-1" />
              Level {dash.level}
            </span>
            <span className="text-secondary">{dash.xp} XP</span>
          </div>
          <div className="progress" style={{ height: 6 }}>
            <div className="progress-bar" style={{ width: `${Math.round(dash.progress * 100)}%` }} />
          </div>
        </div>
      )}
    </aside>
  );
}

const LANGS: { value: Lang; label: string }[] = [
  { value: "en", label: "EN" },
  { value: "hu", label: "HU" },
  { value: "both", label: "EN+HU" },
];

function Topbar({ onMenu }: { onMenu: () => void }) {
  const { lang, setLang, theme, setTheme } = usePrefs();
  const router = useRouter();
  const logout = async () => {
    await api("/auth/logout/", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  };
  return (
    <header className="topbar">
      <button className="icon-btn d-lg-none" onClick={onMenu} aria-label="Toggle sidebar">
        <i className="bi bi-list fs-4" />
      </button>
      <div className="ms-auto d-flex align-items-center gap-2">
        <div className="seg" role="group" aria-label="Content language">
          {LANGS.map((l) => (
            <button key={l.value} aria-pressed={lang === l.value} onClick={() => setLang(l.value)} title="Language of summaries, cards and quizzes">
              {l.label}
            </button>
          ))}
        </div>
        <button
          className="icon-btn"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <i className={`bi ${theme === "dark" ? "bi-sun" : "bi-moon"}`} />
        </button>
        <Dropdown align="end">
          <Dropdown.Toggle as="button" className="icon-btn" aria-label="Account" bsPrefix="x">
            <i className="bi bi-person-circle fs-5" />
          </Dropdown.Toggle>
          <Dropdown.Menu>
            <Dropdown.Item onClick={logout} className="text-danger">
              <i className="bi bi-box-arrow-right me-2" />
              Log out
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // Remember on which page the mobile sidebar was opened: navigating closes it.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === pathname;
  const close = () => setOpenOn(null);
  return (
    <>
      <Sidebar open={open} onNavigate={close} />
      <div className={`sidebar-backdrop ${open ? "open" : ""}`} onClick={close} />
      <div className="main">
        <Topbar onMenu={() => setOpenOn(open ? null : pathname)} />
        <main className="content">{children}</main>
      </div>
    </>
  );
}
