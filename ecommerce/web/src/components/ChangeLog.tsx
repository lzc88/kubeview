import { ArrowRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import type { StatusEvent } from "../api";
import { clock } from "../format";
import StatusTag from "./StatusTag";

export default function ChangeLog({ history }: { history: StatusEvent[] }) {
  return (
    <ol className="changes">
      <AnimatePresence initial={false}>
        {history.map((event) => (
          <motion.li
            key={event.id}
            className="change"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          >
            {event.from_status ? (
              <StatusTag status={event.from_status} />
            ) : (
              <span className="tag CREATED">Created</span>
            )}
            <ArrowRight size={16} className="arrow" aria-label="changed to" />
            <StatusTag status={event.to_status} />

            <span className="when">
              <time dateTime={event.at}>{clock(event.at)}</time>
              <small title={event.pod}>{event.pod.slice(0, 12)}</small>
            </span>
          </motion.li>
        ))}
      </AnimatePresence>
    </ol>
  );
}
