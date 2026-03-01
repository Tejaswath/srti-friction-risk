# Figma Export Handoff

Use this file when dropping exported UI code/assets for integration.

## 1) Route mapping

List each screen and target route.

- `Home frame` -> `/`
- `Details frame` -> `/details/:stationId`

## 2) Component mapping

List key exported components and intended app component names.

- `MapHeader.tsx` -> `src/components/MapHeader.tsx`
- `RiskLegend.tsx` -> `src/components/RiskLegend.tsx`

## 3) Typography

Declare font families and weights used.

- Font family: `Inter`
- Weights: `400, 500, 600, 700`

## 4) Spacing and sizing notes

- Base spacing unit: `4px`
- Corner radius scale: `4/8/12`

## 5) Assets inventory

List exported assets and expected import paths.

- `assets/icon-warning.svg` -> `src/assets/icon-warning.svg`
- `assets/pattern-bg.png` -> `src/assets/pattern-bg.png`

## 6) Constraints

- Exported code must remain presentation-only.
- API fetch logic stays in existing page-level data hooks.
- Do not add external icon libraries.
