import { ChevronDown, LogOut, Settings, UserRound } from "lucide-react";
import { Avatar } from "./Avatar";
import { Dropdown, DropdownItem, DropdownLink } from "./Dropdown";

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
  return (
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
      <DropdownItem onClick={onSignOut}>
        <LogOut size={16} />
        Sign out
      </DropdownItem>
    </Dropdown>
  );
}
