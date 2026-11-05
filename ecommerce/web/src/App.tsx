import { useState } from "react";

import CartPanel from "./panels/CartPanel";
import ItemsPanel from "./panels/ItemsPanel";
import OrdersPanel from "./panels/OrdersPanel";

export type Focus = { id: number; notice?: string };

function focusFromPath(): Focus | null {
  const match = window.location.pathname.match(/^\/orders\/(\d+)\/?$/);

  if (!match) {
    return null;
  }

  window.history.replaceState(null, "", "/");
  return { id: Number(match[1]) };
}

const initialFocus = focusFromPath();

export default function App() {
  const [focus, setFocus] = useState<Focus | null>(initialFocus);
  const [version, setVersion] = useState(0);

  function onPlaced(next: Focus) {
    setFocus(next);
    setVersion((value) => value + 1);
  }

  return (
    <div className="app">
      <header className="top">
        <span className="wordmark">welcome to my shop</span>
        <span className="hint">Stripe test card 4242 4242 4242 4242</span>
      </header>

      <main className="columns">
        <ItemsPanel />
        <CartPanel onPlaced={onPlaced} />
        <OrdersPanel focus={focus} onFocus={setFocus} version={version} />
      </main>
    </div>
  );
}
