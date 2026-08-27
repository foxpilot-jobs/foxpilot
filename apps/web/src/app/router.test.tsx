import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppRouter } from "./router";

vi.mock("../features/auth/useAuth", () => ({
  useAuth: () => ({ loading: true, user: null }),
}));

describe("AppRouter loading state", () => {
  it("shows a restrained branded loader instead of an oversized mark", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AppRouter />
      </MemoryRouter>,
    );

    expect(screen.getByRole("status", { name: "Loading FoxPilot" })).toBeInTheDocument();
    expect(screen.getByRole("presentation").parentElement).toHaveClass("auth-loading-mark");
    expect(screen.getByText("Preparing your workspace")).toBeInTheDocument();
  });
});
