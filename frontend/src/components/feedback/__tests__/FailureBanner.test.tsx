import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FailureBanner } from "../FailureBanner";
import { ACTION_LABELS, type FailureCode, type FailurePayload, type RecoveryAction } from "../../../types/cascade";
import { RECOVERY_HINTS } from "../../../lib/recoveryHints";

const codes: FailureCode[] = [
  "S1_NO_SOURCE_URL",
  "S2_VERSION_MISMATCH",
  "S3_NO_FORMULA",
  "S4_SCENES_LEN_OUT_OF_RANGE",
  "S5_INVALID_PAYLOAD",
  "S6_NEGATIVE_COST",
  "S7_UPSTREAM_TIMEOUT",
  "S8_UPSTREAM_REFUSED",
];

describe("FailureBanner", () => {
  it.each(codes)("renders hint and action labels for %s", (code) => {
    const actions: RecoveryAction[] = ["REPORT"];
    const payload: FailurePayload = { code, hint: RECOVERY_HINTS[code], actions, request_id: "req_test" };
    render(<FailureBanner failure={payload} />);
    expect(screen.getByText(RECOVERY_HINTS[code])).toBeInTheDocument();
    expect(screen.getByRole("button", { name: ACTION_LABELS.REPORT })).toBeInTheDocument();
  });
});
