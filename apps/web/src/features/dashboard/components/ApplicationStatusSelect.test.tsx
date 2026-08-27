import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApplicationStatusSelect } from "./ApplicationStatusSelect";

describe("ApplicationStatusSelect", () => {
  it("opens a visible status menu and reports the selected status", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ApplicationStatusSelect
        disabled={false}
        jobTitle="Data Engineer"
        status="saved"
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Application status for Data Engineer" }));
    expect(screen.getByRole("listbox", { name: "Application status" })).toBeVisible();
    await user.click(screen.getByRole("option", { name: "Interviewing" }));
    expect(onChange).toHaveBeenCalledWith("interviewing");
  });
});
