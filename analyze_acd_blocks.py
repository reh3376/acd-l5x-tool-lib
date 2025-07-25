#!/usr/bin/env python3
"""
Analyze extracted ACD blocks to understand their structure
"""

import os
import struct
from pathlib import Path
import string

def read_pascal_string(data, offset):
    """Read a Pascal-style string (length-prefixed)"""
    if offset >= len(data):
        return None, offset
    
    length = data[offset]
    if offset + 1 + length > len(data):
        return None, offset
    
    try:
        text = data[offset + 1:offset + 1 + length].decode('utf-8', errors='ignore')
        return text, offset + 1 + length
    except:
        return None, offset + 1

def read_uint16_string(data, offset):
    """Read a string with 2-byte length prefix"""
    if offset + 2 > len(data):
        return None, offset
    
    length = struct.unpack('<H', data[offset:offset+2])[0]
    if offset + 2 + length > len(data):
        return None, offset
    
    try:
        text = data[offset + 2:offset + 2 + length].decode('utf-8', errors='ignore')
        return text, offset + 2 + length
    except:
        return None, offset + 2

def find_strings(data, min_length=4):
    """Find all printable strings in binary data"""
    strings = []
    current = []
    offset = 0
    
    for i, byte in enumerate(data):
        if chr(byte) in string.printable and byte not in [0, 10, 13]:  # Exclude null, LF, CR
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                strings.append((''.join(current), offset))
            current = []
            offset = i + 1
    
    if len(current) >= min_length:
        strings.append((''.join(current), offset))
    
    return strings

def analyze_block(filepath):
    """Analyze a single block file"""
    print(f"\n{'=' * 60}")
    print(f"📦 Analyzing: {filepath.name}")
    print(f"{'=' * 60}")
    
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"Size: {len(data):,} bytes")
    
    # Show first 256 bytes in hex
    print("\n🔍 First 256 bytes:")
    for i in range(0, min(256, len(data)), 16):
        hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {i:04X}: {hex_part:<48} |{ascii_part}|")
    
    # Look for specific patterns
    print("\n🔎 Pattern Analysis:")
    
    # Check for database headers
    if b'Comps\x00' in data:
        pos = data.find(b'Comps\x00')
        print(f"  ✓ Found 'Comps' database at offset 0x{pos:X}")
        
        # Try to parse Comps structure
        print("\n  📊 Comps Database Structure:")
        offset = pos + 6  # Skip 'Comps\0'
        
        # Look for .dat and .idx sections
        dat_pos = data.find(b'.dat', offset)
        idx_pos = data.find(b'.idx', offset)
        
        if dat_pos != -1:
            print(f"    - .dat section at 0x{dat_pos:X}")
        if idx_pos != -1:
            print(f"    - .idx section at 0x{idx_pos:X}")
    
    # Look for component types
    component_types = [
        b'Controller', b'DataType', b'Program', b'Routine', 
        b'Tag', b'Module', b'AddOnInstructionDefinition',
        b'Task', b'Trend', b'Alarm'
    ]
    
    print("\n  🏗️ Component Types Found:")
    for comp_type in component_types:
        count = data.count(comp_type)
        if count > 0:
            print(f"    - {comp_type.decode()}: {count} occurrences")
            # Find first occurrence
            pos = data.find(comp_type)
            print(f"      First at: 0x{pos:X}")
    
    # Extract readable strings
    print("\n  📝 Notable Strings:")
    strings = find_strings(data, min_length=8)
    
    # Group strings by type
    plc_names = []
    data_types = []
    instructions = []
    other = []
    
    for text, offset in strings[:200]:  # First 200 strings
        if any(keyword in text.lower() for keyword in ['plc', 'mash', 'brew', 'tank', 'valve', 'pump']):
            plc_names.append((text, offset))
        elif any(keyword in text.upper() for keyword in ['BOOL', 'DINT', 'REAL', 'STRING', 'TIMER']):
            data_types.append((text, offset))
        elif any(keyword in text.upper() for keyword in ['ADD', 'SUB', 'MOV', 'TON', 'CTU', 'OTE', 'XIC']):
            instructions.append((text, offset))
        else:
            other.append((text, offset))
    
    # Show categorized strings
    if plc_names:
        print("\n    🏭 PLC-related names:")
        for text, offset in plc_names[:10]:
            print(f"      0x{offset:06X}: {text}")
    
    if data_types:
        print("\n    📊 Data types:")
        for text, offset in data_types[:10]:
            print(f"      0x{offset:06X}: {text}")
    
    if instructions:
        print("\n    🔧 Instructions:")
        for text, offset in instructions[:10]:
            print(f"      0x{offset:06X}: {text}")
    
    # Look for binary structures
    print("\n  🔢 Binary Structure Analysis:")
    
    # Look for common integer patterns (like array sizes, counts)
    for i in range(0, len(data) - 4, 4):
        value = struct.unpack('<I', data[i:i+4])[0]
        if value in [1, 2, 3, 4, 5, 10, 16, 32, 64, 100, 256, 1000]:
            print(f"    - Found common value {value} at 0x{i:X}")
            if i < 100:  # Only for early occurrences
                break

def main():
    """Analyze all extracted blocks"""
    blocks_dir = Path("extracted_blocks")
    
    if not blocks_dir.exists():
        print("❌ No extracted_blocks directory found!")
        return
    
    print("🔬 ACD Block Analysis Tool")
    print("=" * 60)
    
    # Get all block files
    block_files = sorted(blocks_dir.glob("block_*.bin"))
    
    print(f"Found {len(block_files)} blocks to analyze")
    
    # Analyze each block
    for block_file in block_files:
        analyze_block(block_file)
        
        # Ask if user wants to continue
        response = input("\nPress Enter to continue to next block, or 'q' to quit: ")
        if response.lower() == 'q':
            break
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main() 