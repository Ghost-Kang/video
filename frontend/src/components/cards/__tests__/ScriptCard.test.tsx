import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScriptCard } from "../ScriptCard";
import { MOCK_BAOMAM_ANALYSIS } from "../../../fixtures/baomamFushi001";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";
import { buildDefaultScript } from "../../../fixtures/baomamFushi001";

describe("ScriptCard", () => {
  const script = buildDefaultScript(MOCK_BAOMAM_ANALYSIS);

  it("renders all three viral bullets with human labels", () => {
    render(
      <ScriptCard
        analysis={MOCK_BAOMAM_ANALYSIS}
        script={script}
        onScriptChange={() => {}}
      />
    );

    expect(screen.getByText(COPY.hook_label)).toBeInTheDocument();
    expect(screen.getByText(COPY.pacing_label)).toBeInTheDocument();
    expect(screen.getByText(COPY.climax_label)).toBeInTheDocument();
    expect(
      screen.getByText(MOCK_BAOMAM_ANALYSIS.viral_analysis.hook, { exact: false })
    ).toBeInTheDocument();
  });

  it("never displays raw schema field names", () => {
    const { container } = render(
      <ScriptCard
        analysis={MOCK_BAOMAM_ANALYSIS}
        script={script}
        onScriptChange={() => {}}
      />
    );
    const html = container.innerHTML;
    expect(html).not.toMatch(/viral_analysis/);
    expect(html).not.toMatch(/\bhook\b/);
    expect(html).not.toMatch(/\bpacing\b/);
    expect(html).not.toMatch(/\bclimax\b/);
  });

  it("contains no forbidden terms in rendered output", () => {
    const { container } = render(
      <ScriptCard
        analysis={MOCK_BAOMAM_ANALYSIS}
        script={script}
        onScriptChange={() => {}}
      />
    );
    const text = container.textContent ?? "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toMatch(new RegExp(term, "i"));
    }
  });
});
