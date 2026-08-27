import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProfileActions } from "./ProfileActions";

describe("ProfileActions", () => {
  it("shows matching progress and does not expose source scanning", async () => {
    const user = userEvent.setup();
    const onMatching = vi.fn();
    const { rerender } = render(
      <ProfileActions disabled={false} loading onMatching={onMatching} />,
    );

    expect(screen.queryByRole("button", { name: /run job scan/i })).not.toBeInTheDocument();
    const matchingButton = screen.getByRole("button", { name: /run matching/i });
    expect(matchingButton).toHaveAttribute("aria-busy", "true");
    rerender(<ProfileActions disabled={false} loading={false} onMatching={onMatching} />);
    await user.click(screen.getByRole("button", { name: /run matching/i }));
    expect(onMatching).toHaveBeenCalledOnce();
  });
});
