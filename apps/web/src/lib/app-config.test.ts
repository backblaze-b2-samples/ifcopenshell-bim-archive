import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("IfcOpenShell BIM Archive");
    expect(APP_DESCRIPTION).toBe(
      "BIM digital-twin archive powered by Backblaze B2 + IfcOpenShell"
    );
  });
});
