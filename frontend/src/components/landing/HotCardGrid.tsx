import cards from "../../data/featured_cards.json";
import { HotCard, type FeaturedCard } from "./HotCard";

export function HotCardGrid({ onPick }: { onPick: (card: FeaturedCard) => void }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {(cards as FeaturedCard[]).map((card) => (
        <HotCard key={card.id} card={card} onPick={onPick} />
      ))}
    </div>
  );
}
