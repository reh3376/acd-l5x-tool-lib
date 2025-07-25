# Rockwell PLC File Conversion Options Summary

## Overview of Available Tools

| Option | Where it comes from | What you can do with it | Typical import name |
|--------|-------------------|------------------------|-------------------|
| **Logix Designer SDK (v2.01+)** | Installed with Studio 5000 (or as separate download under "Studio 5000 Logix Designer SDK"). Includes a signed **.whl** file plus examples. | Open/save ACD or L5X files, run comparisons, set comm paths, download to controllers, etc., all from Python 3.7-3.11. | `from logix_designer_sdk.logix_project import LogixProject` |
| **COM / .NET Automation** | Exposed by every Studio 5000 install; traditionally driven from VBA or C#, but Python can drive it via **pywin32** or **pythonnet**. | Full UI automation (invoke menu commands, click dialogs) plus file I/O. | `win32com.client.Dispatch("RA.LogixDesigner.Application")` |
| **pylogix / pycomm3** | Community libraries on GitHub / PyPI. | Communicate with a *running* PLC (EtherNet/IP), **not** for file conversion. | `from pylogix import PLC` |
| **hutcheb/acd** | Open-source Python library on GitHub | Parse ACD files, extract databases, export to L5X. Great for ACD → L5X conversion. | `from acd.api import ImportProjectFromFile` |
| **etl.studio5000_integration** | Part of the PLC-File-Conversion Library | Automates Studio 5000 via COM for L5X → ACD conversion | `from etl.studio5000_integration import Studio5000AutomationClient` |

## Official Rockwell SDK (Recommended)

The **Logix Designer SDK** is Rockwell's official Python interface for PLC file operations.

### Installation

```bash
# 1. Download from FactoryTalk Hub → Downloads → Studio 5000 → Utilities → "Logix Designer SDK"
# 2. Install with "Python client" option checked
# 3. Navigate to SDK directory
cd "%PUBLIC%\Documents\Studio 5000\Logix Designer SDK\python\Examples"

# 4. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 5. Install the wheel
pip install "..\dist\logix_designer_sdk-*.whl"
```

### Basic Usage Examples

#### L5X to ACD Conversion (Official SDK)

```python
import asyncio
from logix_designer_sdk.logix_project import LogixProject

async def l5x_to_acd(src_l5x: str, dst_acd: str):
    # Import L5X as project in memory
    proj = await LogixProject.import_l5x(src_l5x)
    # Save it back out as ACD file
    await proj.save_as(dst_acd)
    await proj.close()

asyncio.run(l5x_to_acd(r"C:\Projects\Foo.L5X", 
                       r"C:\Projects\Foo.ACD"))
```

#### ACD to L5X Conversion (Official SDK)

```python
async def acd_to_l5x(src_acd: str, dst_l5x: str):
    # Open existing ACD project
    proj = await LogixProject.open_logix_project(src_acd)
    # Export to L5X
    await proj.export_l5x(dst_l5x, 
                         encode_source=False,  # Keep readable
                         export_context=True)  # Include all
    await proj.close()

asyncio.run(acd_to_l5x(r"C:\Projects\Foo.ACD",
                       r"C:\Projects\Foo.L5X"))
```

## Alternative Methods

### 1. Studio5000AutomationClient (COM Automation)

Part of the etl.studio5000_integration module:

```python
from etl.studio5000_integration import Studio5000AutomationClient

client = Studio5000AutomationClient()
client.connect()
client.import_from_l5x("C:/JobFolder/Project.L5X",
                       target_acd_path="C:/JobFolder/Project.ACD")
client.disconnect()
```

### 2. hutcheb/acd (Open Source)

Best for ACD → L5X conversion and ACD file analysis:

```python
from acd.api import ImportProjectFromFile

# Convert ACD to L5X
proj = ImportProjectFromFile("project.ACD")
proj.write_to_l5x("project.L5X")
```

### 3. COM Automation via pywin32

Direct COM automation for full control:

```python
import win32com.client

# Create Studio 5000 application object
app = win32com.client.Dispatch("RSLogix5000.Application")

# Open L5X file
app.OpenProject(r"C:\Projects\MyProject.L5X")

# Save as ACD
app.SaveProjectAs(r"C:\Projects\MyProject.ACD")

# Close
app.Quit()
```

## Complete Round-Trip Solutions

We've created three comprehensive round-trip converters:

### 1. Official SDK Converter (`official_sdk_round_trip_converter.py`)
- Uses Logix Designer SDK for both directions
- Most reliable and official method
- Requires SDK installation

### 2. Hybrid Converter (`studio5000_round_trip_converter.py`)
- Uses hutcheb/acd for ACD → L5X
- Uses Studio5000AutomationClient for L5X → ACD
- Good balance of features

### 3. Advanced Prototype (`l5x_to_acd_advanced.py`)
- Research prototype for binary reconstruction
- Not production-ready but educational

## Feature Comparison

| Feature | Official SDK | COM Automation | hutcheb/acd | Our Converters |
|---------|-------------|----------------|-------------|----------------|
| ACD → L5X | ✅ | ✅ | ✅ | ✅ |
| L5X → ACD | ✅ | ✅ | ❌ | ✅ |
| Python Support | ✅ Native | ✅ via pywin32 | ✅ Native | ✅ |
| Async Support | ✅ | ❌ | ❌ | ✅ |
| Comment Extraction | ✅ | ✅ | ✅ Enhanced | ✅ |
| Batch Processing | ✅ | ✅ | ✅ | ✅ |
| Cross-Platform | ❌ Windows | ❌ Windows | ✅ | ❌ Windows |
| License Required | ✅ Studio 5000 | ✅ Studio 5000 | ❌ | ✅ Studio 5000 |

## Recommendations by Use Case

### For Production Use:
1. **Official SDK** (`logix_designer_sdk`) - Most reliable
2. **Studio5000AutomationClient** - Good automation
3. **Our round-trip converters** - Complete solution

### For Development/Analysis:
1. **hutcheb/acd** - Best for understanding ACD structure
2. **Our advanced prototypes** - Learning binary formats

### For Automation/CI-CD:
1. **Official SDK with async** - Best performance
2. **Our batch converters** - Ready-made solutions

### For Cross-Platform:
1. **hutcheb/acd** - Only option for ACD → L5X on Linux/Mac
2. **L5X → ACD requires Windows and Studio 5000**

## Quick Start Commands

```bash
# Using our converters
python official_sdk_round_trip_converter.py roundtrip MyProject.ACD
python studio5000_round_trip_converter.py acd2l5x MyProject.ACD
python studio5000_round_trip_converter.py l5x2acd MyProject.L5X

# Batch conversion
python official_sdk_round_trip_converter.py batch C:/ACDFiles C:/L5XOutput
```

## Bottom Line

- **Official SDK** is the gold standard for both conversions
- **hutcheb/acd** excels at ACD analysis and extraction
- **Our converters** provide complete, tested solutions
- All L5X → ACD methods require Windows and Studio 5000
- Round-trip conversion is now 100% automated!

---
*This guide covers all available options for Rockwell PLC file conversion* 