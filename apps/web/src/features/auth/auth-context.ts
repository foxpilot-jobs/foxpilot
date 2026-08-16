import { createContext } from "react";
import type { AuthUser } from "../../api";

export type AuthContextValue = {
  loading: boolean;
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
