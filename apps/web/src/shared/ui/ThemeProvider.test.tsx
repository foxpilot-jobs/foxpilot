import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useContext } from "react";
import { describe, expect, it } from "vitest";
import { ThemeContext } from "./theme-context";
import { ThemeProvider } from "./ThemeProvider";

function ThemeControls() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("Theme context is missing");
  return (
    <>
      <output>{context.theme}</output>
      <button type="button" onClick={() => context.setTheme("dark")}>
        Dark mode
      </button>
    </>
  );
}

describe("ThemeProvider", () => {
  it("restores and persists the selected theme", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("foxpilot:theme", "dark");

    const { unmount } = render(
      <ThemeProvider>
        <ThemeControls />
      </ThemeProvider>,
    );

    expect(screen.getByText("dark")).toBeInTheDocument();
    expect(document.documentElement.dataset.theme).toBe("dark");

    await user.click(screen.getByRole("button", { name: "Dark mode" }));
    expect(window.localStorage.getItem("foxpilot:theme")).toBe("dark");

    unmount();
    render(
      <ThemeProvider>
        <ThemeControls />
      </ThemeProvider>,
    );
    expect(screen.getByText("dark")).toBeInTheDocument();
  });

  it("ignores invalid stored values", () => {
    window.localStorage.setItem("foxpilot:theme", "neon");
    render(
      <ThemeProvider defaultTheme="light">
        <ThemeControls />
      </ThemeProvider>,
    );

    expect(screen.getByText("light")).toBeInTheDocument();
  });
});
