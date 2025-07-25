# Complete L5X to ACD Conversion Guide

## Overview

There are three official methods to convert L5X files to ACD format, each suited for different use cases:

1. **Open-as-New-Project** - Best for converting entire controller exports
2. **Import Components** - Best for merging L5X components into existing projects
3. **Scripted/Batch Conversion** - Best for automation and multiple files

## Method 1: Open-as-New-Project (Quickest for Full Controllers)

This is the simplest method when your L5X represents a complete controller configuration.

### Steps:

1. **Start Studio 5000 Logix Designer**
   - Use same or newer major revision than the L5X was exported from

2. **Create New Project from L5X**
   - `File → New Project...`
   - Choose "Import Logix Designer XML file (.L5X)"
   - (Older versions show a radio button labeled "Import")

3. **Import Wizard**
   - Browse to your .L5X file
   - Pick the controller family & firmware revision Studio suggests
   - Step through the wizard

4. **Save as ACD**
   - When project opens, it exists only in RAM
   - `File → Save` or `Save As`
   - Give it a name
   - Studio writes to disk as an *.ACD file

**Result**: A fresh ACD that is byte-for-byte equivalent to what you would have had if the project had never been exported.

## Method 2: Import Components (For Merging into Existing Projects)

Use this when you need to merge L5X components into an existing ACD project.

### Steps:

1. **Open Destination Project**
   - Open (or create) the destination .ACD file

2. **Import Components**
   - **Option A**: Right-click Controller in Controller Organizer → Import Component
   - **Option B**: Tools → Import Component Data

3. **Select L5X File**
   - Point to the .L5X file
   - Studio walks through name-matching wizard
   - Choose to keep or overwrite existing tags, routines, etc.

4. **Save Project**
   - Save the project
   - Original ACD plus imported logic now lives in one file

### Component Types You Can Import:
- Routines
- Programs
- User-Defined Data Types (UDTs)
- Add-On Instructions (AOIs)
- Tags
- Module configurations

## Method 3: Scripted/Batch Conversion (Automation)

Perfect for converting multiple files or integrating into CI/CD pipelines.

### Basic Script:

```python
from etl.studio5000_integration import Studio5000AutomationClient

client = Studio5000AutomationClient()
client.connect()
client.import_from_l5x("C:/JobFolder/Project.L5X",
                       target_acd_path="C:/JobFolder/Project.ACD")
client.disconnect()
```

### Advanced Batch Conversion:

```python
import os
from pathlib import Path
from etl.studio5000_integration import Studio5000AutomationClient

def batch_convert_directory(input_dir, output_dir):
    """
    Convert all L5X files in a directory to ACD format
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    client = Studio5000AutomationClient()
    client.connect()
    
    success_count = 0
    failed_files = []
    
    try:
        for l5x_file in input_path.glob("*.L5X"):
            acd_file = output_path / f"{l5x_file.stem}.ACD"
            
            try:
                print(f"Converting {l5x_file.name}...")
                client.import_from_l5x(
                    str(l5x_file.absolute()),
                    target_acd_path=str(acd_file.absolute())
                )
                print(f"  ✅ Saved as {acd_file.name}")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                failed_files.append((l5x_file.name, str(e)))
                
    finally:
        client.disconnect()
        
    # Report results
    print(f"\n📊 Conversion Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(failed_files)}")
    
    if failed_files:
        print("\n❌ Failed conversions:")
        for filename, error in failed_files:
            print(f"  - {filename}: {error}")
    
    return success_count, failed_files

# Example usage
batch_convert_directory("C:/L5X_Files", "C:/ACD_Output")
```

### Round-Trip Verification:

```python
from studio5000_round_trip_converter import RoundTripConverter

converter = RoundTripConverter()

# Test round-trip conversion
success = converter.round_trip_test("original.ACD")

if success:
    print("✅ Round-trip conversion successful - files are identical!")
else:
    print("⚠️  Round-trip conversion resulted in differences")
```

## Common Issues and Solutions

| Issue | What to Do |
|-------|------------|
| **Firmware mismatch** | The controller revision you pick in the wizard must be ≥ the revision stored in the L5X |
| **Unsupported modules** | If the PC doesn't have the EDS/AOP installed, Studio will import tags but leave module as "<Unknown Module>". Install the profile, then Change Module |
| **Add-On Instructions from newer releases** | Import succeeds, but AOI source may be locked. Open in matching or newer Studio version to unlock/edit |
| **Source-protected content** | Protection flags survive export/import. You'll still need the key or source-code rights |

## Best Practices

### For Single File Conversion:
1. Use **Open-as-New-Project** for complete controllers
2. Use **Import Components** for partial imports
3. Always verify firmware compatibility

### For Multiple Files:
1. Use **Scripted/Batch Conversion**
2. Implement error handling and logging
3. Test with a small subset first
4. Keep original L5X files as backup

### For Production Use:
1. Validate conversions with round-trip testing
2. Document firmware versions used
3. Maintain audit trail of conversions
4. Handle licensing requirements

## Quick Decision Tree

```
Do you need to convert the entire controller?
├─ YES → Use Open-as-New-Project
└─ NO
   │
   └─ Do you need to merge into existing project?
      ├─ YES → Use Import Components
      └─ NO
         │
         └─ Do you have multiple files or need automation?
            ├─ YES → Use Scripted/Batch Conversion
            └─ NO → Use Open-as-New-Project
```

## Complete Round-Trip Solution

Our project provides a complete round-trip converter that combines:
- **hutcheb/acd** for ACD → L5X conversion
- **Studio5000AutomationClient** for L5X → ACD conversion

```python
from studio5000_round_trip_converter import RoundTripConverter

converter = RoundTripConverter()

# Convert ACD to L5X
l5x_file = converter.acd_to_l5x("project.ACD")

# Convert L5X to ACD
acd_file = converter.l5x_to_acd("project.L5X")

# Full round-trip test with validation
success = converter.round_trip_test("original.ACD")
```

## Bottom Line

- **For straight-up conversion**: Open the L5X as a new project and press Save - you've got an ACD
- **For automation**: Use the COM-automation/batch-conversion script with Studio5000AutomationClient
- **For round-trip verification**: Use our complete converter to ensure perfect fidelity

---
*This guide covers all official Rockwell methods for L5X to ACD conversion* 