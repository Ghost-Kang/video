import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AudioCard } from "../AudioCard";
import { COPY, FORBIDDEN_TERMS } from "../../../lib/cardCopy";

const MOCK_AUDIO = {
  bgm: "舒缓钢琴 + 渐强弦乐",
  voice_pace: "中速口播 220 字/分",
  sound_effects: "结尾 0.5s 留白",
};

describe("AudioCard", () => {
  it("renders all three audio bullets with human labels", () => {
    render(<AudioCard audio={MOCK_AUDIO} />);

    expect(screen.getByText(COPY.audio_header)).toBeInTheDocument();
    expect(screen.getByText(COPY.audio_bgm_label)).toBeInTheDocument();
    expect(screen.getByText(COPY.audio_pace_label)).toBeInTheDocument();
    expect(screen.getByText(COPY.audio_sfx_label)).toBeInTheDocument();
    expect(screen.getByText(MOCK_AUDIO.bgm)).toBeInTheDocument();
    expect(screen.getByText(MOCK_AUDIO.voice_pace)).toBeInTheDocument();
    expect(screen.getByText(MOCK_AUDIO.sound_effects)).toBeInTheDocument();
  });

  it("never displays forbidden schema terms", () => {
    const { container } = render(<AudioCard audio={MOCK_AUDIO} />);
    const text = container.textContent || "";
    for (const term of FORBIDDEN_TERMS) {
      expect(text).not.toContain(term);
    }
  });
});
