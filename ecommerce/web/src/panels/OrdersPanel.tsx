import { CircleAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { LIVE_STATUSES, listOrders, type Order } from "../api";
import type { Focus } from "../App";
import OrderCard from "../components/OrderCard";
import { useUser } from "../store";
import { usePageRestore } from "../usePageRestore";

const POLL_MS = 3000;
const MAX_POLL_MS = 30000;

type Props = {
  focus: Focus | null;
  onFocus: (focus: Focus | null) => void;
  version: number;
};

export default function OrdersPanel({ focus, onFocus, version }: Props) {
  const user = useUser();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);

  const load = useCallback(async () => {
    const request = ++latestRequest.current;

    if (!user) {
      return;
    }

    try {
      const fresh = await listOrders(user);

      if (request === latestRequest.current) {
        setOrders(fresh);
        setError(null);
      }
    } catch (caught) {
      if (request === latestRequest.current) {
        setError((caught as Error).message);
      }
    }
  }, [user]);

  usePageRestore(load);

  useEffect(() => {
    setOrders(null);
    setError(null);
  }, [user]);

  useEffect(() => {
    load();
  }, [load, version]);

  const live = orders?.some((order) => LIVE_STATUSES.includes(order.status));

  const liveKey = (orders ?? [])
    .filter((order) => LIVE_STATUSES.includes(order.status))
    .map((order) => `${order.id}:${order.status}`)
    .join(",");

  useEffect(() => {
    if (!liveKey) {
      return;
    }

    let delay = POLL_MS;
    let timer: number | undefined;
    let stopped = false;

    async function tick() {
      await load();

      if (!stopped) {
        delay = Math.min(delay * 2, MAX_POLL_MS);
        timer = window.setTimeout(tick, delay);
      }
    }

    timer = window.setTimeout(tick, delay);

    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [liveKey, load, version]);

  return (
    <section className="panel" aria-labelledby="orders-title">
      <h2 className="panel-title" id="orders-title">
        Orders {orders && <small>{orders.length}</small>}
        {live && <span className="live" aria-label="Refreshing" />}
      </h2>

      <div className="panel-body">
        {!user && <p className="empty">Enter a username in the cart to see orders.</p>}

        {error && (
          <div className="alert" role="alert">
            <CircleAlert size={16} aria-hidden />
            <div>
              {error}{" "}
              <button type="button" className="link" onClick={load}>
                Try again
              </button>
            </div>
          </div>
        )}

        {user && orders === null && !error && <p className="empty">Loading…</p>}

        {orders?.length === 0 && <p className="empty">No orders for {user} yet.</p>}

        {orders && orders.length > 0 && (
          <ul className="rows">
            {orders.map((order) => (
              <li key={order.id}>
                <OrderCard
                  order={order}
                  open={focus?.id === order.id}
                  notice={focus?.id === order.id ? focus.notice : undefined}
                  onToggle={() => onFocus(focus?.id === order.id ? null : { id: order.id })}
                  onNotice={(notice) => onFocus({ id: order.id, notice })}
                  onChanged={load}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
