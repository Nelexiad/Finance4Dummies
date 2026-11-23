import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders Finance4Dummies shell and displays online statuses when API responds", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/api/v1/health/ready")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              status: "ok",
              dependencies: { database: "ok", redis: "ok" },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }

      return Promise.resolve(
        new Response(
          JSON.stringify({
            status: "ok",
            app: "Finance4Dummies",
            environment: "development",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    });

    render(<App />);

    expect(screen.getByText("Finance4Dummies")).toBeInTheDocument();
    expect(screen.getByText("Banking Actors & Accounts")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("API: Online")).toBeInTheDocument();
      expect(screen.getByText("PostgreSQL: Online")).toBeInTheDocument();
      expect(screen.getByText("Redis: Online")).toBeInTheDocument();
    });
  });
});
