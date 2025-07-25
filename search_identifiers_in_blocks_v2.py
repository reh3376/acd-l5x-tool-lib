#!/usr/bin/env python3
"""
Search for L5X identifiers in extracted ACD blocks - Version 2
Uses actual program names from L5X exports
"""

import os
import json
from pathlib import Path

def search_identifiers_in_blocks_v2(blocks_dir):
    """Search for identifiers in extracted blocks"""
    
    # List of actual program names from L5X exports
    program_names = [
        "Main",
        "Milling_PID_Logic",
        "DropTub_PID_Logic", 
        "GrainLoadin_Device_Logic",
        "DropTub_Device_Config",
        "MashCooler_Device_Config",
        "Milling_Device_Config",
        "MashWater_AutoLogic",
        "MashWater_PID_Logic",
        "SafetyProgram",
        "MashCooler_Device_Logic",
        "MashWater_Device_Logic",
        "DropTub_Device_Logic",
        "DropTub_AutoLogic",
        "Mashing01_FBD01",
        "GrainLoadin_PID_Logic",
        "MashWater_DeviceLogic",
        "Milling_AutoLogic",
        "Master_Main",
        "Cookers_Device_Logic",
        "Cooker_2_AutoLogic",
        "Receiving_AutoLogic",
        "Receiving_DeviceLogic",
        "Milling_DeviceLogic",
        "Cooker_2_DeviceLogic",
        "GrainLoadin_Device_Config",
        "Cooker_1_DeviceLogic",
        "Cookers_Device_Config",
        "Cookers_PID_Logic",
        "MashWater_Device_Config",
        "MashCooler_PID_Logic",
        "MashCooler_DeviceLogic",
        "Milling_Device_Logic",
        "Cooker_DeviceLogic",
        "DropTub_DeviceLogic",
        "MashCooler_AutoLogic",
        "Cooker_AutoLogic",
        "Cooker_1_AutoLogic"
    ]
    
    # Also search for common module prefixes
    module_prefixes = [
        "ENET_ECP",
        "DI_ECP",
        "DO_ECP", 
        "AI_ECP",
        "AO_ECP",
        "FAN_",
        "CONV_",
        "PMP_",
        "AGI_",
        "FIT_",
        "WIT_",
        "MIL_",
        "XFV_",
        "PLC100_",
        "PLC200_",
        "PLC300_",
        "PLC400_"
    ]
    
    # Controller name
    controller_names = ["PLC100_Mashing"]
    
    # Combine all identifiers
    all_identifiers = set(program_names + module_prefixes + controller_names)
    
    print(f"🔍 Searching for {len(all_identifiers)} identifiers in blocks...")
    
    results = {}
    
    # Search each block
    for block_file in Path(blocks_dir).glob("*.bin"):
        print(f"\n📦 Searching in {block_file.name}...")
        
        with open(block_file, 'rb') as f:
            block_data = f.read()
        
        block_results = {}
        
        # Search for each identifier
        for identifier in sorted(all_identifiers):
            # Try different encodings
            encodings_to_try = [
                ('utf-8', identifier.encode('utf-8')),
                ('utf-16le', identifier.encode('utf-16le')),
                ('ascii', identifier.encode('ascii') if identifier.isascii() else None)
            ]
            
            for encoding_name, search_bytes in encodings_to_try:
                if search_bytes and search_bytes in block_data:
                    count = block_data.count(search_bytes)
                    if identifier not in block_results or count > block_results[identifier]['count']:
                        block_results[identifier] = {
                            'encoding': encoding_name,
                            'count': count
                        }
                    print(f"  ✅ Found '{identifier}' in {encoding_name} ({count} times)")
        
        if block_results:
            results[block_file.name] = block_results
    
    # Save results
    output_file = Path("identifier_search_results_v2.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Summary
    total_found = sum(len(block_results) for block_results in results.values())
    print(f"\n📊 Summary: Found {total_found} unique identifiers across {len(results)} blocks")
    
    # Show which identifiers were found
    found_identifiers = set()
    for block_results in results.values():
        found_identifiers.update(block_results.keys())
    
    print(f"\n🎯 Found identifiers: {sorted(found_identifiers)}")

def main():
    blocks_dir = "extracted_blocks"
    search_identifiers_in_blocks_v2(blocks_dir)

if __name__ == "__main__":
    main() 