# Changelog

## [1.2.1] - 2026-03-27

### Fixed
- **Bug Fix: Type conversion errors**
  - Fixed "int cannot be converted" error in address handling
  - Added type checking and defensive programming
  - Fixed enabled.lower() potential AttributeError
  - Fixed address calculation in add_test_table()

### Protected Functions
- `validate_and_align_flash_address()` - Handle negative/invalid inputs
- `calculate_dynamic_mask_bytes()` - Handle edge cases
- `calculate_enable_mask_with_gaps()` - Added exception handling
- `detect_flash_address_gaps()` - Added exception handling
- `get_test_tables()` - Added type checking and validation

## [1.2.0] - 2026-03-27

### Added
- **NEW: Tab 5 - Logic Test Tab**
  - Test Scenario Setup (Base Address, Tables)
  - Address Alignment Test
  - Dynamic Mask Calculation Test
  - Gap Detection Test
  - HEX Buffer Generation Test
  - Preset loading (3-table scenario)
  - Quick single test mode
  - Detailed mask calculation view

## [1.1.0] - 2026-03-27

### Changed
- **Tab3 Register Integrator Logic Enhanced:**
  - Auto-alignment, 256-byte boundaries
  - Dynamic mask byte calculation
  - Gap detection and 0xFF padding

## [1.0.0] - 2026-03-27

### Added
- Initial release with Firmware Packer, M0 HEX Converter, Register Integrator, Single Map Viewer
