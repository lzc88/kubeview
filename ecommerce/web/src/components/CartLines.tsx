import { Minus, Plus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { findItem } from "../catalog";
import { fromCents, lineTotal, sgd, toCents } from "../format";
import { setQty, type Cart } from "../store";
import ItemIcon from "./ItemIcon";

export function cartTotal(cart: Cart): string {
  const cents = Object.entries(cart).reduce((sum, [sku, qty]) => {
    const item = findItem(sku);
    return item ? sum + toCents(item.price) * qty : sum;
  }, 0);

  return fromCents(cents);
}

export default function CartLines({ cart }: { cart: Cart }) {
  const lines = Object.entries(cart).filter(([sku]) => findItem(sku));

  return (
    <ul className="lines">
      <AnimatePresence initial={false}>
        {lines.map(([sku, qty]) => {
          const item = findItem(sku)!;

          return (
            <motion.li
              key={sku}
              className="line"
              layout
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            >
              <ItemIcon sku={sku} />
              <span className="line-name">{item.name}</span>
              <span className="line-total">{sgd(lineTotal(item.price, qty))}</span>

              <span className="line-qty">
                <span className="stepper">
                  <button
                    type="button"
                    onClick={() => setQty(sku, qty - 1)}
                    aria-label={`One fewer ${item.name}`}
                  >
                    <Minus size={13} aria-hidden />
                  </button>
                  <span aria-label="Quantity">{qty}</span>
                  <button
                    type="button"
                    onClick={() => setQty(sku, qty + 1)}
                    aria-label={`One more ${item.name}`}
                  >
                    <Plus size={13} aria-hidden />
                  </button>
                </span>
                <span className="unit">× {sgd(item.price)}</span>
                <button
                  type="button"
                  className="remove"
                  onClick={() => setQty(sku, 0)}
                  aria-label={`Remove ${item.name}`}
                >
                  <X size={15} aria-hidden />
                </button>
              </span>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}
