import { DDRAGON_VERSION, ITEMS } from "./items";

export { ITEMS };

export type CategoryId =
  | "attack"
  | "ability"
  | "defense"
  | "boots"
  | "support"
  | "starter"
  | "component"
  | "consumable"
  | "other";

export type Category = {
  id: CategoryId;
  name: string;
  color: string;
};

export type Item = {
  sku: string;
  name: string;
  price: string;
  category: CategoryId;
};

export const CATEGORIES: Category[] = [
  { id: "attack", name: "Attack damage", color: "var(--cat-attack)" },
  { id: "ability", name: "Ability power", color: "var(--cat-ability)" },
  { id: "defense", name: "Defense", color: "var(--cat-defense)" },
  { id: "boots", name: "Boots", color: "var(--cat-boots)" },
  { id: "support", name: "Support", color: "var(--cat-support)" },
  { id: "starter", name: "Starter", color: "var(--cat-starter)" },
  { id: "component", name: "Components", color: "var(--cat-component)" },
  { id: "consumable", name: "Consumables", color: "var(--cat-consumable)" },
  { id: "other", name: "Other", color: "var(--muted)" },
];

const bySku = new Map(ITEMS.map((item) => [item.sku, item]));

export function findItem(sku: string): Item | undefined {
  return bySku.get(sku);
}

export function iconUrl(sku: string): string {
  return `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/item/${sku}.png`;
}

export function categoryOf(sku: string): Category | undefined {
  const item = findItem(sku);
  return CATEGORIES.find((category) => category.id === item?.category);
}
