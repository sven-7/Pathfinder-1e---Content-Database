# PWA_REQUIREMENTS

## Deployment Model

Locally hosted PWA. The host machine runs `python scripts/run_app.py` and players
at the table access the app via local network (e.g. `http://192.168.x.x:8000`).
Devices install the PWA from the LAN URL. No cloud hosting required.

## Must-Haves (Phase PWA-0)
- Web app manifest (name, icons, display=standalone, start_url)
- Service worker:
  - cache static assets (HTML/CSS/JS/fonts)
  - offline fallback route for core screens
  - cache-first strategy for content DB queries (spells, feats, classes)
- Responsive layout:
  - tablet portrait + landscape
  - large touch controls (>= 44px targets)
- Viewport meta tag for mobile/tablet

## Offline Minimum Viable Use
When offline (or if LAN host is down), a user can:
- open the app
- browse character library (cached from last session)
- open a character sheet
- update local state (HP, conditions, spell dots, notes)
- export/save locally if server isn't reachable

## Nice-to-Haves (Later)
- background sync when LAN host comes back online
- conflict resolution strategy for multi-device edits
- push notification when GM updates campaign state

---

End
