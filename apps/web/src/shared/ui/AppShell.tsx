import { Menu, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

const COLLAPSE_KEY = "foxpilot:sidebar-collapsed";
const MOBILE_QUERY = "(max-width: 768px)";

function readStoredCollapsed() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(COLLAPSE_KEY) === "1";
}

export function AppShell({
  children,
  mobileNav,
  sidebar,
  topbar,
}: {
  children: ReactNode;
  mobileNav?: ReactNode;
  sidebar?: ReactNode;
  topbar?: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(readStoredCollapsed);
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(MOBILE_QUERY).matches,
  );
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const query = window.matchMedia(MOBILE_QUERY);
    const update = () => setIsMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.classList.add("ui-scroll-locked");
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("ui-scroll-locked");
    };
  }, [mobileOpen]);

  const toggleNav = () => {
    if (isMobile) setMobileOpen((open) => !open);
    else setCollapsed((current) => !current);
  };

  const navToggleLabel = isMobile
    ? mobileOpen
      ? "Close navigation"
      : "Open navigation"
    : collapsed
      ? "Expand navigation"
      : "Collapse navigation";

  return (
    <div
      className={["ui-app-shell", collapsed ? "ui-shell-collapsed" : ""].filter(Boolean).join(" ")}
    >
      <header className="ui-app-topbar">
        <button
          aria-expanded={isMobile ? mobileOpen : !collapsed}
          aria-label={navToggleLabel}
          className="ui-icon-button ui-nav-toggle"
          type="button"
          onClick={toggleNav}
        >
          {isMobile ? (
            mobileOpen ? (
              <X size={20} />
            ) : (
              <Menu size={20} />
            )
          ) : collapsed ? (
            <PanelLeftOpen size={20} />
          ) : (
            <PanelLeftClose size={20} />
          )}
        </button>
        {topbar}
      </header>
      <aside className={`ui-app-sidebar ${mobileOpen ? "ui-app-sidebar-open" : ""}`}>
        {sidebar}
      </aside>
      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="ui-mobile-overlay"
          type="button"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <main className="ui-app-content">
        <div className="ui-page-transition" key={location.pathname}>
          {children}
        </div>
      </main>
      {mobileNav}
    </div>
  );
}

export function PageContainer({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`ui-page-container ${className}`.trim()}>{children}</div>;
}

export function Sidebar({ children }: { children?: ReactNode }) {
  return (
    <nav className="ui-sidebar-content" aria-label="Primary navigation">
      {children}
    </nav>
  );
}

export function Topbar({ children }: { children?: ReactNode }) {
  return <div className="ui-topbar-content">{children}</div>;
}

export function MobileNav({ children }: { children?: ReactNode }) {
  return (
    <nav className="ui-mobile-nav" aria-label="Mobile navigation">
      {children}
    </nav>
  );
}

export function PageHeader({
  actions,
  children,
  description,
  eyebrow,
  title,
}: {
  actions?: ReactNode;
  children?: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  title: ReactNode;
}) {
  return (
    <header className="ui-page-header">
      <div>
        {eyebrow && <p className="ui-eyebrow">{eyebrow}</p>}
        <h1 className="ui-page-title">{title}</h1>
        {description && <p className="ui-page-description">{description}</p>}
        {children}
      </div>
      {actions && <div className="ui-page-header-actions">{actions}</div>}
    </header>
  );
}

export function Section({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`ui-section ${className}`.trim()}>{children}</section>;
}

export function Stack({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`ui-stack ${className}`.trim()}>{children}</div>;
}

export function Inline({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`ui-inline ${className}`.trim()}>{children}</div>;
}

export function Grid({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`ui-grid ${className}`.trim()}>{children}</div>;
}
