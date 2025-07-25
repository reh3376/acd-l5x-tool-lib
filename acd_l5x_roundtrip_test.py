#!/usr/bin/env python3
"""
ACD ↔ L5X Round-Trip Conversion Test
This script tests the ability to convert ACD → L5X → ACD and verify identity
"""

import sys
import os
import hashlib
from pathlib import Path

def calculate_file_hash(filepath):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def test_round_trip_conversion():
    """Test round-trip conversion ACD → L5X → ACD"""
    
    # File paths
    original_acd = "/Users/reh3376/repos/acd-l5x-tool-lib/docs/acd-files/PLC100_Mashing.ACD"
    converted_l5x = "/Users/reh3376/repos/acd-l5x-tool-lib/docs/l5x-files/PLC100_Mashing.L5X"
    roundtrip_acd = "/Users/reh3376/repos/acd-l5x-tool-lib/docs/acd-files/PLC100_Mashing_roundtrip.ACD"
    
    print("🔄 Round-Trip Conversion Test: ACD → L5X → ACD")
    print("=" * 60)
    
    # Step 1: Get original ACD file info
    print("\n📄 Original ACD File:")
    print(f"   Path: {original_acd}")
    print(f"   Size: {os.path.getsize(original_acd) / 1024 / 1024:.2f} MB")
    original_hash = calculate_file_hash(original_acd)
    print(f"   MD5:  {original_hash}")
    
    # Step 2: Check existing L5X conversion
    print("\n📄 Converted L5X File:")
    if os.path.exists(converted_l5x):
        print(f"   Path: {converted_l5x}")
        print(f"   Size: {os.path.getsize(converted_l5x) / 1024:.2f} KB")
        print("   ✅ L5X file exists from previous conversion")
    else:
        print("   ❌ L5X file not found - conversion needed")
        return
    
    # Step 3: Attempt L5X → ACD conversion
    print("\n🔄 Attempting L5X → ACD Conversion...")
    print("   ⚠️  This requires Studio 5000 COM automation")
    
    # Check if plc-convert supports l5x2acd
    plc_convert = "/Users/reh3376/Library/Python/3.9/bin/plc-convert"
    
    import subprocess
    try:
        # Check available commands
        result = subprocess.run([plc_convert, "--help"], 
                              capture_output=True, text=True)
        
        if "l5x2acd" in result.stdout:
            print("   ✅ l5x2acd command is available")
            
            # Try the conversion
            print("   🔄 Running L5X to ACD conversion...")
            cmd = [plc_convert, "l5x2acd", converted_l5x, roundtrip_acd]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("   ✅ Conversion completed")
                
                # Compare files
                print("\n📊 Comparing Files:")
                roundtrip_hash = calculate_file_hash(roundtrip_acd)
                print(f"   Original MD5:  {original_hash}")
                print(f"   Roundtrip MD5: {roundtrip_hash}")
                
                if original_hash == roundtrip_hash:
                    print("   ✅ Files are IDENTICAL - Perfect round-trip!")
                else:
                    print("   ❌ Files are DIFFERENT - Round-trip failed")
                    
            else:
                print(f"   ❌ Conversion failed: {result.stderr}")
        else:
            print("   ❌ l5x2acd command not available")
            print("\n📋 Available commands:")
            for line in result.stdout.split('\n'):
                if "2" in line and ("acd" in line or "l5x" in line):
                    print(f"      {line.strip()}")
                    
    except Exception as e:
        print(f"   ❌ Error checking converter: {e}")
    
    # Step 4: Analysis
    print("\n📊 Round-Trip Conversion Analysis:")
    print("   1. ACD → L5X: Partial success (basic structure only)")
    print("   2. L5X → ACD: Not implemented without Studio 5000")
    print("   3. Perfect round-trip: Not currently possible")
    
    print("\n🔍 Technical Limitations:")
    print("   • ACD is a proprietary binary format")
    print("   • Full ACD parsing requires Rockwell tools")
    print("   • L5X → ACD requires Studio 5000 COM interface")
    print("   • Current L5X only contains basic structure, not full logic")

if __name__ == "__main__":
    test_round_trip_conversion() 