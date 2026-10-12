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

## Informational Pages (`ezid-info-pages`)
Informational pages ("About", FAQs, documentation) originate from a separate repository: [ezid-info-pages](https://github.com/CDLUC3/ezid-info-pages).
- **Source of truth in local dev:** Checked out at `templates/info/` (a separate git clone ignored by EZID's `.gitignore`).
- **Where to make edits:** Edit files directly in `templates/info/`.
- **Separate Git repository & PRs:** Commits and PRs for these pages must be made in the `ezid-info-pages` repository (`git -C templates/info ...`), not the main EZID repository. Deploys incorporate updates from `ezid-info-pages`.
- **Do NOT edit duplicate copies:** Never edit files in `static_src/info/` or `static/info/`. Multiple copies exist (partially through historical commits and `collectstatic`), but editing them will not persist to the deployed site and will cause confusion.

## Common Commands
```bash
# Node & UI Build
nvm use
npm install
npx gulp build               # Compile SCSS/JS and copy to static_src/
npx gulp                     # Launch local UI preview server (localhost:3000)

# Info Pages (ezid-info-pages repo)
git -C templates/info status # Check status of info pages repo
git -C templates/info diff   # View diff in info pages repo

# Django & Tests
pip install -e .                            # Install EZID in editable mode
pip install -r requirements-dev.txt         # Install test dependencies
./prepare_test_db.sh                        # Create/migrate test database (requires local MySQL on 127.0.0.1:3306)
pytest --ds=settings.tests tests/           # Run test suite
pytest --ds=settings.tests tests/<file>.py  # Run single test file
python manage.py runserver                  # Run Django dev server
```
