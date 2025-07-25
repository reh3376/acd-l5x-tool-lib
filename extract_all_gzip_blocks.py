#!/usr/bin/env python3
"""
Extract ALL GZIP blocks from ACD file using multiple strategies
"""

import os
import gzip
import zlib
import struct
from pathlib import Path

class GZIPBlockExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("extracted_blocks_complete")
        self.output_dir.mkdir(exist_ok=True)
        
        with open(self.acd_file, 'rb') as f:
            self.data = f.read()
        
        print(f"📄 Loaded ACD file: {self.acd_file.name}")
        print(f"📏 Size: {len(self.data):,} bytes")
        
    def find_all_gzip_headers(self):
        """Find all GZIP headers in the file"""
        headers = []
        offset = 0
        
        while offset < len(self.data):
            pos = self.data.find(b'\x1F\x8B', offset)
            if pos == -1:
                break
            
            # Check if it's a valid GZIP header (next byte should be 0x08)
            if pos + 2 < len(self.data) and self.data[pos + 2] == 0x08:
                headers.append(pos)
            
            offset = pos + 1
        
        print(f"\n🔍 Found {len(headers)} potential GZIP headers")
        return headers
    
    def extract_gzip_block(self, start_pos, block_num):
        """Try to extract a GZIP block starting at given position"""
        # Strategy 1: Try standard gzip decompression with various sizes
        test_sizes = [
            100, 500, 1000, 5000, 10000, 50000, 100000, 500000,
            1000000, 2000000, 5000000, 10000000, 20000000
        ]
        
        for size in test_sizes:
            if start_pos + size > len(self.data):
                size = len(self.data) - start_pos
            
            try:
                compressed_data = self.data[start_pos:start_pos + size]
                decompressed = gzip.decompress(compressed_data)
                
                # Success! Save the block
                output_file = self.output_dir / f"block_{block_num:03d}_offset_0x{start_pos:x}_gzip.bin"
                with open(output_file, 'wb') as f:
                    f.write(decompressed)
                
                print(f"✅ Block {block_num}: offset=0x{start_pos:x}, "
                      f"compressed={size:,}, decompressed={len(decompressed):,}")
                
                return size, len(decompressed)
                
            except Exception:
                continue
        
        # Strategy 2: Try zlib decompression (raw deflate)
        for size in test_sizes[:10]:  # Try smaller sizes for zlib
            if start_pos + size > len(self.data):
                size = len(self.data) - start_pos
            
            try:
                # Skip GZIP header (10 bytes) and try raw deflate
                compressed_data = self.data[start_pos + 10:start_pos + size]
                decompressed = zlib.decompress(compressed_data)
                
                output_file = self.output_dir / f"block_{block_num:03d}_offset_0x{start_pos:x}_zlib.bin"
                with open(output_file, 'wb') as f:
                    f.write(decompressed)
                
                print(f"✅ Block {block_num} (zlib): offset=0x{start_pos:x}, "
                      f"compressed={size:,}, decompressed={len(decompressed):,}")
                
                return size, len(decompressed)
                
            except Exception:
                continue
        
        # Strategy 3: Try to find the end of GZIP block
        # GZIP format ends with CRC32 (4 bytes) + uncompressed size (4 bytes)
        for end_offset in range(start_pos + 50, min(start_pos + 50000000, len(self.data))):
            try:
                compressed_data = self.data[start_pos:end_offset]
                decompressed = gzip.decompress(compressed_data)
                
                # Check if the following 8 bytes could be CRC + size
                if end_offset + 8 <= len(self.data):
                    potential_size = struct.unpack('<I', self.data[end_offset-4:end_offset])[0]
                    if potential_size == len(decompressed) % (2**32):
                        # This looks like a valid GZIP ending
                        output_file = self.output_dir / f"block_{block_num:03d}_offset_0x{start_pos:x}_exact.bin"
                        with open(output_file, 'wb') as f:
                            f.write(decompressed)
                        
                        print(f"✅ Block {block_num} (exact): offset=0x{start_pos:x}, "
                              f"compressed={end_offset-start_pos:,}, decompressed={len(decompressed):,}")
                        
                        return end_offset - start_pos, len(decompressed)
                
            except Exception:
                continue
        
        print(f"❌ Block {block_num}: Failed to extract from offset 0x{start_pos:x}")
        return 0, 0
    
    def extract_all_blocks(self):
        """Extract all GZIP blocks from the ACD file"""
        headers = self.find_all_gzip_headers()
        
        print("\n🗜️  Extracting compressed blocks...")
        
        total_extracted = 0
        total_decompressed_size = 0
        
        for i, header_pos in enumerate(headers):
            compressed_size, decompressed_size = self.extract_gzip_block(header_pos, i + 1)
            
            if compressed_size > 0:
                total_extracted += 1
                total_decompressed_size += decompressed_size
        
        print(f"\n📊 Summary:")
        print(f"  Total blocks extracted: {total_extracted}/{len(headers)}")
        print(f"  Total decompressed size: {total_decompressed_size:,} bytes")
        
        return total_extracted
    
    def analyze_text_header(self):
        """Analyze the text header section"""
        print("\n📝 Analyzing text header...")
        
        # Find where binary data starts (after XML-like header)
        binary_start = self.data.find(b'\x00\x00\x00')
        if binary_start > 0:
            text_header = self.data[:binary_start].decode('utf-8', errors='ignore')
            print(f"  Text header size: {binary_start:,} bytes")
            
            # Look for key information
            if 'RSLogix5000Content' in text_header:
                print("  ✓ Found RSLogix5000Content header")
            if 'Controller Name=' in text_header:
                start = text_header.find('Controller Name="') + 17
                end = text_header.find('"', start)
                controller_name = text_header[start:end]
                print(f"  ✓ Controller Name: {controller_name}")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    
    extractor = GZIPBlockExtractor(acd_file)
    extractor.analyze_text_header()
    total = extractor.extract_all_blocks()
    
    if total > 0:
        print(f"\n✅ Extraction complete! Check '{extractor.output_dir}' directory")
    else:
        print("\n❌ No blocks could be extracted")

if __name__ == "__main__":
    main() 