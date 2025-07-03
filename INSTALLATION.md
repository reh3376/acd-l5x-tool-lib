# Installation Guide

## Installing from PyPI (Recommended)

Once the package is published to PyPI, you can install it using pip:

```bash
pip install plc-format-converter
```

### Install with All Features

To install with all optional dependencies (recommended for full functionality):

```bash
pip install plc-format-converter[all]
```

### Install for Development

To install in development mode with all development dependencies:

```bash
pip install plc-format-converter[dev,all]
```

## Installing from GitHub

You can also install directly from the GitHub repository:

```bash
pip install git+https://github.com/reh3376/acd-l5x-tool-lib.git
```

## Command Line Tools

After installation, the following command-line tools will be available:

- `acd2l5x` - Convert ACD files to L5X format
- `l5x2acd` - Convert L5X files to ACD format  
- `plc-convert` - Universal PLC file converter

### Example Usage

```bash
# Convert ACD to L5X
acd2l5x input.ACD output.L5X

# Convert L5X to ACD
l5x2acd input.L5X output.ACD

# Universal converter (auto-detects format)
plc-convert input.ACD output.L5X
```

## Python API Usage

```python
from plc_format_converter import convert_acd_to_l5x, convert_l5x_to_acd

# Convert ACD to L5X
convert_acd_to_l5x('input.ACD', 'output.L5X')

# Convert L5X to ACD
convert_l5x_to_acd('input.L5X', 'output.ACD')
```

## Requirements

- Python 3.8 or higher
- Windows (for Studio 5000 integration features)
- Studio 5000 Logix Designer (for ACD file operations)

## Troubleshooting

### Studio 5000 Not Found

If you get errors about Studio 5000 not being found:

1. Ensure Studio 5000 Logix Designer is installed
2. Run the installation verification:
   ```bash
   python -c "from plc_format_converter import verify_studio5000; verify_studio5000()"
   ```

### Permission Errors

If you encounter permission errors on Windows:

1. Run your command prompt or terminal as Administrator
2. Ensure Studio 5000 is not running when performing conversions

### Import Errors

If you get import errors:

1. Ensure you've installed with all dependencies:
   ```bash
   pip install plc-format-converter[all]
   ```

2. Check your Python version:
   ```bash
   python --version
   ```
   (Must be 3.8 or higher)

## Support

For issues and support:

1. Check the [GitHub Issues](https://github.com/reh3376/acd-l5x-tool-lib/issues)
2. Review the [Documentation](https://github.com/reh3376/acd-l5x-tool-lib)
3. Submit a new issue with details about your environment and the error

## License

This project is licensed under the MIT License - see the LICENSE file for details. 