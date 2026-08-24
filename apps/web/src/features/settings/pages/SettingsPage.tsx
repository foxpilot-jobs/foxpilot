import { ArrowRight, KeyRound, LogOut, Moon, Sparkles, Sun, UserRound } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../../shared/ui/Alert";
import { Avatar } from "../../../shared/ui/Avatar";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { Modal, ModalActions } from "../../../shared/ui/Modal";
import { useAuth } from "../../auth/useAuth";
import { useTheme } from "../../../shared/ui/useTheme";

export function SettingsPage() {
  const { signOut, user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [signOutError, setSignOutError] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  if (!user) return null;

  async function handleSignOut() {
    setConfirmOpen(false);
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
        <p className="ui-eyebrow">Workspace preferences</p>
        <h1>Settings</h1>
        <p>Manage your FoxPilot account and preferences.</p>
      </header>

      {signOutError && (
        <div className="settings-error">
          <Alert variant="error">We couldn&apos;t sign you out. Please try again.</Alert>
        </div>
      )}

      <div className="settings-sections">
        <Card className="settings-account-card">
          <CardContent>
            <div className="settings-account-row">
              <Avatar alt="" initials={user.email.slice(0, 1).toUpperCase()} />
              <div className="settings-account-identity">
                <strong>{user.email}</strong>
                <span>FoxPilot account</span>
              </div>
              <Badge variant={user.email_verified ? "success" : "warning"}>
                {user.email_verified ? "Verified" : "Verification needed"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Choose how FoxPilot looks on this device.</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              aria-label="Appearance"
              className="settings-theme-switch"
              data-selected={theme}
              role="radiogroup"
            >
              <span className="settings-theme-thumb" aria-hidden="true" />
              {(
                [
                  { value: "light", label: "Light", icon: Sun },
                  { value: "dark", label: "Dark", icon: Moon },
                ] as const
              ).map(({ icon: Icon, label, value }) => (
                <label className="settings-theme-option" key={value}>
                  <input
                    checked={theme === value}
                    name="theme"
                    type="radio"
                    value={value}
                    onChange={() => setTheme(value)}
                  />
                  <Icon size={16} aria-hidden="true" />
                  <span>{label}</span>
                </label>
              ))}
            </div>
            <p className="settings-supporting">
              System theme isn&apos;t supported yet — pick the one that feels right for now.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Your career workspace</CardTitle>
            <CardDescription>
              Shortcuts to the information FoxPilot uses to personalize your matches.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="settings-link-list">
              <Link to="/app/profile">
                <span className="settings-link-icon">
                  <UserRound size={17} aria-hidden="true" />
                </span>
                <span className="settings-link-copy">
                  <strong>Manage profile</strong>
                  <small>Update your resume and extracted career profile.</small>
                </span>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
              <Link to="/app/profile/insights">
                <span className="settings-link-icon">
                  <Sparkles size={17} aria-hidden="true" />
                </span>
                <span className="settings-link-copy">
                  <strong>View profile insights</strong>
                  <small>Understand what FoxPilot sees in your experience and skills.</small>
                </span>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
              <Link to="/forgot-password">
                <span className="settings-link-icon">
                  <KeyRound size={17} aria-hidden="true" />
                </span>
                <span className="settings-link-copy">
                  <strong>Reset password</strong>
                  <small>Get a secure link to choose a new password.</small>
                </span>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session</CardTitle>
            <CardDescription>Sign out of FoxPilot on this device.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              icon={<LogOut size={17} />}
              variant="outline"
              onClick={() => setConfirmOpen(true)}
            >
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>

      <Modal onClose={() => setConfirmOpen(false)} open={confirmOpen} title="Sign out of FoxPilot?">
        <p>You&apos;ll need to sign back in to view your matches and applications.</p>
        <ModalActions>
          <Button variant="outline" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button icon={<LogOut size={16} />} variant="danger" onClick={() => void handleSignOut()}>
            Sign out
          </Button>
        </ModalActions>
      </Modal>
    </main>
  );
}
