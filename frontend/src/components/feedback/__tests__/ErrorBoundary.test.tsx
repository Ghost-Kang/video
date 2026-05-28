/**
 * Unit tests for <ErrorBoundary/> — W5D2-E。
 *
 * 覆盖:
 * - 正常子树 render passthrough
 * - 子树 throw 时 render fallback + 文案合规(无 FORBIDDEN_TERMS)
 * - componentDidCatch 投递到 reportClientError 且 kind=react_error_boundary
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

// Mock errorReporter — boundary 不能依赖真的 fetch。我们只 assert call shape。
vi.mock("../../../lib/errorReporter", async (orig) => {
  const real = (await orig()) as typeof import("../../../lib/errorReporter");
  return {
    ...real,
    reportClientError: vi.fn(),
  };
});

import { reportClientError } from "../../../lib/errorReporter";

function Boom() {
  throw new Error("kaboom-test-error");
  // unreachable; included so TS infers a return type
  // eslint-disable-next-line no-unreachable
  return null;
}

// React 19 still surfaces componentDidCatch errors to console.error;
// silence to keep test output clean.
let errSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  vi.mocked(reportClientError).mockReset();
});

afterEach(() => {
  errSpy.mockRestore();
});

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div>healthy-child</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("healthy-child")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary-fallback")).not.toBeInTheDocument();
  });

  it("renders fallback UI when child throws", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    const fallback = screen.getByTestId("error-boundary-fallback");
    expect(fallback).toBeInTheDocument();
    expect(fallback).toHaveTextContent("页面遇到问题");
    expect(fallback).toHaveTextContent("出了点小状况");
    expect(screen.getByRole("button", { name: "刷新页面" })).toBeInTheDocument();
  });

  it("fallback copy avoids FORBIDDEN_TERMS (节点/锚点/Agent/AI/平台/工具/画布/DAG)", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    const text = screen.getByTestId("error-boundary-fallback").textContent ?? "";
    const banned = ["节点", "锚点", "Agent", "AI", "平台", "工具", "画布", "DAG"];
    for (const term of banned) {
      expect(text).not.toContain(term);
    }
  });

  it("reports the error via reportClientError with kind=react_error_boundary", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(reportClientError).toHaveBeenCalled();
    const payload = vi.mocked(reportClientError).mock.calls[0][0];
    expect(payload.kind).toBe("react_error_boundary");
    expect(payload.message).toBe("kaboom-test-error");
    // component_stack 由 React 自动注入,可能存在
    expect(typeof payload.url).toBe("string");
  });
});
