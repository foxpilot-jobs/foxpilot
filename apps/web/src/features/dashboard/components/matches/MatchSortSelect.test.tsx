import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MatchSortSelect } from "./MatchSortSelect";

describe("MatchSortSelect", () => {
  it("uses the themed menu and reports sort changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<MatchSortSelect sort="score" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Sort matches" }));
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByRole("listbox", { name: "Sort matches" })).toBeVisible();
    await user.click(screen.getByRole("option", { name: "Newest" }));

    expect(onChange).toHaveBeenCalledWith("newest");
  });
});
