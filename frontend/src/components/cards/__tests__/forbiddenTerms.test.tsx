import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ScriptCard } from "../ScriptCard";
import { ShotCard } from "../ShotCard";
import { PublishPackCard } from "../PublishPackCard";
import { MOCK_BAOMAM_ANALYSIS, buildDefaultScript } from "../../../fixtures/baomamFushi001";
import { FORBIDDEN_TERMS } from "../../../lib/cardCopy";

function assertNoForbiddenTerms(text: string, label: string) {
  for (const term of FORBIDDEN_TERMS) {
    const pattern = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
    expect(text, `${label} contains forbidden term "${term}"`).not.toMatch(pattern);
  }
}

describe("forbidden terms in rendered card HTML", () => {
  const script = buildDefaultScript(MOCK_BAOMAM_ANALYSIS);

  it("ScriptCard, ShotCard, PublishPackCard have zero forbidden terms in DOM text", () => {
    const { container: scriptEl } = render(
      <ScriptCard
        analysis={MOCK_BAOMAM_ANALYSIS}
        script={script}
        onScriptChange={() => {}}
      />
    );
    assertNoForbiddenTerms(scriptEl.textContent ?? "", "ScriptCard");

    for (const scene of MOCK_BAOMAM_ANALYSIS.scenes) {
      const { container } = render(<ShotCard scene={scene} />);
      assertNoForbiddenTerms(container.textContent ?? "", `ShotCard#${scene.scene_index}`);
    }

    const { container: publishEl } = render(
      <PublishPackCard script={script} analysis={MOCK_BAOMAM_ANALYSIS} />
    );
    assertNoForbiddenTerms(publishEl.textContent ?? "", "PublishPackCard");
  });
});
