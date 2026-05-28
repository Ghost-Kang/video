export function truncateUrlMiddle(url: string, maxChars = 50): string {
  if (url.length <= maxChars) return url;
  const half = Math.floor((maxChars - 3) / 2);
  return `${url.slice(0, half)}...${url.slice(-half)}`;
}
