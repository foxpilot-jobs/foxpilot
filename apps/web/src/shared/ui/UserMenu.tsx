import { ChevronDown, LogOut, Settings, UserRound } from "lucide-react";
import { useState } from "react";
import { Avatar } from "./Avatar";
import { Button } from "./Button";
import { Dropdown, DropdownItem, DropdownLink } from "./Dropdown";
import { Modal, ModalActions } from "./Modal";

export function UserMenu({
  displayName,
  email,
  onSignOut,
  profileHref = "/app/profile",
  settingsHref = "/app/settings",
}: {
  displayName?: string;
  email: string;
  onSignOut?: () => void;
  profileHref?: string;
  settingsHref?: string;
}) {
  const initials = (displayName ?? email).slice(0, 1).toUpperCase();
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <>
      <Dropdown
        label={
          <>
            <Avatar initials={initials} alt="" />
            <span className="ui-user-menu-label">
              {displayName && <strong>{displayName}</strong>}
              <span className="ui-user-menu-email">{email}</span>
            </span>
            <ChevronDown size={16} />
          </>
        }
      >
        <DropdownLink href={profileHref}>
          <UserRound size={16} />
          Profile
        </DropdownLink>
        <DropdownLink href={settingsHref}>
          <Settings size={16} />
          Settings
        </DropdownLink>
        <DropdownItem onClick={() => setConfirmOpen(true)}>
          <LogOut size={16} />
          Sign out
        </DropdownItem>
      </Dropdown>
      <Modal onClose={() => setConfirmOpen(false)} open={confirmOpen} title="Sign out of FoxPilot?">
        <p>You&apos;ll need to sign back in to view your matches and applications.</p>
        <ModalActions>
          <Button variant="outline" onClick={() => setConfirmOpen(false)}>
            Cancel
          </Button>
          <Button
            icon={<LogOut size={16} />}
            variant="danger"
            onClick={() => {
              setConfirmOpen(false);
              onSignOut?.();
            }}
          >
            Sign out
          </Button>
        </ModalActions>
      </Modal>
    </>
  );
}
