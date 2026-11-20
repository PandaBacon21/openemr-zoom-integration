# ZHR Skin Framework for OpenEMR – Claude Code Handoff

Nov 20, 2026 · @Josh Aiken

## Purpose and context

Build a switchable "skin" layer for our custom OpenEMR image so a demo user can flip the whole app between stock OpenEMR, an Epic-style layout, and later other EHR looks (Cerner-style first). This is an internal demo tool only, never shipped to customers.

- **Codebase:** our own custom OpenEMR (PHP) Docker image. Confirm the exact OpenEMR version before starting; several paths below vary by version.
- **Design reference:** the Epic-style mockups (Flow Board, Schedule, Patient Workspace, Theme Tokens) live on the [design canvas](https://claude.ai/artifact/V2kJM61q3Vj5UirVjhE8Pu). The token values you need are copied into the Epic-style skin spec section below, so you can work without the canvas.
- **Demo data:** provider Chen, Michael at Zoomly Medical Center - CO, with patients Singh (157), Kapoor (135), Hill (134) and Romero (184) on 2026-11-20.

Think of OpenEMR as the house and each skin as a set of furniture and paint. The framework is the moving crew: it must be able to swap one set for another without touching the walls (core PHP) wherever possible.

## Goals and non-goals

The framework ships first; the Epic-style skin is its first real consumer and the proof that it works.

**Goals**

1. A pluggable skin registry: adding a new skin means adding a folder, not editing core.
2. A settings page where each user picks a skin, and an admin sets the default and whether users may choose.
3. "Stock OpenEMR" is always available as a skin and renders exactly as today.
4. The Epic-style skin covers every page in the P0 and P1 tiers of the coverage matrix.
5. Core OpenEMR files stay untouched wherever an event or CSS can do the job; any core edit is small, guarded, and listed in a patch log.

**Non-goals**

- Pixel-perfect copies of Epic or Cerner, or any of their logos, names or icons.
- Changing clinical behavior, data, or workflows. Skins change presentation only.
- The patient portal, the API, and mobile layouts beyond "doesn't break."
- Production hardening for customers.

## Architecture: the skin framework

Build everything as one OpenEMR custom module, `oe-module-zhr-skins`, that resolves the active skin per request and injects that skin's CSS, JS and a `data-zhr-skin` attribute into every page.

### How a page gets skinned

1. A user loads any page. OpenEMR's main shell is one top window, and every tab is its own iframe that calls `OpenEMR\Core\Header::setupHeader()`.
2. The module's `SkinResolver` picks the skin in this order: the user's choice → the admin default → `openemr-stock`. If the admin has turned user choice off, it skips the first step.
3. The module adds the skin's stylesheets and scripts to that page through OpenEMR's header events (see the verify-first list) and sets `<html data-zhr-skin="epic">`.
4. Every skin CSS rule is scoped under that attribute, so `openemr-stock` is simply "no attribute, no extra CSS."
5. Switching skins saves the preference, then reloads the top window so the shell and all open iframes pick it up together.

### Module layout

```
interface/modules/custom_modules/oe-module-zhr-skins/
  openemr.bootstrap.php        # registers event listeners + menu item
  info.txt                     # module name for the Modules Manager
  table.sql                    # module tables, if any (see settings page)
  src/
    Bootstrap.php              # wires listeners
    SkinRegistry.php           # discovers skins/*/skin.json
    SkinResolver.php           # user -> admin default -> stock
    SkinAssetInjector.php      # header style/script events, html attribute
    TemplateOverrides.php      # optional structural swaps (see below)
  public/
    settings.php               # the skin settings page
  skins/
    openemr-stock/skin.json    # no assets; the control case
    epic/
      skin.json
      css/tokens.css           # --zhr-* variables
      css/base.css             # Bootstrap + global component overrides
      css/shell.css            # top bar, workspace tabs, patient bar
      css/pages/*.css          # one file per page group (flowboard, calendar...)
      js/shell.js              # small DOM tweaks the CSS can't do
      preview.png              # thumbnail for the settings page
    cerner/                    # later; empty stub proves pluggability
```

### The skin manifest

```json
{
  "id": "epic",
  "name": "Epic-style",
  "description": "Dark system bar, workspace tabs, left patient banner",
  "version": "0.1.0",
  "css": ["css/tokens.css", "css/base.css", "css/shell.css", "css/pages/*.css"],
  "js": ["js/shell.js"],
  "preview": "preview.png",
  "templates": {}
}
```

`templates` maps a named core template (for example `tabs/patient_data_template`) to a skin-provided replacement. Leave it empty until CSS and JS can't do a job.

### Three layers, in order of preference

1. **Tokens.** CSS variables only. A new skin can start as just a new `tokens.css`.
2. **Component overrides.** Scoped CSS against OpenEMR's existing Bootstrap classes and IDs. Because almost every OpenEMR page uses Bootstrap, this layer alone reskins most of the app.
3. **Structural changes.** Only for layout CSS cannot reach, such as moving the patient bar to a left-side banner. Prefer a small `js/shell.js` DOM move; use a template override only when JS would be fragile.

### CSS scoping rule

```css
/* every rule lives under the skin attribute */
html[data-zhr-skin="epic"] .btn-primary {
  background: var(--zhr-primary);
  border-color: var(--zhr-primary);
  border-radius: 3px;
}
```

No unscoped selectors, no `!important` unless a core inline style forces it (log each one in the patch log with the reason).

## Skin settings page

One page, `public/settings.php` in the module, serves both audiences: every user sees "My skin," and users with the admin ACL also see "Organization defaults."

### What it shows

- **My skin:** a card per registered skin (preview image, name, description) with a radio button, plus "Use organization default." Saving reloads the top window.
- **Organization defaults (admin only):** the default skin for everyone, and an "Allow users to choose their own skin" toggle. When the toggle is off, the My skin section is read-only and shows which skin is enforced.
- **Quick switcher (P1):** a small skin dropdown in the user menu of the top bar, so a demo presenter can flip skins live without opening the settings page.

### Where it lives in the menu

Add the entry with OpenEMR's menu event (`MenuEvent::MENU_UPDATE`) rather than editing the menu JSON: **Miscellaneous → Skin** for everyone and **Admin → Skins** for admins, both pointing to the same page.

### Storage

| Setting | Scope | Where |
| --- | --- | --- |
| User's chosen skin | per user | OpenEMR `user_settings` table, label `zhr_skin` (reuse core's user-setting helpers if present) |
| Default skin | organization | module table `zhr_skin_settings`, key `default_skin` |
| Allow user choice | organization | module table `zhr_skin_settings`, key `allow_user_choice` |

A user whose saved skin has since been removed falls back to the default, then to `openemr-stock`.

### Security conventions

- Every POST carries an OpenEMR CSRF token (`CsrfUtils::collectCsrfToken()` in the form, `CsrfUtils::verifyCsrfToken()` on save).
- The admin section checks `AclMain::aclCheckCore('admin', 'super')` server-side, not only in the UI.
- All output goes through OpenEMR's escaping helpers (`text()`, `attr()`, `js_escape()`).
- The submitted skin id must exist in `SkinRegistry`; reject anything else.

## Page coverage matrix

P0 is the end-to-end demo path (log in → schedule → flow board → open patient → chart a visit) and must be done before anything else; P1 rounds out a full demo; P2 only needs to not look broken. File paths are from recent OpenEMR releases: Claude Code should confirm each one in our image during Phase 0 and correct this table.

| Tier | Page | Menu path | Likely files | Skin work |
| --- | --- | --- | --- | --- |
| P0 | Login | — | `interface/login/login.php`, `templates/login/` | Tokens + layout CSS |
| P0 | Main shell: top menu, workspace tabs, patient bar, user menu | — | `interface/main/tabs/main.php`, `interface/main/tabs/templates/*_template.php` | Structural: `shell.css` + `shell.js` |
| P0 | Calendar day/week/month | Calendar | `interface/main/calendar/` (PostCalendar module templates) | Page CSS |
| P0 | Add/edit appointment dialog | Calendar → click slot | `interface/main/calendar/add_edit_event.php` | Dialog + form CSS |
| P0 | Flow Board | Flow | `interface/patient_tracker/patient_tracker.php` | Page CSS + status pills |
| P0 | Patient Finder | Finder | `interface/main/finder/dynamic_finder.php` | DataTables CSS |
| P0 | Patient dashboard | Patient → Dashboard | `interface/patient_file/summary/demographics.php` | Structural: left patient banner |
| P0 | Encounter summary + forms list | Patient → Visits | `interface/patient_file/encounter/` (`encounter_top.php`, `forms.php`) | Page CSS |
| P0 | Vitals and SOAP forms | Encounter → Clinical | `interface/forms/vitals/`, `interface/forms/soap/` | Form CSS |
| P0 | Messages (inbox) | Messages | `interface/main/messages/messages.php` | Page CSS |
| P1 | Issues: problems, allergies, medications | Patient → Issues | `interface/patient_file/summary/stats_full.php`, `add_edit_issue.php` | Page CSS |
| P1 | Prescriptions | Patient → Rx | `interface/patient_file/summary/rx_frameset.php` | Page CSS |
| P1 | New patient / edit demographics | Patient → New/Search | `interface/new/new_comprehensive.php`, `interface/patient_file/summary/demographics_full.php` | Form CSS |
| P1 | Recalls | Recalls | `interface/main/messages/messages.php` (recalls view) | Page CSS |
| P1 | Fee sheet and checkout | Fees | `interface/forms/fee_sheet/`, `interface/patient_file/pos_checkout.php` | Form CSS |
| P1 | Procedure orders and results | Procedures | `interface/orders/` | Page CSS |
| P1 | Documents | Patient → Documents | document controller under `controller.php` | Page CSS |
| P1 | Reports landing + top 5 demo reports | Reports | `interface/reports/` | Table CSS |
| P1 | Modal dialogs app-wide | — | `library/dialog.js` and Bootstrap modals | Global CSS |
| P2 | Admin: globals, users, facilities | Admin | `interface/super/edit_globals.php`, `interface/usergroup/` | Base CSS only |
| P2 | Billing manager | Fees → Billing | `interface/billing/billing_report.php` | Base CSS only |
| P2 | Flow Board kiosk mode | Flow → Kiosk | `interface/patient_tracker/` | Base CSS only |
| P2 | Popups menu items | Popups | various | Base CSS only |

Rule of thumb: if a page only needs "base CSS only," the tokens + Bootstrap overrides layer should already cover it. A page graduates to its own `css/pages/*.css` file only when the base layer leaves it looking unfinished.

## Epic-style skin spec

The look comes from layout conventions (dark system bar, workspace tabs, left patient banner, dense tables with status pills), not from copied assets. Match the [design canvas](https://claude.ai/artifact/V2kJM61q3Vj5UirVjhE8Pu) for anything not stated here.

### Tokens (`skins/epic/css/tokens.css`)

```css
html[data-zhr-skin="epic"] {
  --zhr-chrome: #34284F;      /* system bar */
  --zhr-menu: #B3264A;        /* app menu button, active tab top border */
  --zhr-primary: #1F5FA8;     /* primary buttons */
  --zhr-link: #1A55A0;
  --zhr-tabstrip: #D9DEE7;    /* workspace tab bar */
  --zhr-tab-inactive: #EEF1F5;
  --zhr-panel: #E8ECF2;       /* filter/settings panels, left rails */
  --zhr-banner: #E3E9F1;      /* patient banner */
  --zhr-grid-head: #DDE3EC;   /* table headers */
  --zhr-row-alt: #F6F8FB;
  --zhr-row-selected: #DCE8F8;
  --zhr-border: #C3CBD8;
  --zhr-border-strong: #9AA6B8; /* inputs, secondary buttons */
  --zhr-text: #1F2430;
  --zhr-text-muted: #4D5666;
  --zhr-font: "Segoe UI", "Noto Sans", Arial, sans-serif;
  --zhr-font-size: 13px;
  --zhr-radius: 3px;
}
```

### Appointment status pills

| Label shown | OpenEMR code | Background | Text | Dot |
| --- | --- | --- | --- | --- |
| Scheduled | `-` (None) | #E6E9EF | #3A4352 | #7A8496 |
| Arrived | `@` | #DCE8F8 | #1A4A8A | #2F6FC4 |
| Roomed | `<` (In exam room) | #EADFF5 | #5A2D82 | #7E4BB0 |
| Checked Out | `>` | #DCEFE4 | #1D5E3A | #2E8A57 |
| No Show | `?` | #FBE3D6 | #8A3A12 | #C2410C |

Any other code (`*`, `+`, `~`, `!`, `#`, `$`, `%`, `x`) gets the Scheduled style plus its OpenEMR title until we decide otherwise. Keep the mapping in one PHP array in the module so the Flow Board and calendar share it.

### Components

- **System bar:** 44px, `--zhr-chrome`, white text. Left: a "ZHR" app-menu button in `--zhr-menu`. Then icon + label links (Schedule, Inbox with count, Flow Board, Patient Lists, Encounter, Reports). Right: patient search box, user initials + name + facility.
- **Workspace tabs:** strip in `--zhr-tabstrip`. Active tab is white with a 3px `--zhr-menu` top border and merges into the page; inactive tabs are `--zhr-tab-inactive`. Patient tabs show a person icon before the name. Every tab keeps OpenEMR's close and refresh behavior.
- **Patient banner:** 240–280px left column in `--zhr-banner`: initials avatar, name, age/sex/DOB, PID, PCP, facility, coverage, phone, an allergy box (#FBE3D6), today's appointment, care team.
- **Chart section nav:** 170–190px vertical list beside the banner; active item white with a 3px `--zhr-menu` inset left edge.
- **Tables:** 13px text, `--zhr-grid-head` header with 12px bold labels, alternating `--zhr-row-alt` rows, `--zhr-row-selected` for the selected row.
- **Filter panels:** `--zhr-panel` box, 11px bold uppercase field labels above 28px inputs, one primary "Apply" button.
- **Buttons:** 30px tall, `--zhr-radius`. Primary = `--zhr-primary` fill; secondary = white with `--zhr-border-strong`; outline = white with primary border and text.
- **Calendar day view:** 22px per 15-minute slot, bold hour labels, 30-minute half labels, an orange (#C2410C) current-time line, appointment blocks tinted by status with a status dot, time, patient link, "PID · visit type · duration," a video button for telehealth, and a status pill.

### Accessibility floor

Text contrast at least 4.5:1 (all pairs above pass), visible keyboard focus on every control, and status never shown by color alone (always a text label).

## Implementation phases

Work in seven phases, in order; finish each phase's checks before starting the next, and stop to report after Phases 0, 2 and 4.

### Phase 0: Discovery (no code changes)

- [ ] Report the OpenEMR version, PHP version, and how our Docker image builds and mounts custom code.
- [ ] Confirm or correct every path in the page coverage matrix.
- [ ] Confirm which header events exist for adding styles and scripts, and whether `MenuEvent::MENU_UPDATE` and the tabs render events exist in this version.
- [ ] Confirm how per-user settings are stored (`user_settings` and its helper functions).
- [ ] Write findings into `docs/zhr-skins/DISCOVERY.md` and stop for review.

### Phase 1: Module skeleton

- [ ] Scaffold `oe-module-zhr-skins` so it installs and enables from the Modules Manager.
- [ ] Add `SkinRegistry` (reads `skins/*/skin.json`, validates ids) and `SkinResolver` (user → default → stock).
- [ ] Add `SkinAssetInjector`: sets `data-zhr-skin` and adds the active skin's CSS/JS on every page, including tab iframes.
- [ ] Ship `openemr-stock` and an `epic` skin whose CSS is one obvious test rule (for example, a colored top border), to prove injection reaches every iframe.

### Phase 2: Settings page

- [ ] Build `public/settings.php` per the settings page section, with CSRF, ACL and escaping.
- [ ] Add the menu entries through the menu event.
- [ ] Saving a skin reloads the top window and every open tab shows the new skin. Stop for review.

### Phase 3: Epic tokens and base layer

- [ ] Write `tokens.css` and `base.css` (Bootstrap buttons, forms, tables, cards, modals, DataTables, nav tabs).
- [ ] Walk every page in the matrix and screenshot it with stock and Epic skins. Most P2 pages should already look acceptable.

### Phase 4: Shell

- [ ] Restyle the top menu into the system bar, the tab bar into workspace tabs, and the user menu.
- [ ] Add the quick skin switcher to the user menu.
- [ ] Stop for review with screenshots.

### Phase 5: P0 pages

- [ ] Flow Board, Calendar and appointment dialog, Patient Finder, Messages, Encounter and its forms, Login.
- [ ] Patient dashboard with the left banner and chart section nav. Try a `shell.js`-only approach first; use a template override only if it's too fragile.

### Phase 6: P1 pages, then a Cerner stub

- [ ] Cover each P1 page.
- [ ] Add `skins/cerner/` with its own `tokens.css` only, to prove a new skin needs no PHP changes.

## Guardrails

These rules keep the skins safe to upgrade, easy to remove, and clear of trademark trouble.

- **Core stays clean.** Prefer events, CSS and JS. Any unavoidable core edit is a few lines guarded by "is the module enabled," commented `// ZHR-SKINS`, and listed in `docs/zhr-skins/PATCHES.md` with the file, line and reason.
- **Disable = gone.** Disabling the module in the Modules Manager must return the app to stock with no leftover CSS, attributes or menu items.
- **Presentation only.** No changes to queries, saved data, ACLs or clinical logic. If a layout needs data a page doesn't load, raise it instead of adding queries.
- **OpenEMR conventions.** CSRF on every POST, `text()`/`attr()`/`js_escape()` on output, ACL checks server-side, PSR-4 classes under the module namespace, no new Composer packages without asking.
- **No vendor IP.** No Epic or Cerner logos, product names, trademarked terms, icons or screenshots in code or assets. Use generic labels (Inbox, Patient banner, Summary) and our ZHR brand. Skin display names stay "Epic-style" and "Cerner-style."
- **Scoped CSS only.** Every selector starts with `html[data-zhr-skin="<id>"]`; `!important` only with a patch-log entry.
- **Ask before** deleting files, changing the Docker build, running database migrations outside the module's `table.sql`, or committing to a shared branch.

## Acceptance criteria and testing

The work is done when a presenter can run the full P0 demo path in the Epic-style skin, flip to stock and back from the user menu, and nothing in the stock skin has changed.

**Acceptance criteria**

- [ ] With `openemr-stock` selected, screenshots of every matrix page match a baseline taken before the module was installed.
- [ ] With `epic` selected, every P0 and P1 page matches the skin spec; P2 pages have no broken layout or unreadable text.
- [ ] A user's skin choice survives logout and login; a second user can hold a different skin at the same time.
- [ ] With "Allow users to choose" off, every user sees the admin default and cannot change it.
- [ ] A non-admin cannot reach or POST the admin section.
- [ ] Disabling the module restores stock with no leftovers.
- [ ] Adding the `cerner` folder makes it appear in the settings page with no PHP edits.

**Testing approach**

- **Screenshot sweep:** a script (Playwright is fine) that logs in as the demo user and captures each matrix page in each skin to `docs/zhr-skins/screens/<skin>/<page>.png`. Run it at the end of Phases 3, 4, 5 and 6.
- **Unit tests:** `SkinRegistry` (bad manifests rejected, unknown ids rejected) and `SkinResolver` (each fallback path).
- **Manual smoke:** the P0 demo path end to end in both skins, including opening and closing tabs and switching skins with several tabs open.

## Verify first and open questions

These came from general knowledge of recent OpenEMR versions, not from our repo, so Claude Code should confirm each one before relying on it.

**Verify in our codebase**

- Header style/script filter events (expected `OpenEMR\Events\Core\StyleFilterEvent` and `ScriptFilterEvent`, dispatched from `Header::setupHeader()`). If absent, fall back to one guarded hook in `src/Core/Header.php`.
- `MenuEvent::MENU_UPDATE` and the tabs render events in `interface/main/tabs/main.php`.
- The user-settings helpers in `library/user.inc.php` and the `user_settings` table.
- Whether OpenEMR's own "General Theme" global is user-overridable. The stock skin should leave that setting alone so existing themes keep working.
- Pages that build their own `<head>` without `Header::setupHeader()`. List them; they need a fallback include.

**Open questions for the owner**

- Should the admin default apply per facility, or one default for the whole install?
- Should the Epic-style skin keep OpenEMR's horizontal patient bar inside non-dashboard pages, or show a slim version of the left banner everywhere a patient is open?
- Which five reports matter for demos?
