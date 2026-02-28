# UI_MODIFICATION_PROTOCOL.md

When modifying UI for the Pathfinder 1e Campaign Manager, follow this protocol.

This app must function as:
- A Progressive Web App (installable, offline-capable, locally hosted for table LAN access)
- Tablet-first (iPad + Android tablet)
- Modern "Apple-like" app shell
- With optional Classic RPG sheet mode (parchment aesthetic)

---

## Before Implementing

### 1. Confirm
- Service worker strategy unaffected
- Manifest remains valid
- Offline minimum viable functionality preserved
- Touch targets >= 44px
- No dense SaaS dashboard aesthetic

### 2. Preserve
- Situation-based UX (turn-time focus)
- Calculated final numbers shown primarily
- Print-ready classic sheet
- Modular panel mode for combat

### 3. When Adding UI
- Separate "App Shell" styling from "Classic Sheet Mode"
- Ensure both can coexist
- Ensure consistent navigation patterns

### 4. If Introducing New Components
- Describe component hierarchy
- Show how it scales to tablet
- Include accessibility considerations

---

## Required Output for UI Changes

1. **Design Rationale** — Why this change, what problem it solves
2. **Component Structure** — Hierarchy, parent/child, reuse
3. **Files Modified** — Exact list with nature of change
4. **PWA Considerations** — Cache impact, offline behavior, manifest
5. **Visual Consistency Check** — Fonts, spacing, color tokens, both modes
6. **Regression Risk Check** — What existing UI could break

---

End
