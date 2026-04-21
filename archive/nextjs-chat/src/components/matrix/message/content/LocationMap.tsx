"use client";

/**
 * Re-export LocationMapInner for use with next/dynamic in consumer apps.
 *
 * Usage in Next.js apps:
 * ```tsx
 * import dynamic from "next/dynamic";
 * const LocationMap = dynamic(
 *   () => import("@shared/location").then(m => m.LocationMapInner),
 *   { ssr: false, loading: () => <div>Karte wird geladen...</div> }
 * );
 * ```
 *
 * Or use the pre-wrapped LocationMap from this module (requires next/dynamic at runtime).
 */
export { LocationMapInner as LocationMap } from "./LocationMapInner";
