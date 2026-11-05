import { ChevronDown, Info, LoaderCircle } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

import { isPayable, startPayment, type Order } from "../api";
import { findItem } from "../catalog";
import { lineTotal, sgd, when } from "../format";
import { usePageRestore } from "../usePageRestore";
import ChangeLog from "./ChangeLog";
import ItemIcon from "./ItemIcon";
import StatusTag from "./StatusTag";

type Props = {
  order: Order;
  open: boolean;
  notice?: string;
  onToggle: () => void;
  onNotice: (notice?: string) => void;
  onChanged: () => void;
};

export default function OrderCard({ order, open, notice, onToggle, onNotice, onChanged }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [paying, setPaying] = useState(false);

  usePageRestore(() => setPaying(false));

  useEffect(() => {
    if (open) {
      ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [open]);

  async function pay() {
    setPaying(true);
    onNotice(undefined);

    const payment = await startPayment(order.id);

    if (payment.redirected) {
      return;
    }

    onNotice(payment.notice);
    setPaying(false);
    onChanged();
  }

  return (
    <div ref={ref} className={open ? "order open" : "order"}>
      <button type="button" className="row" onClick={onToggle} aria-expanded={open}>
        <span className="row-name">#{order.id}</span>
        <span className="row-meta">{when(order.created_at)}</span>
        <StatusTag status={order.status} />
        <span className="row-total">{sgd(order.total)}</span>
        <ChevronDown size={16} className="chev" aria-hidden />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="order-detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="order-inner">
              {notice && (
                <div className="alert info" role="status">
                  <Info size={16} aria-hidden />
                  <div>{notice}</div>
                </div>
              )}

              <ul className="order-items">
                {order.items.map((item) => (
                  <li key={item.sku}>
                    <ItemIcon sku={item.sku} />
                    <span className="row-name">{findItem(item.sku)?.name ?? item.sku}</span>
                    <span className="row-meta">
                      {item.qty} × {sgd(item.unit_price)}
                    </span>
                    <span className="row-total">
                      {sgd(lineTotal(item.unit_price, item.qty))}
                    </span>
                  </li>
                ))}
              </ul>

              {order.history.length > 0 && <ChangeLog history={order.history} />}

              {isPayable(order.status) && (
                <button type="button" className="btn" disabled={paying} onClick={pay}>
                  {paying && <LoaderCircle size={16} className="spin" aria-hidden />}
                  {paying ? "Starting payment…" : `Pay ${sgd(order.total)}`}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
