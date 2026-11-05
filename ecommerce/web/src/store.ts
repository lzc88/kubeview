import { useSyncExternalStore } from "react";

export type Cart = Record<string, number>;

export type Attempt = { key: string; signature: string };

const listeners = new Set<() => void>();
const cache = new Map<string, unknown>();

function read<T>(name: string, fallback: T): T {
  if (cache.has(name)) {
    return cache.get(name) as T;
  }

  let value = fallback;

  try {
    const raw = localStorage.getItem(name);
    if (raw !== null) {
      value = JSON.parse(raw) as T;
    }
  } catch {
    value = fallback;
  }

  cache.set(name, value);
  return value;
}

function write<T>(name: string, value: T): void {
  cache.set(name, value);

  try {
    localStorage.setItem(name, JSON.stringify(value));
  } catch {
    return;
  } finally {
    listeners.forEach((listener) => listener());
  }
}

window.addEventListener("storage", (event) => {
  if (event.key === null) {
    cache.clear();
  } else {
    cache.delete(event.key);
  }

  listeners.forEach((listener) => listener());
});

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const EMPTY_CART: Cart = {};

export function useCart(): Cart {
  return useSyncExternalStore(subscribe, () => read("kv:cart", EMPTY_CART));
}

export function useUser(): string {
  return useSyncExternalStore(subscribe, () => read("kv:user", ""));
}

export function setUser(name: string): void {
  write("kv:user", name.trim());
}

export function setQty(sku: string, qty: number): void {
  const next = { ...read("kv:cart", EMPTY_CART) };

  if (qty <= 0) {
    delete next[sku];
  } else {
    next[sku] = Math.min(qty, 99);
  }

  write("kv:cart", next);
}

export function addToCart(sku: string): void {
  setQty(sku, (read("kv:cart", EMPTY_CART)[sku] ?? 0) + 1);
}

export function clearCart(): void {
  write("kv:cart", EMPTY_CART);
}

export function attemptFor(signature: string): Attempt {
  const current = read<Attempt | null>("kv:attempt", null);

  if (current && current.signature === signature) {
    return current;
  }

  const attempt = { key: crypto.randomUUID(), signature };
  write("kv:attempt", attempt);
  return attempt;
}

export function clearAttempt(): void {
  write("kv:attempt", null);
}
