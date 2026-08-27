import {
  BriefcaseBusiness,
  ChevronDown,
  ChevronRight,
  CircleUserRound,
  LayoutDashboard,
  Moon,
  Search,
  Settings,
  Sun,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../features/auth/useAuth";
import { AppShell, MobileNav, Sidebar, Topbar } from "../ui/AppShell";
import { Button } from "../ui/Button";
import { UserMenu } from "../ui/UserMenu";
import { useTheme } from "../ui/useTheme";

type NavChild = { label: string; to: string };
type NavItem = {
  label: string;
  to: string;
  icon: LucideIcon;
  end?: boolean;
  children?: NavChild[];
};

const primaryNavigation: NavItem[] = [
  { label: "Overview", to: "/app", icon: LayoutDashboard, end: true },
  { label: "Matches", to: "/app/matches", icon: Search },
  { label: "Applications", to: "/app/applications", icon: BriefcaseBusiness },
];

const profileNavigation: NavItem[] = [
  {
    label: "Profile",
    to: "/app/profile",
    icon: CircleUserRound,
    children: [{ label: "Insights", to: "/app/profile/insights" }],
  },
];

const systemNavigation: NavItem[] = [{ label: "Settings", to: "/app/settings", icon: Settings }];

export function AppLayout() {
  const { signOut, user } = useAuth();
  const { theme, setTheme } = useTheme();
  const location = useLocation();
  const title = getPageTitle(location.pathname);
  const navigation = [...primaryNavigation, ...profileNavigation, ...systemNavigation];

  return (
    <AppShell
      mobileNav={
        <MobileNav>
          {navigation.slice(0, 4).map((item) => (
            <NavigationLink item={item} key={item.to} mobile />
          ))}
        </MobileNav>
      }
      sidebar={
        <Sidebar>
          <NavBrand />
          <NavigationGroup label="Primary workflow" items={primaryNavigation} />
          <NavigationGroup label="Profile" items={profileNavigation} />
          <NavigationGroup label="System" items={systemNavigation} />
        </Sidebar>
      }
      topbar={
        <Topbar>
          <div className="ui-context-title">
            <span className="ui-context-label">Workspace</span>
            <ChevronRight size={14} aria-hidden="true" />
            <strong>{title}</strong>
          </div>
          <div className="ui-topbar-actions">
            <Button
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              icon={theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
              iconOnly
              size="sm"
              variant="ghost"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            />
            {user && <UserMenu email={user.email} onSignOut={() => void signOut()} />}
          </div>
        </Topbar>
      }
    >
      <Outlet />
    </AppShell>
  );
}

function NavBrand() {
  return (
    <NavLink className="ui-nav-brand" to="/app">
      <span className="ui-nav-brand-mark">
        <img src="/brand/foxpilot-mark.png" alt="" />
      </span>
      <span className="ui-nav-label">FoxPilot</span>
    </NavLink>
  );
}

function NavigationGroup({ items, label }: { items: NavItem[]; label: string }) {
  return (
    <div className="ui-nav-group">
      <p className="ui-nav-group-label">{label}</p>
      {items.map((item) => (
        <NavigationLink item={item} key={item.to} />
      ))}
    </div>
  );
}

function NavigationLink({ item, mobile = false }: { item: NavItem; mobile?: boolean }) {
  const Icon = item.icon;
  const location = useLocation();
  const hasChildren = Boolean(item.children?.length);
  const childActive = item.children?.some((child) => location.pathname.startsWith(child.to));
  const [open, setOpen] = useState(Boolean(childActive));
  const [flyoutSuppressed, setFlyoutSuppressed] = useState(false);

  if (mobile) {
    return (
      <NavLink
        className={({ isActive }) =>
          `ui-mobile-nav-link ${isActive ? "ui-mobile-nav-link-active" : ""}`
        }
        end={item.end}
        to={item.to}
      >
        <Icon size={18} aria-hidden="true" />
        <span>{item.label}</span>
      </NavLink>
    );
  }

  return (
    <div
      className={`ui-nav-item ${flyoutSuppressed ? "ui-nav-item-flyout-suppressed" : ""}`}
      onMouseEnter={() => setFlyoutSuppressed(false)}
      onMouseLeave={() => setFlyoutSuppressed(false)}
    >
      <div className="ui-nav-item-row">
        <NavLink
          className={({ isActive }) =>
            `ui-nav-link ${isActive || childActive ? "ui-nav-link-active" : ""}`
          }
          end={item.end}
          to={item.to}
          onClick={() => setFlyoutSuppressed(true)}
          onFocus={() => setFlyoutSuppressed(false)}
        >
          <Icon size={18} aria-hidden="true" />
          <span className="ui-nav-label">{item.label}</span>
        </NavLink>
        {hasChildren && (
          <button
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${item.label} section`}
            className="ui-nav-caret"
            type="button"
            onClick={() => setOpen((current) => !current)}
          >
            <ChevronDown size={14} aria-hidden="true" />
          </button>
        )}
      </div>
      {hasChildren && open && (
        <div className="ui-nav-subitems">
          {item.children!.map((child) => (
            <NavLink
              className={({ isActive }) => `ui-nav-sublink ${isActive ? "ui-nav-link-active" : ""}`}
              key={child.to}
              to={child.to}
            >
              {child.label}
            </NavLink>
          ))}
        </div>
      )}
      <div className="ui-nav-flyout" role={hasChildren ? "menu" : undefined}>
        <span className="ui-nav-flyout-label">{item.label}</span>
        {item.children?.map((child) => (
          <NavLink className="ui-nav-flyout-link" key={child.to} to={child.to} role="menuitem">
            {child.label}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function getPageTitle(pathname: string) {
  if (pathname.startsWith("/app/jobs/")) return "Matches";
  if (pathname.startsWith("/app/profile")) return "Profile";
  if (pathname.startsWith("/app/settings")) return "Settings";
  if (pathname.startsWith("/app/applications")) return "Applications";
  if (pathname.startsWith("/app/matches")) return "Matches";
  return "Overview";
}
