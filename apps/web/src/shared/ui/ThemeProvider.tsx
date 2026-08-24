import { useEffect, useState, type ReactNode } from "react";
import { ThemeContext, type Theme } from "./theme-context";

export type { Theme, ThemeContextValue } from "./theme-context";

export function ThemeProvider({
  children,
  defaultTheme = "light",
}: {
  children: ReactNode;
  defaultTheme?: Theme;
}) {
  const [theme, setTheme] = useState<Theme>(defaultTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}
