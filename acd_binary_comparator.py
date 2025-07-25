#!/usr/bin/env python3
"""
ACD Binary Comparator - Compare two ACD files to understand format changes
"""

import sys
import gzip
from pathlib import Path
import struct
import difflib

class ACDBinaryComparator:
    """Compare two ACD files at the binary level"""
    
    def __init__(self, file1: str, file2: str):
        self.file1_path = Path(file1)
        self.file2_path = Path(file2)
        self.file1_data = None
        self.file2_data = None
        self.file1_blocks = []
        self.file2_blocks = []
    
    def load_files(self):
        """Load both ACD files"""
        print(f"📁 Loading files:")
        print(f"   File 1: {self.file1_path.name}")
        print(f"   File 2: {self.file2_path.name}")
        
        with open(self.file1_path, 'rb') as f:
            self.file1_data = f.read()
        
        with open(self.file2_path, 'rb') as f:
            self.file2_data = f.read()
        
        print(f"\n📏 File sizes:")
        print(f"   File 1: {len(self.file1_data):,} bytes")
        print(f"   File 2: {len(self.file2_data):,} bytes")
        print(f"   Difference: {len(self.file2_data) - len(self.file1_data):+,} bytes")
    
    def extract_gzip_blocks(self, data: bytes) -> list:
        """Extract all GZIP blocks from data"""
        blocks = []
        offset = 0
        
        while offset < len(data):
            pos = data.find(b'\x1F\x8B', offset)
            if pos == -1:
                break
            
            # Try to decompress with various sizes
            for size in [1000, 10000, 100000, 1000000, 10000000]:
                if pos + size > len(data):
                    size = len(data) - pos
                
                try:
                    decompressed = gzip.decompress(data[pos:pos + size])
                    blocks.append({
                        'offset': pos,
                        'compressed_size': size,
                        'decompressed_size': len(decompressed),
                        'data': decompressed
                    })
                    offset = pos + size
                    break
                except:
                    continue
            else:
                offset = pos + 2
        
        return blocks
    
    def compare_headers(self):
        """Compare file headers (text portion)"""
        print("\n📄 Comparing Headers:")
        
        # Find end of text headers
        header1_end = self.file1_data.find(b'\x00\x00\x00\x00\x00')
        header2_end = self.file2_data.find(b'\x00\x00\x00\x00\x00')
        
        if header1_end > 0 and header2_end > 0:
            header1 = self.file1_data[:header1_end].decode('utf-8', errors='ignore')
            header2 = self.file2_data[:header2_end].decode('utf-8', errors='ignore')
            
            # Show differences
            differ = difflib.unified_diff(
                header1.splitlines(), 
                header2.splitlines(),
                fromfile='File1',
                tofile='File2',
                lineterm=''
            )
            
            changes = list(differ)
            if changes:
                print("   Header differences found:")
                for line in changes[:20]:  # Show first 20 lines
                    if line.startswith('+') and not line.startswith('+++'):
                        print(f"   + {line[1:]}")
                    elif line.startswith('-') and not line.startswith('---'):
                        print(f"   - {line[1:]}")
            else:
                print("   Headers are identical")
    
    def compare_blocks(self):
        """Compare GZIP blocks between files"""
        print("\n📦 Extracting and comparing GZIP blocks:")
        
        self.file1_blocks = self.extract_gzip_blocks(self.file1_data)
        self.file2_blocks = self.extract_gzip_blocks(self.file2_data)
        
        print(f"\n   File 1: {len(self.file1_blocks)} blocks")
        print(f"   File 2: {len(self.file2_blocks)} blocks")
        
        # Compare each block
        for i in range(max(len(self.file1_blocks), len(self.file2_blocks))):
            if i < len(self.file1_blocks) and i < len(self.file2_blocks):
                b1 = self.file1_blocks[i]
                b2 = self.file2_blocks[i]
                
                print(f"\n   Block {i}:")
                print(f"      File 1: {b1['decompressed_size']:,} bytes")
                print(f"      File 2: {b2['decompressed_size']:,} bytes")
                
                if b1['data'] != b2['data']:
                    print(f"      ⚠️  Block contents differ!")
                    self.analyze_block_differences(b1['data'], b2['data'], i)
                else:
                    print(f"      ✅ Blocks are identical")
    
    def analyze_block_differences(self, data1: bytes, data2: bytes, block_num: int):
        """Analyze differences within a block"""
        print(f"\n🔍 Analyzing differences in Block {block_num}:")
        
        # Find first difference
        first_diff = -1
        for i in range(min(len(data1), len(data2))):
            if data1[i] != data2[i]:
                first_diff = i
                break
        
        if first_diff >= 0:
            print(f"   First difference at offset 0x{first_diff:X}")
            
            # Show context
            start = max(0, first_diff - 32)
            end = min(len(data1), len(data2), first_diff + 32)
            
            print(f"\n   Context around first difference:")
            print(f"   File 1: {self.format_hex(data1[start:end], first_diff - start)}")
            print(f"   File 2: {self.format_hex(data2[start:end], first_diff - start)}")
        
        # Look for added strings
        self.find_new_strings(data1, data2)
    
    def format_hex(self, data: bytes, highlight_pos: int = -1) -> str:
        """Format bytes as hex with optional highlighting"""
        result = []
        for i, byte in enumerate(data):
            if i == highlight_pos:
                result.append(f"[{byte:02X}]")
            else:
                result.append(f"{byte:02X}")
        return ' '.join(result)
    
    def find_new_strings(self, data1: bytes, data2: bytes):
        """Find strings that appear in data2 but not data1"""
        strings1 = set(self.extract_strings(data1))
        strings2 = set(self.extract_strings(data2))
        
        new_strings = strings2 - strings1
        removed_strings = strings1 - strings2
        
        if new_strings:
            print(f"\n   📝 New strings in File 2:")
            for s in sorted(new_strings)[:10]:
                print(f"      + {s}")
        
        if removed_strings:
            print(f"\n   📝 Removed strings from File 1:")
            for s in sorted(removed_strings)[:10]:
                print(f"      - {s}")
    
    def extract_strings(self, data: bytes, min_length: int = 4) -> list:
        """Extract readable strings from binary data"""
        strings = []
        current = []
        
        for byte in data:
            if 32 <= byte < 127:
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    text = ''.join(current)
                    if any(c.isalpha() for c in text):
                        strings.append(text)
                current = []
        
        return strings
    
    def generate_report(self):
        """Generate comparison report"""
        print("\n" + "=" * 60)
        print("🔬 ACD Binary Comparison Report")
        print("=" * 60)
        
        self.load_files()
        self.compare_headers()
        self.compare_blocks()
        
        print("\n✅ Comparison complete!")

def main():
    """Compare two ACD files"""
    if len(sys.argv) != 3:
        print("Usage: python acd_binary_comparator.py <file1.ACD> <file2.ACD>")
        sys.exit(1)
    
    comparator = ACDBinaryComparator(sys.argv[1], sys.argv[2])
    comparator.generate_report()

if __name__ == "__main__":
    main() 