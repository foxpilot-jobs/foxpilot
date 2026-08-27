import { describe, expect, it } from "vitest";
import { getGreeting } from "./greeting";

describe("getGreeting", () => {
  it.each([
    [0, "Good morning"],
    [11, "Good morning"],
    [12, "Good afternoon"],
    [17, "Good afternoon"],
    [18, "Good evening"],
    [23, "Good evening"],
  ])("returns the local-time greeting for hour %i", (hour, expected) => {
    expect(getGreeting(hour)).toBe(expected);
  });
});
