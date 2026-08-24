import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { Avatar } from "./Avatar";
import { Dropdown, DropdownItem } from "./Dropdown";

export function UserMenu({ email, onSignOut }: { email: string; onSignOut?: () => void }) {
  const initials = email.slice(0, 1).toUpperCase();
  return (
    <Dropdown
      label={
        <>
          <Avatar initials={initials} alt="" />
          <span className="ui-user-menu-email">{email}</span>
          <ChevronDown size={16} />
        </>
      }
    >
      <DropdownItem>
        <UserRound size={16} />
        Profile
      </DropdownItem>
      <DropdownItem onClick={onSignOut}>
        <LogOut size={16} />
        Sign out
      </DropdownItem>
    </Dropdown>
  );
}
