import { readFile, writeFile } from "node:fs/promises";

const VERSION = "16.21.1";
const SOURCE = `https://ddragon.leagueoflegends.com/cdn/${VERSION}/data/en_US/item.json`;
const OUTPUT = new URL("../src/items.ts", import.meta.url);

const ATTACK_TAGS = ["Damage", "CriticalStrike", "AttackSpeed", "OnHit", "ArmorPenetration", "LifeSteal"];
const DEFENSE_TAGS = ["Health", "Armor", "SpellBlock", "HealthRegen", "Tenacity"];

const SUPPORT_ITEMS = new Set([
  "Ardent Censer",
  "Bloodsong",
  "Celestial Opposition",
  "Dream Maker",
  "Echoes of Helia",
  "Imperial Mandate",
  "Knight's Vow",
  "Locket of the Iron Solari",
  "Mikael's Blessing",
  "Moonstone Renewer",
  "Redemption",
  "Shurelya's Battlesong",
  "Solstice Sleigh",
  "Staff of Flowing Water",
  "Trailblazer",
  "Zaz'Zak's Realmspike",
  "Zeke's Convergence",
]);

function hasAny(tags, wanted) {
  return wanted.some((tag) => tags.includes(tag));
}

function categorize(item) {
  const tags = item.tags ?? [];

  if (tags.includes("Consumable")) return "consumable";
  if (tags.includes("Boots")) return "boots";
  if (item.into?.length) return "component";
  if (hasAny(tags, ["Lane", "Jungle"]) && !item.from?.length) return "starter";
  if (SUPPORT_ITEMS.has(item.name)) return "support";
  if (tags.includes("SpellDamage")) return "ability";
  if (hasAny(tags, ATTACK_TAGS)) return "attack";
  if (hasAny(tags, DEFENSE_TAGS)) return "defense";
  return "other";
}

function isInShop(item) {
  return (
    Number(item.sku) < 100000 &&
    item.maps?.["11"] &&
    item.gold?.purchasable &&
    item.gold.total > 0 &&
    item.inStore !== false &&
    !item.requiredChampion &&
    !item.requiredAlly
  );
}

async function loadSource() {
  const local = process.argv[2];

  if (local) {
    return JSON.parse(await readFile(local, "utf8"));
  }

  const response = await fetch(SOURCE);

  if (!response.ok) {
    throw new Error(`fetch ${SOURCE} failed: ${response.status}`);
  }

  return response.json();
}

const source = await loadSource();

const byName = new Map();

for (const [sku, item] of Object.entries(source.data)) {
  if (!isInShop({ sku, ...item })) continue;

  const existing = byName.get(item.name);

  if (!existing || Number(sku) < Number(existing.sku)) {
    byName.set(item.name, { sku, ...item });
  }
}

const items = [...byName.values()]
  .map((item) => ({
    sku: item.sku,
    name: item.name,
    price: (item.gold.total / 100).toFixed(2),
    category: categorize(item),
  }))
  .sort((a, b) => Number(b.price) - Number(a.price) || a.name.localeCompare(b.name));

const lines = items.map((item) => `  ${JSON.stringify(item)},`);

const file = [
  'import type { Item } from "./catalog";',
  "",
  `export const DDRAGON_VERSION = ${JSON.stringify(VERSION)};`,
  "",
  "export const ITEMS: Item[] = [",
  ...lines,
  "];",
  "",
].join("\n");

await writeFile(OUTPUT, file);

console.log(`wrote ${items.length} items to src/items.ts`);
