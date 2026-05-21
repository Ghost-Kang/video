import { useNavigate } from "react-router-dom";
import { HotCardGrid } from "../components/landing/HotCardGrid";
import { UrlFallback } from "../components/landing/UrlFallback";
import { WaitlistCta } from "../components/landing/WaitlistCta";
import type { FeaturedCard } from "../components/landing/HotCard";

function sessionId() {
  return `session-${Date.now().toString(36)}`;
}

export function Landing() {
  const navigate = useNavigate();
  const pick = (card: FeaturedCard) => {
    navigate(`/chat/${sessionId()}?analysis_id=${card.fixture_analysis_id}`);
  };

  return (
    <main className="min-h-screen bg-stone-50 px-4 py-10">
      <div className="mx-auto max-w-[720px]">
        <h1 className="mb-6 text-2xl font-medium text-stone-900">
          看到刷屏的视频，想做一条自己的？挑一张开始 ↓
        </h1>
        <HotCardGrid onPick={pick} />
        <UrlFallback onSubmit={() => navigate(`/chat/${sessionId()}`)} />
      </div>
      <WaitlistCta />
    </main>
  );
}
