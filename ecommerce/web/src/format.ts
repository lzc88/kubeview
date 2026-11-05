const money = new Intl.NumberFormat("en-SG", {
  style: "currency",
  currency: "SGD",
  currencyDisplay: "narrowSymbol",
});

export function sgd(amount: string | number): string {
  return `S${money.format(Number(amount))}`;
}

export function toCents(amount: string): number {
  return Math.round(Number(amount) * 100);
}

export function fromCents(cents: number): string {
  return (cents / 100).toFixed(2);
}

export function lineTotal(unitPrice: string, qty: number): string {
  return fromCents(toCents(unitPrice) * qty);
}

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-SG", { hour12: false });
}

export function when(iso: string): string {
  return new Date(iso).toLocaleString("en-SG", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
