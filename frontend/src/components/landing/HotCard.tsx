import { ArrowRight, ImageIcon } from "lucide-react";

export interface FeaturedCard {
  id: string;
  niche: string;
  thumbnail_url: string;
  title_three_lines: string[];
  fixture_analysis_id: string;
}

export function HotCard({ card, onPick }: { card: FeaturedCard; onPick: (card: FeaturedCard) => void }) {
  return (
    <article className="rounded-2xl bg-white shadow-sm border border-stone-200 p-5 hover:shadow-md transition-shadow">
      <div className="aspect-video rounded-xl bg-stone-100 flex items-center justify-center overflow-hidden mb-4">
        {card.thumbnail_url ? <img src={card.thumbnail_url} alt="" className="h-full w-full object-cover" /> : <ImageIcon className="h-8 w-8 text-stone-300" />}
      </div>
      <p className="text-sm text-orange-600 font-medium mb-2">今天值得拍</p>
      <h2 className="text-lg font-medium text-stone-900 mb-2">{card.title_three_lines[0]}</h2>
      <p className="text-base text-stone-600 mb-5">
        {card.title_three_lines.slice(1).join(" / ")}
      </p>
      <button
        type="button"
        onClick={() => onPick(card)}
        className="w-full inline-flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white rounded-xl py-3 px-5 font-medium transition-colors"
      >
        挑这一张
        <ArrowRight className="h-4 w-4" aria-hidden />
      </button>
    </article>
  );
}
