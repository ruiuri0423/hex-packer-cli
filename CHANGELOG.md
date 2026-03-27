# Changelog

## [1.2.2] - 2026-03-27

### Fixed
- **Tab3 HEX Generation Bug Fix**
  - Now dumps ALL loaded tables to HEX (not just enabled)
  - Mask only for enabled tables (enabled=1, disabled=0)
  - Disabled tables are still included in HEX output
  - Gap areas filled with 0xFF

### Changed Logic
- `btn_int_generate()`: Now processes ALL tables, not just enabled
- `refresh_int_tree()`: Calculate mask based on ALL tables max address
- `_debug_mask_mapping()`: Show all tables with status

### Example
- 60 tables loaded, 30 enabled, 30 disabled
- OLD: Only 30 enabled tables dumped to HEX
- NEW: All 60 tables dumped to HEX

## [1.2.1] - 2026-03-27

### Fixed
- Bug Fix: Type conversion errors
- Defensive programming added

## [1.2.0] - 2026-03-27

### Added
- NEW: Tab 5 - Logic Test Tab

## [1.1.0] - 2026-03-27

### Changed
- Tab3 Register Integrator Logic Enhanced

## [1.0.0] - 2026-03-27

### Added
- Initial release
