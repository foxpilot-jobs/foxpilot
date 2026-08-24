import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";
import { Modal, ModalActions } from "./Modal";

describe("Modal", () => {
  it("renders nothing when closed", () => {
    render(
      <Modal open={false} onClose={vi.fn()} title="Confirm">
        Body
      </Modal>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("supports close button, backdrop, and Escape dismissal", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open onClose={onClose} title="Confirm">
        <p>Body</p>
        <ModalActions>
          <Button onClick={onClose}>Confirm</Button>
        </ModalActions>
      </Modal>,
    );

    expect(screen.getByRole("dialog", { name: "Confirm" })).toBeInTheDocument();
    expect(document.body).toHaveClass("ui-scroll-locked");
    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("dialog").parentElement!);
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});
