import {
  ArrowRight,
  KeyRound,
  LogOut,
  Moon,
  Palette,
  ShieldCheck,
  Sun,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../../shared/ui/Alert";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { useAuth } from "../../auth/useAuth";
import { useTheme } from "../../../shared/ui/useTheme";

export function SettingsPage() {
  const { signOut, user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [signOutError, setSignOutError] = useState(false);
  if (!user) return null;

  async function handleSignOut() {
    setSignOutError(false);
    try {
      await signOut();
    } catch {
      setSignOutError(true);
    }
  }

  return (
    <main className="settings-page">
      <header className="settings-header">
        <div>
          <p className="ui-eyebrow">Workspace preferences</p>
          <h1>Settings</h1>
          <p>Manage your FoxPilot account and preferences.</p>
        </div>
      </header>
      {signOutError && (
        <div className="settings-error">
          <Alert variant="error">We couldn&apos;t sign you out. Please try again.</Alert>
        </div>
      )}
      <div className="settings-sections">
        <Card>
          <CardHeader>
            <CardTitle>
              <UserRound size={19} aria-hidden="true" />
              Account
            </CardTitle>
            <CardDescription>Your FoxPilot account details.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="settings-account-row">
              <div>
                <span>Email</span>
                <strong>{user.email}</strong>
              </div>
              <Badge variant={user.email_verified ? "success" : "warning"}>
                {user.email_verified ? "Verified" : "Verification needed"}
              </Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <Palette size={19} aria-hidden="true" />
              Appearance
            </CardTitle>
            <CardDescription>Choose how FoxPilot looks on this device.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="settings-theme-selector" aria-label="Appearance" role="radiogroup">
              {[
                { value: "light", label: "Light", icon: Sun },
                { value: "dark", label: "Dark", icon: Moon },
              ].map(({ icon: Icon, label, value }) => (
                <label
                  className={`settings-theme-option ${theme === value ? "settings-theme-option-selected" : ""}`}
                  key={value}
                >
                  <input
                    checked={theme === value}
                    name="theme"
                    type="radio"
                    value={value}
                    onChange={() => setTheme(value as "light" | "dark")}
                  />
                  <Icon size={17} aria-hidden="true" />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            <p className="settings-supporting">
              System theme is not currently supported by the existing theme provider.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <UserRound size={19} aria-hidden="true" />
              Career profile
            </CardTitle>
            <CardDescription>
              Manage the information FoxPilot uses to personalize recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="settings-link-list">
              <Link to="/app/profile">
                <span>
                  Manage profile<small>Update your resume and extracted career profile.</small>
                </span>
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
              <Link to="/app/profile/insights">
                <span>
                  View profile insights
                  <small>Understand what FoxPilot sees in your experience and skills.</small>
                </span>
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <ShieldCheck size={19} aria-hidden="true" />
              Security
            </CardTitle>
            <CardDescription>
              Manage access to your account through the existing authentication flow.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link className="settings-action-link" to="/forgot-password">
              <span>
                <KeyRound size={17} aria-hidden="true" />
                Reset password
              </span>
              <ArrowRight size={17} aria-hidden="true" />
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <LogOut size={19} aria-hidden="true" />
              Account actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              icon={<LogOut size={17} />}
              variant="outline"
              onClick={() => void handleSignOut()}
            >
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
