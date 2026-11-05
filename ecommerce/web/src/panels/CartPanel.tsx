import { CircleAlert, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { ApiError, createOrder, startPayment, type Order } from "../api";
import type { Focus } from "../App";
import { findItem } from "../catalog";
import CartLines, { cartTotal } from "../components/CartLines";
import { sgd } from "../format";
import {
  attemptFor,
  clearAttempt,
  clearCart,
  setUser,
  useCart,
  useUser,
} from "../store";
import { usePageRestore } from "../usePageRestore";

type Step = "idle" | "creating" | "paying" | "redirecting";

const STEP_LABEL: Record<Exclude<Step, "idle">, string> = {
  creating: "Creating order…",
  paying: "Starting payment…",
  redirecting: "Opening Stripe…",
};

export default function CartPanel({ onPlaced }: { onPlaced: (focus: Focus) => void }) {
  const cart = useCart();
  const savedUser = useUser();
  const [name, setName] = useState(savedUser);
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<{ message: string; retryable: boolean } | null>(null);

  usePageRestore(() => setStep("idle"));

  const items = Object.entries(cart)
    .filter(([sku]) => findItem(sku))
    .map(([sku, qty]) => ({ sku, qty, unit_price: findItem(sku)!.price }));

  const total = cartTotal(cart);
  const busy = step !== "idle";
  const ready = items.length > 0 && name.trim().length > 0 && !busy;

  async function placeOrder() {
    const userId = name.trim();
    setUser(userId);
    setError(null);
    setStep("creating");

    const sorted = [...items].sort((a, b) => a.sku.localeCompare(b.sku));
    const attempt = attemptFor(JSON.stringify({ userId, sorted }));
    let order: Order;

    try {
      order = (await createOrder(userId, sorted, attempt.key)).data;
    } catch (caught) {
      setStep("idle");

      if (caught instanceof ApiError && caught.status === 422) {
        clearAttempt();
        setError({ message: `The order was rejected: ${caught.message}`, retryable: false });
      } else {
        setError({
          message: `${(caught as Error).message} Retrying reuses the same idempotency key, so you won't get a duplicate order.`,
          retryable: true,
        });
      }

      return;
    }

    clearAttempt();
    clearCart();
    setStep("paying");

    const payment = await startPayment(order.id);

    if (payment.redirected) {
      setStep("redirecting");
      return;
    }

    onPlaced({ id: order.id, notice: payment.notice });
    setStep("idle");
  }

  return (
    <section className="panel" aria-labelledby="cart-title">
      <h2 className="panel-title" id="cart-title">
        Cart <small>{items.length}</small>
      </h2>

      <div className="panel-body" aria-busy={busy}>
        {items.length === 0 ? (
          <p className="empty">Click an item to add it here.</p>
        ) : (
          <CartLines cart={cart} />
        )}
      </div>

      <div className="panel-foot">
        <label className="field">
          <span>Username</span>
          <input
            value={name}
            maxLength={40}
            placeholder="who's buying?"
            autoComplete="username"
            disabled={busy}
            onChange={(event) => setName(event.target.value)}
            onBlur={() => setUser(name)}
          />
        </label>

        <div className="total">
          <span>Total</span>
          <span>{sgd(total)}</span>
        </div>

        <button type="button" className="btn" disabled={!ready} onClick={placeOrder}>
          {busy && <LoaderCircle size={16} className="spin" aria-hidden />}
          {busy ? STEP_LABEL[step as Exclude<Step, "idle">] : "Place order & pay"}
        </button>

        {error && (
          <div className="alert" role="alert">
            <CircleAlert size={16} aria-hidden />
            <div>
              {error.message}{" "}
              {error.retryable && (
                <button type="button" className="link" disabled={!ready} onClick={placeOrder}>
                  Try again
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
