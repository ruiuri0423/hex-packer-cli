# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2026-03-27

### Changed
- **Tab3 Register Integrator Logic Enhanced:**
  - Added auto-alignment: If Flash Address < Base Address, auto-align to Base Address
  - Flash addresses now enforced to 256-byte boundaries
  - Dynamic mask byte calculation based on MAX Flash Address - Base Address
  - Gap detection: Flash address gaps = mask enable bit = 0
  - Gap areas in HEX output filled with 0xFF padding
  - Enhanced debug output showing bit-to-address mapping with gaps

### Added
- `validate_and_align_flash_address()` - Address validation and auto-alignment
- `calculate_dynamic_mask_bytes()` - Dynamic mask byte length calculation
- `calculate_enable_mask_with_gaps()` - Gap-aware mask calculation
- `detect_flash_address_gaps()` - Gap detection for HEX generation
- Mask byte length label in GUI

## [1.0.0] - 2026-03-27

### Added
- Initial release
- Firmware Packer with multi-section support
- CRC16 calculation (Verilog-compatible)
- Register Integrator with dynamic Enable Mask
- M0 HEX Converter (Intel HEX / Raw HEX)
- Single Map Viewer with gap detection
- Full GUI interface (Tkinter)
- CLI headless execution mode
- Complete documentation (README, API docs, statistics)
