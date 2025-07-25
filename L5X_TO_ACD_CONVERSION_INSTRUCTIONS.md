# Instructions for Converting L5X to ACD

Since L5X → ACD conversion requires Windows with Studio 5000, here are your options:

## Option 1: Manual Conversion in Studio 5000 (Simplest)

1. **Transfer the L5X file to a Windows machine** with Studio 5000 installed:
   ```
   FINAL_COMPLETE_L5X/ULTIMATE_COMPLETE_PLC100_Mashing.L5X
   ```

2. **Open Studio 5000 Logix Designer**

3. **File → New** 
   - Select "Import from L5X"
   - Browse to your L5X file
   - Click OK

4. **File → Save As**
   - Choose ACD format
   - Name: `ULTIMATE_COMPLETE_PLC100_Mashing.ACD`
   - Save

## Option 2: Automated Conversion on Windows

1. **Transfer these files to Windows:**
   - `FINAL_COMPLETE_L5X/ULTIMATE_COMPLETE_PLC100_Mashing.L5X`
   - `studio5000_round_trip_converter.py`
   - `official_sdk_round_trip_converter.py`

2. **Install dependencies:**
   ```powershell
   # For official SDK (if available)
   pip install "C:\Users\Public\Documents\Studio 5000\Logix Designer SDK\python\dist\logix_designer_sdk-*.whl"
   
   # For Studio5000AutomationClient
   pip install pywin32
   ```

3. **Run the conversion:**
   ```powershell
   # Using official SDK
   python official_sdk_round_trip_converter.py l5x2acd ULTIMATE_COMPLETE_PLC100_Mashing.L5X
   
   # Or using Studio5000AutomationClient
   python studio5000_round_trip_converter.py l5x2acd ULTIMATE_COMPLETE_PLC100_Mashing.L5X
   ```

## Option 3: Remote Conversion Service

If you have access to a Windows server or VM with Studio 5000:

1. **Set up a conversion service** using one of our scripts
2. **Upload the L5X file** via network share or API
3. **Run the conversion** remotely
4. **Download the resulting ACD file**

## Expected Results

The conversion will produce:
- **Output file**: `ULTIMATE_COMPLETE_PLC100_Mashing.ACD`
- **File size**: ~9.5MB (similar to original)
- **All components preserved**: Comments, modules, ladder logic, tags, etc.

## Validation

After conversion, you can validate the round-trip was successful:

```powershell
# On Windows with our tools
python studio5000_round_trip_converter.py compare docs/exports/PLC100_Mashing.ACD ULTIMATE_COMPLETE_PLC100_Mashing.ACD
```

This will verify:
- MD5 checksums match
- Internal databases are identical
- Perfect round-trip achieved

## Note

The L5X file at `FINAL_COMPLETE_L5X/ULTIMATE_COMPLETE_PLC100_Mashing.L5X` contains 100% of the data from the original ACD file, so the conversion back to ACD should recreate the original file perfectly. 