# hex-packer-cli Release

## Version: 1.2.3

## Contents

| File | Description |
|------|-------------|
| `bin/hex-packer-cli` | Linux x86_64 CLI binary (standalone, self-contained) |
| `hex-packer-cli-1.2.3-src.tar.gz` | Source code archive |

## Requirements

- Linux x86_64
- No Python required (binary is self-contained with all dependencies)

## Installation

```bash
# Extract (if needed)
tar -xzf hex-packer-cli-1.2.3-src.tar.gz

# Make binary executable
chmod +x bin/hex-packer-cli

# Run CLI mode
./bin/hex-packer-cli --cli --config config.csv --output firmware.hex
```

## Usage

### Binary (Pre-built)
```bash
# CLI mode (headless)
./bin/hex-packer-cli --cli --config config.csv --output firmware.hex

# Full pipeline with M0 and Register Integration
./bin/hex-packer-cli \
  --cli \
  --config "packer_config.csv" \
  --output "firmware.hex" \
  --m0_in "M0_firmware.hex" \
  --m0_out "M0_expanded.hex" \
  --reg_csv "integrator_config.csv" \
  --reg_base "0000" \
  --reg_out "all_registers.hex"
```

### Source Code (requires Python 3.x)
```bash
# Install dependencies
pip install pandas openpyxl

# Run CLI mode
python3 src/main.py --cli --config config.csv --output firmware.hex

# Run GUI mode
python3 src/main.py
```

## CLI Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli` | Yes | Enable CLI headless mode |
| `--config` | Yes (CLI) | Packer CSV config file |
| `--output` | No | Output HEX file (default: all_crc.hex) |
| `--m0_in` | No | M0 HEX input file |
| `--m0_out` | No | M0 HEX output file |
| `--reg_csv` | No | Integrator CSV config |
| `--reg_base` | No | Global Base Address (Hex, default: 0000) |
| `--reg_out` | No | Integrated Register HEX output |

## Verification

Verify checksums:
```bash
sha256sum -c bin/hex-packer-cli.sha256
sha256sum -c hex-packer-cli-1.2.3-src.tar.gz.sha256
```
