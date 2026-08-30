import {
  BriefcaseBusiness,
  Check,
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
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { listWorkspaces, switchWorkspace, type Workspace } from "../../api";
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
  workspaces?: true; // renders live workspace switcher as sub-items
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
    workspaces: true,
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
  const [flyoutOpen, setFlyoutOpen] = useState(false);

  // Live workspace list — only loaded when this nav item has workspaces: true
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  useEffect(() => {
    if (!item.workspaces) return;
    listWorkspaces()
      .then(setWorkspaces)
      .catch(() => {});
  }, [item.workspaces]);

  async function handleWorkspaceSwitch(ws: Workspace) {
    if (ws.is_active) return;
    try {
      await switchWorkspace(ws.workspace_id);
      setWorkspaces((prev) =>
        prev.map((w) => ({ ...w, is_active: w.workspace_id === ws.workspace_id })),
      );
    } catch {
      // non-blocking — user can retry from the profile page
    }
  }

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
      className={`ui-nav-item ${flyoutOpen ? "ui-nav-item-flyout-open" : ""}`}
      onMouseEnter={() => setFlyoutOpen(true)}
      onMouseLeave={() => setFlyoutOpen(false)}
    >
      <div className="ui-nav-item-row">
        <NavLink
          className={({ isActive }) =>
            `ui-nav-link ${isActive || childActive ? "ui-nav-link-active" : ""}`
          }
          end={item.end}
          to={item.to}
          onClick={() => setFlyoutOpen(false)}
          onFocus={() => setFlyoutOpen(true)}
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
          {item.workspaces && workspaces.length > 0 && (
            <>
              <span className="ui-nav-subgroup-label">Workspaces</span>
              {workspaces.map((ws) => (
                <button
                  className={`ui-nav-sublink ui-nav-workspace-item ${ws.is_active ? "ui-nav-workspace-active" : ""}`}
                  key={ws.workspace_id}
                  title={ws.name}
                  type="button"
                  onClick={() => void handleWorkspaceSwitch(ws)}
                >
                  {ws.is_active && <Check size={12} aria-hidden="true" />}
                  <span className="ui-nav-workspace-name">{ws.name}</span>
                </button>
              ))}
            </>
          )}
        </div>
      )}
      <div className="ui-nav-flyout" role={hasChildren ? "menu" : undefined}>
        <span className="ui-nav-flyout-label">{item.label}</span>
        {item.children?.map((child) => (
          <NavLink
            className="ui-nav-flyout-link"
            key={child.to}
            role="menuitem"
            to={child.to}
            onClick={() => setFlyoutOpen(false)}
          >
            {child.label}
          </NavLink>
        ))}
        {item.workspaces && workspaces.length > 0 && (
          <>
            <span className="ui-nav-flyout-label ui-nav-flyout-section">Workspaces</span>
            {workspaces.map((ws) => (
              <button
                className={`ui-nav-flyout-link ui-nav-workspace-flyout ${ws.is_active ? "ui-nav-workspace-active" : ""}`}
                key={ws.workspace_id}
                type="button"
                onClick={() => {
                  void handleWorkspaceSwitch(ws);
                  setFlyoutOpen(false);
                }}
              >
                {ws.is_active && <Check size={12} aria-hidden="true" />}
                {ws.name}
              </button>
            ))}
          </>
        )}
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
