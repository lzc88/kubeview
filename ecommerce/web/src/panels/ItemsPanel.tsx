import { CATEGORIES, ITEMS } from "../catalog";
import ItemIcon from "../components/ItemIcon";
import { sgd } from "../format";
import { addToCart, useCart } from "../store";

export default function ItemsPanel() {
  const cart = useCart();

  return (
    <section className="panel" aria-labelledby="items-title">
      <h2 className="panel-title" id="items-title">
        Items <small>{ITEMS.length}</small>
      </h2>

      <div className="panel-body">
        {CATEGORIES.map((category) => {
          const items = ITEMS.filter((item) => item.category === category.id);

          if (items.length === 0) {
            return null;
          }

          return (
            <div key={category.id} className="group">
              <h3 className="group-title">{category.name}</h3>

              <ul className="tiles">
                {items.map((item) => {
                  const qty = cart[item.sku] ?? 0;

                  return (
                    <li key={item.sku}>
                      <button
                        type="button"
                        className={qty ? "tile in" : "tile"}
                        onClick={() => addToCart(item.sku)}
                        title={item.name}
                        aria-label={`Add ${item.name}, ${sgd(item.price)}${qty ? `, ${qty} in cart` : ""}`}
                      >
                        <ItemIcon sku={item.sku} />
                        <span className="tile-price">{sgd(item.price)}</span>
                        {qty > 0 && <span className="badge">{qty}</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
