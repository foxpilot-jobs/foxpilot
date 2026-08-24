import { Menu, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

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
  const location = useLocation();
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);
  return (
    <div className="ui-app-shell">
      <header className="ui-app-topbar">
        <button
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          className="ui-icon-button ui-mobile-menu-button"
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
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
      <main className="ui-app-content">{children}</main>
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
