import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";

function renderShell() {
  return render(
    <MemoryRouter>
      <AppShell sidebar={<nav>Navigation</nav>} topbar={<span>FoxPilot</span>}>
        <h1>Dashboard</h1>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("collapses and restores the desktop navigation", async () => {
    const user = userEvent.setup();
    renderShell();
    const toggle = screen.getByRole("button", { name: "Collapse navigation" });

    await user.click(toggle);

    expect(screen.getByRole("button", { name: "Expand navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(window.localStorage.getItem("foxpilot:sidebar-collapsed")).toBe("1");
  });

  it("opens the mobile drawer and closes it with Escape", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: true,
      media: "(max-width: 768px)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });
    renderShell();

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(screen.getAllByRole("button", { name: "Close navigation" })[0]).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(document.body).toHaveClass("ui-scroll-locked");

    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Open navigation" })).toBeInTheDocument();
    expect(document.body).not.toHaveClass("ui-scroll-locked");
  });
});
