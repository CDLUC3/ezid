# AGENTS.md

## Overview
EZID is a Django application for managing persistent identifiers (DOIs, ARKs).
- **Backend:** Python 3.11+ / Django 4.2+
- **Frontend Assets:** Node 24 (`.nvmrc`), Gulp asset pipeline
- **Frameworks:** Bootstrap 5.3 (CDN in `templates/layouts/base.html`), jQuery (`dev/js/vendor/`)

## UI & CSS Architecture
EZID loads two stylesheets in `templates/layouts/base.html`:
1. `main2.min.css` (primary styles compiled from SCSS)
2. `main.css` (legacy static stylesheet)

### Styling Rules
- **Source of truth:** `dev/scss/` (entrypoint: `dev/scss/main2.scss`). Always edit SCSS here.
- **Never edit compiled files directly:** Do not manually edit `ui_library/css/main2.min.css` or `static_src/stylesheets/main2.min.css`.
- **Compile command:** Run `npx gulp build` from the repo root after changing SCSS or JS. This compiles assets to `ui_library/` and automatically copies `main2.min.css` and `main2.min.js` into `static_src/`.
- **Legacy styles:** `static_src/stylesheets/main.css` is uncompiled. Only edit directly if a style exists exclusively there; prefer migrating styles to `dev/scss/`.
- **External content warning:** "About" and documentation pages originate from a separate `info-pages` repository—do not edit local static copies of those pages.

## JavaScript
- Source files reside in `dev/js/` (bundled and minified into `main2.min.js` via `npx gulp build`).
- Standalone or page-specific scripts live unbundled in `static_src/javascripts/`.

## Templates & Accessibility (a11y)
- **Django Templates:** Located in `templates/` (layouts in `templates/layouts/`, components/partials in `templates/includes/`, features in `templates/<feature>/`).
- **UI Demos:** HTML component mockups live in `dev/` (`dev/component_*.html`, `dev/layout_*.html`). When altering a UI component, keep its demo HTML in sync.
- **Accessibility Priorities:**
  - Semantic HTML (`<main>`, `<nav>`, `<header>`, `<footer>`, `<fieldset>`, `<legend>`).
  - Form labels: Every input must have an explicit, associated `<label for="...">` or appropriate `aria-label`/`aria-labelledby`.
  - Keyboard navigation: Interactive elements must be focusable with visible `:focus-visible` styles.
  - ARIA attributes: Use `aria-expanded`, `aria-controls`, `aria-live`, and `aria-hidden` accurately for toggles, alerts, and dynamic content.
  - Color contrast: Maintain WCAG 2.1 AA ratios (4.5:1 for normal text, 3:1 for large text and UI components).

## Common Commands
```bash
# Node & UI Build
nvm use
npm install
npx gulp build               # Compile SCSS/JS and copy to static_src/
npx gulp                     # Launch local UI preview server (localhost:3000)

# Django & Tests
pytest --ds=settings.tests tests/           # Run test suite
pytest --ds=settings.tests tests/<file>.py  # Run single test file
python manage.py runserver                  # Run Django dev server
```
