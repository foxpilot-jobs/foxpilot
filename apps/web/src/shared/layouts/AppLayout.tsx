import {
  BriefcaseBusiness,
  ChevronRight,
  CircleUserRound,
  LayoutDashboard,
  Moon,
  Search,
  Settings,
  Sun,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../features/auth/useAuth";
import { AppShell, MobileNav, Sidebar, Topbar } from "../ui/AppShell";
import { Button } from "../ui/Button";
import { UserMenu } from "../ui/UserMenu";
import { useTheme } from "../ui/useTheme";

const primaryNavigation = [
  { label: "Overview", to: "/app", icon: LayoutDashboard, end: true },
  { label: "Matches", to: "/app/matches", icon: Search },
  { label: "Applications", to: "/app/applications", icon: BriefcaseBusiness },
];

const profileNavigation = [{ label: "Profile", to: "/app/profile", icon: CircleUserRound }];
const systemNavigation = [{ label: "Settings", to: "/app/settings", icon: Settings }];

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
      <span>FoxPilot</span>
    </NavLink>
  );
}

function NavigationGroup({
  items,
  label,
}: {
  items: Array<{ label: string; to: string; icon: typeof LayoutDashboard; end?: boolean }>;
  label: string;
}) {
  return (
    <div className="ui-nav-group">
      <p className="ui-nav-group-label">{label}</p>
      {items.map((item) => (
        <NavigationLink item={item} key={item.to} />
      ))}
    </div>
  );
}

function NavigationLink({
  item,
  mobile = false,
}: {
  item: { label: string; to: string; icon: typeof LayoutDashboard; end?: boolean };
  mobile?: boolean;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      className={({ isActive }) =>
        `${mobile ? "ui-mobile-nav-link" : "ui-nav-link"} ${isActive ? "ui-nav-link-active" : ""}`
      }
      end={item.end}
      to={item.to}
    >
      <Icon size={18} aria-hidden="true" />
      <span>{item.label}</span>
    </NavLink>
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
