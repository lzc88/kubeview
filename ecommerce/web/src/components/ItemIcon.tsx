import { useState } from "react";

import { categoryOf, findItem, iconUrl } from "../catalog";

type Props = { sku: string; decorative?: boolean };

export default function ItemIcon({ sku, decorative = true }: Props) {
  const [broken, setBroken] = useState(false);
  const item = findItem(sku);
  const name = item?.name ?? `Item ${sku}`;

  if (broken || !item) {
    const initials = name
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("");

    return (
      <span
        className="icon icon-fallback"
        style={{ ["--c" as string]: categoryOf(sku)?.color }}
        aria-hidden={decorative}
        aria-label={decorative ? undefined : name}
      >
        {initials}
      </span>
    );
  }

  return (
    <img
      className="icon"
      src={iconUrl(sku)}
      alt={decorative ? "" : name}
      width={64}
      height={64}
      loading="lazy"
      onError={() => setBroken(true)}
    />
  );
}
