export type OrderStatus =
  | "PENDING"
  | "PROCESSING"
  | "PAID"
  | "PAYMENT_FAILED"
  | "CANCELLED"
  | "SHIPPED"
  | "DELIVERED";

export type OrderItem = { sku: string; qty: number; unit_price: string };

export type StatusEvent = {
  id: number;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  pod: string;
  at: string;
};

export type Order = {
  id: number;
  user_id: string;
  total: string;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  history: StatusEvent[];
};

export type PayResult = Order & { checkout_url: string | null };

export class ApiError extends Error {
  constructor(
    readonly status: number | null,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(
  method: string,
  path: string,
  init: { body?: unknown; headers?: Record<string, string> } = {},
): Promise<{ status: number; data: T }> {
  let response: Response;

  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: { "Content-Type": "application/json", ...init.headers },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(null, "Couldn't reach the orders service. Is it running?");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, describe(response.status, data));
  }

  return { status: response.status, data: data as T };
}

function describe(status: number, data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((entry) => entry?.msg ?? String(entry)).join("; ");
  }

  if (status === 502 || status === 503 || status === 504) {
    return `The shop couldn't reach the orders service (HTTP ${status}).`;
  }

  if (status >= 500) {
    return `The orders service failed (HTTP ${status}).`;
  }

  return `Request failed (HTTP ${status}).`;
}

export function createOrder(
  userId: string,
  items: OrderItem[],
  idempotencyKey: string,
) {
  return request<Order>("POST", "/orders", {
    body: { user_id: userId, items },
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function payOrder(orderId: number) {
  return request<PayResult>("POST", `/orders/${orderId}/pay`);
}

export async function getOrder(orderId: number): Promise<Order> {
  return (await request<Order>("GET", `/orders/${orderId}`)).data;
}

export async function listOrders(userId: string): Promise<Order[]> {
  const query = new URLSearchParams({ user_id: userId });
  return (await request<Order[]>("GET", `/orders?${query}`)).data;
}

export type PaymentStart = { redirected: boolean; notice?: string };

export async function startPayment(orderId: number): Promise<PaymentStart> {
  try {
    const { data } = await payOrder(orderId);

    if (data.checkout_url) {
      window.location.assign(data.checkout_url);
      return { redirected: true };
    }

    if (data.status === "PROCESSING") {
      return {
        redirected: false,
        notice: "Payments didn't return a checkout link yet. Try paying again in a moment.",
      };
    }

    return { redirected: false };
  } catch (caught) {
    return {
      redirected: false,
      notice: `Payment couldn't start: ${(caught as Error).message}`,
    };
  }
}

export const LIVE_STATUSES: OrderStatus[] = ["PROCESSING"];

const PAYABLE_STATUSES: OrderStatus[] = ["PENDING", "PROCESSING"];

export function isPayable(status: OrderStatus): boolean {
  return PAYABLE_STATUSES.includes(status);
}
