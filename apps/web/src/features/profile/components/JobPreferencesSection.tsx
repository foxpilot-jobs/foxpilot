import { useEffect, useState } from "react";
import {
  getWorkspacePreferences,
  updateWorkspacePreferences,
  type WorkspacePreferences,
} from "../../../api";
import { Button } from "../../../shared/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { Toast } from "../../../shared/ui/Toast";

export function JobPreferencesSection({ reloadKey }: { reloadKey?: number }) {
  const [preferences, setPreferences] = useState<WorkspacePreferences>({
    target_roles: [],
    work_arrangement: "any",
    preferred_locations: [],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newRole, setNewRole] = useState("");
  const [newLocation, setNewLocation] = useState("");
  const [showAddRoleInput, setShowAddRoleInput] = useState(false);
  const [showAddLocInput, setShowAddLocInput] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getWorkspacePreferences()
      .then((res) => {
        if (active) {
          setPreferences(res);
        }
      })
      .catch(() => {
        if (active) {
          setErrorMessage("Failed to load workspace preferences.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const handleAddRole = () => {
    const trimmed = newRole.trim();
    if (!trimmed) return;
    if (
      preferences.target_roles.some(
        (r) => r.toLowerCase() === trimmed.toLowerCase(),
      )
    ) {
      setNewRole("");
      setShowAddRoleInput(false);
      return;
    }
    setPreferences((prev) => ({
      ...prev,
      target_roles: [...prev.target_roles, trimmed],
    }));
    setNewRole("");
    setShowAddRoleInput(false);
  };

  const handleRemoveRole = (role: string) => {
    setPreferences((prev) => ({
      ...prev,
      target_roles: prev.target_roles.filter((r) => r !== role),
    }));
  };

  const handleAddLocation = () => {
    const trimmed = newLocation.trim();
    if (!trimmed) return;
    if (
      preferences.preferred_locations.some(
        (l) => l.toLowerCase() === trimmed.toLowerCase(),
      )
    ) {
      setNewLocation("");
      setShowAddLocInput(false);
      return;
    }
    setPreferences((prev) => ({
      ...prev,
      preferred_locations: [...prev.preferred_locations, trimmed],
    }));
    setNewLocation("");
    setShowAddLocInput(false);
  };

  const handleRemoveLocation = (loc: string) => {
    setPreferences((prev) => ({
      ...prev,
      preferred_locations: prev.preferred_locations.filter((l) => l !== loc),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    setErrorMessage(null);
    try {
      const saved = await updateWorkspacePreferences(preferences);
      setPreferences(saved);
      setToastMessage("Job preferences saved for this workspace.");
    } catch {
      setErrorMessage("Failed to save workspace preferences. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card className="job-preferences-card">
        <CardHeader>
          <CardTitle>Job preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="profile-muted">Loading preferences…</p>
        </CardContent>
      </Card>
    );
  }

  const workArrangements: Array<{
    id: WorkspacePreferences["work_arrangement"];
    label: string;
  }> = [
    { id: "any", label: "Any" },
    { id: "remote", label: "Remote" },
    { id: "hybrid", label: "Hybrid" },
    { id: "onsite", label: "On-site" },
  ];

  return (
    <Card className="job-preferences-card">
      <CardHeader>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <CardTitle>Job preferences</CardTitle>
            <span className="profile-header-sub" style={{ fontSize: "0.85em", display: "block", marginTop: "2px" }}>
              Configure what jobs you want to apply for in this workspace.
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="job-preferences-content" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {toastMessage && (
          <Toast variant="success" onDismiss={() => setToastMessage(null)}>
            {toastMessage}
          </Toast>
        )}
        {errorMessage && (
          <Toast variant="error" onDismiss={() => setErrorMessage(null)}>
            {errorMessage}
          </Toast>
        )}

        {/* ── Target Roles ── */}
        <div className="preference-group">
          <label className="preference-label" style={{ fontWeight: 600, display: "block", marginBottom: "8px" }}>
            Target roles
          </label>
          <div className="chip-list-editable" style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
            {preferences.target_roles.map((role) => (
              <span
                key={role}
                className="ui-chip-editable"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 10px",
                  borderRadius: "16px",
                  background: "var(--color-brand-soft)",
                  color: "var(--color-brand)",
                  fontWeight: 500,
                  fontSize: "0.9em",
                  border: "1px solid color-mix(in srgb, var(--color-brand) 30%, transparent)",
                }}
              >
                {role}
                <button
                  type="button"
                  aria-label={`Remove ${role}`}
                  onClick={() => handleRemoveRole(role)}
                  style={{
                    border: "none",
                    background: "none",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: "14px",
                    lineHeight: 1,
                    color: "inherit",
                    opacity: 0.8,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
            {showAddRoleInput ? (
              <div style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="e.g. Software Engineer"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddRole();
                    } else if (e.key === "Escape") {
                      setShowAddRoleInput(false);
                    }
                  }}
                  autoFocus
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    border: "1px solid var(--color-border)",
                    fontSize: "0.9em",
                  }}
                />
                <Button size="sm" variant="primary" onClick={handleAddRole}>
                  Add
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowAddRoleInput(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <button
                type="button"
                className="ui-button-add-chip"
                onClick={() => setShowAddRoleInput(true)}
                style={{
                  padding: "4px 12px",
                  borderRadius: "16px",
                  border: "1px dashed var(--color-border)",
                  background: "transparent",
                  color: "var(--color-text-secondary)",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                + Add role
              </button>
            )}
          </div>
        </div>

        {/* ── Work Arrangement ── */}
        <div className="preference-group">
          <label className="preference-label" style={{ fontWeight: 600, display: "block", marginBottom: "8px" }}>
            Work arrangement
          </label>
          <div className="work-arrangement-selector" style={{ display: "flex", gap: "8px" }}>
            {workArrangements.map((item) => {
              const active = preferences.work_arrangement === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() =>
                    setPreferences((prev) => ({ ...prev, work_arrangement: item.id }))
                  }
                  style={{
                    padding: "6px 16px",
                    borderRadius: "8px",
                    border: active
                      ? "1px solid var(--color-brand)"
                      : "1px solid var(--color-border)",
                    background: active
                      ? "var(--color-brand-soft)"
                      : "var(--color-surface)",
                    color: active ? "var(--color-brand)" : "var(--color-text-primary)",
                    fontWeight: active ? 600 : 400,
                    cursor: "pointer",
                    fontSize: "0.9em",
                  }}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Preferred Locations ── */}
        <div className="preference-group">
          <label className="preference-label" style={{ fontWeight: 600, display: "block", marginBottom: "8px" }}>
            Preferred locations
          </label>
          <div className="chip-list-editable" style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
            {preferences.preferred_locations.map((loc) => (
              <span
                key={loc}
                className="ui-chip-editable"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 10px",
                  borderRadius: "16px",
                  background: "var(--color-surface-elevated)",
                  color: "var(--color-text-primary)",
                  fontWeight: 500,
                  fontSize: "0.9em",
                  border: "1px solid var(--color-border)",
                }}
              >
                📍 {loc}
                <button
                  type="button"
                  aria-label={`Remove ${loc}`}
                  onClick={() => handleRemoveLocation(loc)}
                  style={{
                    border: "none",
                    background: "none",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: "14px",
                    lineHeight: 1,
                    color: "inherit",
                    opacity: 0.8,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
            {showAddLocInput ? (
              <div style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="e.g. Hyderabad"
                  value={newLocation}
                  onChange={(e) => setNewLocation(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddLocation();
                    } else if (e.key === "Escape") {
                      setShowAddLocInput(false);
                    }
                  }}
                  autoFocus
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    border: "1px solid var(--color-border)",
                    fontSize: "0.9em",
                  }}
                />
                <Button size="sm" variant="primary" onClick={handleAddLocation}>
                  Add
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowAddLocInput(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <button
                type="button"
                className="ui-button-add-chip"
                onClick={() => setShowAddLocInput(true)}
                style={{
                  padding: "4px 12px",
                  borderRadius: "16px",
                  border: "1px dashed var(--color-border)",
                  background: "transparent",
                  color: "var(--color-text-secondary)",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                + Add location
              </button>
            )}
          </div>
        </div>

        {/* ── Save Action ── */}
        <div style={{ marginTop: "8px" }}>
          <Button variant="primary" disabled={saving} onClick={() => void handleSave()}>
            {saving ? "Saving preferences…" : "Save preferences"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
