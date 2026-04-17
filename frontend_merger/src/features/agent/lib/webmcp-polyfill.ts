/**
 * WebMCP Polyfill — exec-09 Phase 4
 *
 * Importiert den @mcp-b/global Polyfill der navigator.modelContext
 * fuer Browser bereitstellt die es noch nicht nativ unterstuetzen.
 * Chrome 146+ hat es nativ, alle anderen brauchen den Polyfill.
 *
 * MUSS als erstes importiert werden bevor Tools registriert werden.
 * Import in layout.tsx oder _app.tsx: import "@/lib/webmcp-polyfill"
 */

import "@mcp-b/global";
