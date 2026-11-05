import {
  Ban,
  CircleCheck,
  CircleDashed,
  CircleX,
  Hourglass,
  PackageCheck,
  Truck,
  type LucideIcon,
} from "lucide-react";

import type { OrderStatus } from "../api";

const LOOK: Record<OrderStatus, { label: string; Icon: LucideIcon }> = {
  PENDING: { label: "Pending", Icon: CircleDashed },
  PROCESSING: { label: "Processing", Icon: Hourglass },
  PAID: { label: "Paid", Icon: CircleCheck },
  PAYMENT_FAILED: { label: "Payment failed", Icon: CircleX },
  CANCELLED: { label: "Cancelled", Icon: Ban },
  SHIPPED: { label: "Shipped", Icon: Truck },
  DELIVERED: { label: "Delivered", Icon: PackageCheck },
};

type Props = { status: OrderStatus; large?: boolean };

export default function StatusTag({ status, large = false }: Props) {
  const { label, Icon } = LOOK[status] ?? { label: status, Icon: CircleDashed };

  return (
    <span className={`tag ${status}${large ? " lg" : ""}`}>
      <Icon
        size={large ? 17 : 14}
        strokeWidth={2.4}
        aria-hidden
      />
      {label}
    </span>
  );
}
