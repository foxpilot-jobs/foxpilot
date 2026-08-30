import { Check, ChevronDown, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  createWorkspace,
  deleteWorkspace,
  listWorkspaces,
  renameWorkspace,
  switchWorkspace,
  type Workspace,
} from "../../../api";
import { Button } from "../../../shared/ui/Button";
import { Modal, ModalActions } from "../../../shared/ui/Modal";

type Props = {
  /** Called after the active workspace changes so the parent can reload the profile. */
  onSwitch: () => void;
};

export function WorkspaceManager({ onSwitch }: Props) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create modal
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [creating, setCreating] = useState(false);

  // Rename modal
  const [renameTarget, setRenameTarget] = useState<Workspace | null>(null);
  const [renameName, setRenameName] = useState("");
  const [renaming, setRenaming] = useState(false);

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<Workspace | null>(null);
  const [deleting, setDeleting] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const active = workspaces.find((ws) => ws.is_active);

  useEffect(() => {
    listWorkspaces()
      .then(setWorkspaces)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  async function handleSwitch(ws: Workspace) {
    if (ws.is_active) {
      setOpen(false);
      return;
    }
    try {
      await switchWorkspace(ws.workspace_id);
      setWorkspaces((prev) =>
        prev.map((w) => ({ ...w, is_active: w.workspace_id === ws.workspace_id })),
      );
      setOpen(false);
      onSwitch();
    } catch {
      setError("Could not switch workspace. Please try again.");
    }
  }

  async function handleCreate() {
    if (!createName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const ws = await createWorkspace(createName.trim());
      setWorkspaces((prev) => [...prev, ws]);
      setShowCreate(false);
      setCreateName("");
    } catch {
      setError("Could not create workspace. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  async function handleRename() {
    if (!renameTarget || !renameName.trim()) return;
    setRenaming(true);
    setError(null);
    try {
      await renameWorkspace(renameTarget.workspace_id, renameName.trim());
      setWorkspaces((prev) =>
        prev.map((w) =>
          w.workspace_id === renameTarget.workspace_id ? { ...w, name: renameName.trim() } : w,
        ),
      );
      setRenameTarget(null);
    } catch {
      setError("Could not rename workspace. Please try again.");
    } finally {
      setRenaming(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteWorkspace(deleteTarget.workspace_id);
      let next = workspaces.filter((w) => w.workspace_id !== deleteTarget.workspace_id);
      if (deleteTarget.is_active && next.length > 0) {
        next = next.map((w, i) => ({ ...w, is_active: i === 0 }));
        onSwitch();
      }
      setWorkspaces(next);
      setDeleteTarget(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete workspace.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="workspace-manager" ref={containerRef}>
        <button
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-label="Switch workspace"
          className="workspace-trigger"
          type="button"
          onClick={() => setOpen((v) => !v)}
        >
          <span className="workspace-trigger-name">{active?.name ?? "Default"}</span>
          <ChevronDown size={14} aria-hidden="true" />
        </button>

        {open && (
          <div className="workspace-dropdown" role="listbox" aria-label="Workspaces">
            {workspaces.map((ws) => (
              <div className="workspace-row" key={ws.workspace_id}>
                <button
                  aria-selected={ws.is_active}
                  className={`workspace-option${ws.is_active ? " workspace-option-active" : ""}`}
                  role="option"
                  type="button"
                  onClick={() => void handleSwitch(ws)}
                >
                  {ws.is_active && (
                    <Check size={14} aria-hidden="true" className="workspace-check" />
                  )}
                  <span>{ws.name}</span>
                </button>
                <button
                  aria-label={`Rename ${ws.name}`}
                  className="workspace-action"
                  type="button"
                  onClick={() => {
                    setRenameTarget(ws);
                    setRenameName(ws.name);
                    setOpen(false);
                  }}
                >
                  <Pencil size={14} aria-hidden="true" />
                </button>
                {workspaces.length > 1 && (
                  <button
                    aria-label={`Delete ${ws.name}`}
                    className="workspace-action workspace-action-danger"
                    type="button"
                    onClick={() => {
                      setDeleteTarget(ws);
                      setOpen(false);
                    }}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                )}
              </div>
            ))}
            <div className="workspace-dropdown-footer">
              <button
                className="workspace-new"
                type="button"
                onClick={() => {
                  setShowCreate(true);
                  setOpen(false);
                }}
              >
                <Plus size={14} aria-hidden="true" />
                New workspace
              </button>
            </div>
            {error && <p className="workspace-error">{error}</p>}
          </div>
        )}
      </div>

      {/* ── Create modal ── */}
      <Modal open={showCreate} title="New workspace" onClose={() => setShowCreate(false)}>
        <p className="workspace-modal-hint">
          Give this workspace a name. Each workspace has its own resume, profile, and match history.
        </p>
        <label className="workspace-modal-label" htmlFor="ws-create-name">
          Name
        </label>
        <input
          autoFocus
          className="workspace-modal-input"
          id="ws-create-name"
          maxLength={80}
          placeholder="e.g. Senior IC roles"
          type="text"
          value={createName}
          onChange={(e) => setCreateName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void handleCreate();
          }}
        />
        {error && <p className="workspace-error">{error}</p>}
        <ModalActions>
          <Button variant="outline" onClick={() => setShowCreate(false)}>
            Cancel
          </Button>
          <Button disabled={!createName.trim() || creating} onClick={() => void handleCreate()}>
            {creating ? "Creating…" : "Create workspace"}
          </Button>
        </ModalActions>
      </Modal>

      {/* ── Rename modal ── */}
      <Modal
        open={Boolean(renameTarget)}
        title="Rename workspace"
        onClose={() => setRenameTarget(null)}
      >
        <label className="workspace-modal-label" htmlFor="ws-rename-name">
          Name
        </label>
        <input
          autoFocus
          className="workspace-modal-input"
          id="ws-rename-name"
          maxLength={80}
          type="text"
          value={renameName}
          onChange={(e) => setRenameName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void handleRename();
          }}
        />
        {error && <p className="workspace-error">{error}</p>}
        <ModalActions>
          <Button variant="outline" onClick={() => setRenameTarget(null)}>
            Cancel
          </Button>
          <Button disabled={!renameName.trim() || renaming} onClick={() => void handleRename()}>
            {renaming ? "Saving…" : "Save"}
          </Button>
        </ModalActions>
      </Modal>

      {/* ── Delete confirmation ── */}
      <Modal
        open={Boolean(deleteTarget)}
        title={`Delete "${deleteTarget?.name}"?`}
        onClose={() => setDeleteTarget(null)}
      >
        <p>
          This will permanently remove the resume and profile data for this workspace. Matches and
          applications linked to it will also be removed. This cannot be undone.
        </p>
        {error && <p className="workspace-error">{error}</p>}
        <ModalActions>
          <Button variant="outline" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button disabled={deleting} variant="danger" onClick={() => void handleDelete()}>
            {deleting ? "Deleting…" : "Delete workspace"}
          </Button>
        </ModalActions>
      </Modal>
    </>
  );
}
