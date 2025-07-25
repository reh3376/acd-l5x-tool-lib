#!/usr/bin/env python3
"""
ACD Reverse Engineering Toolkit
Tools for analyzing and understanding the ACD binary format
"""

import os
import sys
import gzip
import struct
import hashlib
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

class ACDAnalyzer:
    """Comprehensive ACD file analyzer for reverse engineering"""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data = None
        self.header_text = ""
        self.binary_offset = 0
        self.gzip_blocks = []
        
    def load(self):
        """Load ACD file and identify structure"""
        with open(self.filepath, 'rb') as f:
            self.data = f.read()
        
        # Find text header end
        header_end = self.data.find(b'\x00\x00\x00\x00\x00')
        if header_end > 0:
            self.header_text = self.data[:header_end].decode('utf-8', errors='ignore')
            self.binary_offset = header_end
        
        print(f"📁 Loaded: {self.filepath.name}")
        print(f"📏 Size: {len(self.data):,} bytes")
        print(f"📄 Text header: {len(self.header_text):,} bytes")
        print(f"🔢 Binary starts at: 0x{self.binary_offset:X}")
        
    def find_gzip_blocks(self):
        """Find all GZIP compressed blocks"""
        self.gzip_blocks = []
        offset = self.binary_offset
        
        while offset < len(self.data):
            # Look for GZIP magic bytes (1F 8B)
            pos = self.data.find(b'\x1F\x8B', offset)
            if pos == -1:
                break
            
            print(f"🔍 Found GZIP header at 0x{pos:X}")
            
            # Try to decompress to verify it's valid GZIP
            # For large blocks, we need to be smarter about finding the end
            found = False
            
            # Try common block sizes first
            test_sizes = [1000, 10000, 100000, 1000000, 10000000, 20000000]
            
            for test_size in test_sizes:
                if pos + test_size > len(self.data):
                    test_size = len(self.data) - pos
                
                try:
                    # Try to decompress
                    test_data = self.data[pos:pos + test_size]
                    decompressed = gzip.decompress(test_data)
                    
                    # If successful, we found a valid GZIP block
                    self.gzip_blocks.append({
                        'index': len(self.gzip_blocks),
                        'offset': pos,
                        'compressed_size': test_size,
                        'decompressed_size': len(decompressed),
                        'data': decompressed[:1000]  # Store only first 1KB for analysis
                    })
                    print(f"✅ Block {len(self.gzip_blocks)-1}: offset=0x{pos:X}, "
                          f"compressed={test_size:,}, decompressed={len(decompressed):,}")
                    offset = pos + test_size
                    found = True
                    break
                except gzip.BadGzipFile:
                    continue
                except Exception as e:
                    continue
            
            if not found:
                # Try to find exact size by looking for the end marker
                # GZIP ends with CRC32 (4 bytes) + uncompressed size (4 bytes)
                try:
                    # Read GZIP header to get more info
                    header = self.data[pos:pos+10]
                    if len(header) >= 10:
                        flags = header[3]
                        # Skip past header and any extra fields
                        current = pos + 10
                        
                        # Try progressively larger chunks
                        for chunk_size in range(100, min(20000000, len(self.data) - pos), 10000):
                            try:
                                test_data = self.data[pos:pos + chunk_size]
                                decompressed = gzip.decompress(test_data)
                                
                                self.gzip_blocks.append({
                                    'index': len(self.gzip_blocks),
                                    'offset': pos,
                                    'compressed_size': chunk_size,
                                    'decompressed_size': len(decompressed),
                                    'data': decompressed[:1000]
                                })
                                print(f"✅ Block {len(self.gzip_blocks)-1}: offset=0x{pos:X}, "
                                      f"compressed={chunk_size:,}, decompressed={len(decompressed):,}")
                                offset = pos + chunk_size
                                found = True
                                break
                            except:
                                continue
                except:
                    pass
            
            if not found:
                print(f"⚠️  Could not determine size of GZIP block at 0x{pos:X}")
                offset = pos + 2
        
        print(f"\n📊 Found {len(self.gzip_blocks)} GZIP blocks total")
        return self.gzip_blocks
    
    def analyze_block_contents(self, block_index: int):
        """Analyze contents of a specific GZIP block"""
        if block_index >= len(self.gzip_blocks):
            print(f"❌ Block {block_index} not found")
            return
        
        block = self.gzip_blocks[block_index]
        data = block['data']
        
        print(f"\n📦 Analyzing Block {block_index}:")
        print(f"   Offset: 0x{block['offset']:X}")
        print(f"   Compressed: {block['compressed_size']:,} bytes")
        print(f"   Decompressed: {block['decompressed_size']:,} bytes")
        
        # Show first 256 bytes in hex and ASCII
        print("\n🔍 First 256 bytes:")
        for i in range(0, min(256, len(data)), 16):
            hex_part = ' '.join(f'{b:02X}' for b in data[i:i+16])
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"   {i:04X}: {hex_part:<48} |{ascii_part}|")
        
        # Look for strings
        print("\n📝 Readable strings found:")
        strings = self.extract_strings(data, min_length=4)
        for s in strings[:20]:  # Show first 20
            print(f"   - {s}")
        
        # Look for common patterns
        self.find_patterns(data)
    
    def extract_strings(self, data: bytes, min_length: int = 4) -> List[str]:
        """Extract readable strings from binary data"""
        strings = []
        current = []
        
        for byte in data:
            if 32 <= byte < 127:  # Printable ASCII
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    strings.append(''.join(current))
                current = []
        
        if len(current) >= min_length:
            strings.append(''.join(current))
        
        return strings
    
    def find_patterns(self, data: bytes):
        """Find common patterns in binary data"""
        print("\n🔎 Pattern Analysis:")
        
        # Check for database markers
        if b'Comps\x00' in data:
            print("   ✓ Found 'Comps' database marker")
        if b'.dat' in data:
            print("   ✓ Found '.dat' section marker")
        if b'.idx' in data:
            print("   ✓ Found '.idx' section marker")
        
        # Check for length-prefixed strings (2-byte length)
        count = 0
        for i in range(0, len(data) - 2):
            length = struct.unpack('<H', data[i:i+2])[0]
            if 1 <= length <= 100 and i + 2 + length <= len(data):
                try:
                    string = data[i+2:i+2+length].decode('utf-8')
                    if all(32 <= ord(c) < 127 for c in string):
                        count += 1
                except:
                    pass
        print(f"   ✓ Found {count} potential length-prefixed strings")
    
    def compare_files(self, other_file: str):
        """Compare two ACD files to find differences"""
        other = ACDAnalyzer(other_file)
        other.load()
        other.find_gzip_blocks()
        
        print(f"\n🔄 Comparing files:")
        print(f"   File 1: {self.filepath.name} ({len(self.data):,} bytes)")
        print(f"   File 2: {other.filepath.name} ({len(other.data):,} bytes)")
        
        # Compare GZIP blocks
        print(f"\n📦 GZIP Block Comparison:")
        print(f"   File 1: {len(self.gzip_blocks)} blocks")
        print(f"   File 2: {len(other.gzip_blocks)} blocks")
        
        # Compare each block
        for i in range(max(len(self.gzip_blocks), len(other.gzip_blocks))):
            if i < len(self.gzip_blocks) and i < len(other.gzip_blocks):
                b1 = self.gzip_blocks[i]
                b2 = other.gzip_blocks[i]
                
                if b1['decompressed_size'] != b2['decompressed_size']:
                    print(f"\n   Block {i} size changed:")
                    print(f"      File 1: {b1['decompressed_size']:,} bytes")
                    print(f"      File 2: {b2['decompressed_size']:,} bytes")
                    print(f"      Difference: {b2['decompressed_size'] - b1['decompressed_size']:+,} bytes")
                    
                    # Show what changed
                    self.show_block_diff(b1['data'], b2['data'], i)
    
    def show_block_diff(self, data1: bytes, data2: bytes, block_index: int):
        """Show differences between two data blocks"""
        print(f"\n   🔍 Analyzing changes in Block {block_index}:")
        
        # Find first difference
        for i in range(min(len(data1), len(data2))):
            if data1[i] != data2[i]:
                print(f"      First difference at offset 0x{i:X}")
                
                # Show context around difference
                start = max(0, i - 16)
                end = min(len(data1), len(data2), i + 16)
                
                print(f"      File 1: {' '.join(f'{b:02X}' for b in data1[start:end])}")
                print(f"      File 2: {' '.join(f'{b:02X}' for b in data2[start:end])}")
                break
        
        # Extract strings from both to see what changed
        strings1 = set(self.extract_strings(data1))
        strings2 = set(self.extract_strings(data2))
        
        new_strings = strings2 - strings1
        if new_strings:
            print(f"\n      New strings in File 2:")
            for s in list(new_strings)[:10]:
                print(f"         + {s}")


def main():
    """Interactive ACD analysis tool"""
    print("🔬 ACD Reverse Engineering Toolkit")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python acd_reverse_engineering_toolkit.py <acd_file> [compare_file]")
        sys.exit(1)
    
    # Load and analyze first file
    analyzer = ACDAnalyzer(sys.argv[1])
    analyzer.load()
    analyzer.find_gzip_blocks()
    
    # If second file provided, compare them
    if len(sys.argv) > 2:
        analyzer.compare_files(sys.argv[2])
    else:
        # Interactive analysis
        while True:
            print("\n📋 Options:")
            print("   1. Analyze specific block")
            print("   2. Export all blocks")
            print("   3. Search for pattern")
            print("   4. Compare with another file")
            print("   5. Exit")
            
            choice = input("\nSelect option: ")
            
            if choice == '1':
                block_num = int(input("Block number: "))
                analyzer.analyze_block_contents(block_num)
            elif choice == '2':
                # Export all blocks
                export_dir = Path("extracted_blocks")
                export_dir.mkdir(exist_ok=True)
                for block in analyzer.gzip_blocks:
                    filename = export_dir / f"block_{block['index']:02d}.bin"
                    with open(filename, 'wb') as f:
                        f.write(block['data'])
                print(f"✅ Exported {len(analyzer.gzip_blocks)} blocks to {export_dir}")
            elif choice == '3':
                pattern = input("Enter pattern (text): ")
                for i, block in enumerate(analyzer.gzip_blocks):
                    if pattern.encode() in block['data']:
                        print(f"✓ Found in block {i}")
            elif choice == '4':
                other_file = input("Path to second ACD file: ")
                analyzer.compare_files(other_file)
            elif choice == '5':
                break

if __name__ == "__main__":
    main() 