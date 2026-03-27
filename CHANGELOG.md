# Changelog

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
- **NEW:** Test samples with standalone logic test script

### Verified
- ✅ Auto-alignment: Flash < Base → 對齊到 Base
- ✅ 256-byte boundary 對齊
- ✅ 動態 Mask Byte 計算 (17 bits → 3 bytes for Max=0x2000)
- ✅ Gap 檢測 (Gap #1, Gap #2)
- ✅ HEX Gap 填補 0xFF

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
