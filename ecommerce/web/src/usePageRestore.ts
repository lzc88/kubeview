import { useEffect, useRef } from "react";

export function usePageRestore(onRestore: () => void) {
  const latest = useRef(onRestore);
  latest.current = onRestore;

  useEffect(() => {
    function handle(event: PageTransitionEvent) {
      if (event.persisted) {
        latest.current();
      }
    }

    window.addEventListener("pageshow", handle);
    return () => window.removeEventListener("pageshow", handle);
  }, []);
}
