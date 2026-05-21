import { useCallback } from "react";
import { useCanvasStore } from "../store/canvasStore";
import type { FailurePayload } from "../types/cascade";

export function useApiError() {
  const setFailure = useCanvasStore((s) => s.setFailure);

  const wrappedFetch = useCallback(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const response = await fetch(input, init);
      if (response.ok) return response;
      const contentType = response.headers.get("content-type") || "";
      let failure: FailurePayload;
      if (contentType.includes("application/json")) {
        failure = (await response.json()) as FailurePayload;
      } else {
        failure = {
          code: "S5_INVALID_PAYLOAD",
          hint: "",
          actions: ["REPORT"],
          request_id: `req_${Date.now().toString(36)}`,
        };
      }
      setFailure(failure);
      throw failure;
    },
    [setFailure]
  );

  return { wrappedFetch };
}
