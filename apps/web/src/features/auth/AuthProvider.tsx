import { useEffect, useMemo, useState, type ReactNode } from "react";
import { getAuthUser, logout, type AuthUser } from "../../api";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    getAuthUser()
      .then(setUser)
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(
    () => ({
      loading,
      user,
      setUser,
      signOut: async () => {
        await logout();
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
