#!/usr/bin/env python3
"""
Parse the Comps database structure from ACD Block 3
This is the main database containing all PLC components
"""

import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

class CompsParser:
    """Parser for the Comps database format in ACD files"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.components = {}
        
    def find_comps_header(self) -> int:
        """Find the Comps database header"""
        pos = self.data.find(b'Comps\x00')
        if pos == -1:
            raise ValueError("Comps header not found!")
        print(f"✅ Found Comps database at offset 0x{pos:X}")
        return pos
    
    def parse_database_sections(self):
        """Parse the .dat and .idx sections"""
        # Find .dat section
        dat_pos = self.data.find(b'.dat')
        idx_pos = self.data.find(b'.idx')
        
        if dat_pos != -1:
            print(f"📁 Found .dat section at 0x{dat_pos:X}")
            self.parse_dat_section(dat_pos)
            
        if idx_pos != -1:
            print(f"📇 Found .idx section at 0x{idx_pos:X}")
            self.parse_idx_section(idx_pos)
    
    def parse_dat_section(self, start_pos: int):
        """Parse the .dat (data) section"""
        print("\n🔍 Analyzing .dat section:")
        
        # Look for component type markers after .dat
        offset = start_pos + 4
        
        # Common component types to search for
        comp_types = [
            b'Controller', b'DataType', b'Program', b'Routine',
            b'Tag', b'Module', b'Task', b'Trend'
        ]
        
        # Find all occurrences of each type
        for comp_type in comp_types:
            positions = []
            search_start = offset
            
            while True:
                pos = self.data.find(comp_type, search_start)
                if pos == -1 or pos > start_pos + 1000000:  # Limit search range
                    break
                positions.append(pos)
                search_start = pos + 1
                
            if positions:
                print(f"  - {comp_type.decode()}: {len(positions)} occurrences")
                self.components[comp_type.decode()] = positions[:5]  # Store first 5
    
    def parse_idx_section(self, start_pos: int):
        """Parse the .idx (index) section"""
        print("\n🔍 Analyzing .idx section:")
        
        # The index section typically contains offsets to data records
        offset = start_pos + 4
        
        # Try to read some index entries (assuming 4-byte offsets)
        index_entries = []
        for i in range(20):  # Read first 20 entries
            if offset + 4 > len(self.data):
                break
            
            entry = struct.unpack('<I', self.data[offset:offset+4])[0]
            if entry > 0 and entry < len(self.data):  # Valid offset
                index_entries.append(entry)
            offset += 4
        
        print(f"  - Found {len(index_entries)} potential index entries")
        if index_entries:
            print(f"  - First few entries: {index_entries[:5]}")
    
    def extract_component_data(self, comp_type: str, position: int) -> Dict:
        """Extract data for a specific component"""
        result = {
            'type': comp_type,
            'position': f'0x{position:X}',
            'data': {}
        }
        
        # Try to parse the component structure
        offset = position + len(comp_type.encode()) + 1
        
        # Look for common patterns
        # Many components have a name string following the type
        name, new_offset = self.read_string(offset)
        if name:
            result['data']['name'] = name
            offset = new_offset
        
        # Look for size/length indicators
        if offset + 4 <= len(self.data):
            size = struct.unpack('<I', self.data[offset:offset+4])[0]
            if size < 10000:  # Reasonable size
                result['data']['size'] = size
        
        return result
    
    def read_string(self, offset: int) -> Tuple[Optional[str], int]:
        """Read a string at the given offset"""
        if offset >= len(self.data):
            return None, offset
        
        # Try different string formats
        
        # 1. Pascal string (1-byte length prefix)
        length = self.data[offset]
        if length < 255 and offset + 1 + length <= len(self.data):
            try:
                text = self.data[offset + 1:offset + 1 + length].decode('utf-8', errors='ignore')
                if all(c.isprintable() or c.isspace() for c in text):
                    return text, offset + 1 + length
            except:
                pass
        
        # 2. C-style null-terminated string
        null_pos = self.data.find(b'\x00', offset)
        if null_pos != -1 and null_pos - offset < 255:
            try:
                text = self.data[offset:null_pos].decode('utf-8', errors='ignore')
                if text and all(c.isprintable() or c.isspace() for c in text):
                    return text, null_pos + 1
            except:
                pass
        
        # 3. 2-byte length prefix
        if offset + 2 <= len(self.data):
            length = struct.unpack('<H', self.data[offset:offset+2])[0]
            if length < 1000 and offset + 2 + length <= len(self.data):
                try:
                    text = self.data[offset + 2:offset + 2 + length].decode('utf-8', errors='ignore')
                    if all(c.isprintable() or c.isspace() for c in text):
                        return text, offset + 2 + length
                except:
                    pass
        
        return None, offset
    
    def analyze_structure(self):
        """Perform complete analysis of the Comps database"""
        print("🔬 Analyzing Comps Database Structure")
        print("=" * 50)
        
        # Find and parse the database
        comps_pos = self.find_comps_header()
        self.offset = comps_pos + 6  # Skip 'Comps\0'
        
        # Parse sections
        self.parse_database_sections()
        
        # Extract sample data for each component type
        print("\n📋 Sample Component Data:")
        for comp_type, positions in self.components.items():
            print(f"\n{comp_type}:")
            for i, pos in enumerate(positions[:3]):  # First 3 of each type
                comp_data = self.extract_component_data(comp_type, pos)
                print(f"  {i+1}. {comp_data}")
        
        return self.components

def main():
    """Parse the Comps database from Block 3"""
    block3_path = Path("extracted_blocks/block_003_offset_0x10c95.bin")
    
    if not block3_path.exists():
        print("❌ Block 3 not found! Run the extractor first.")
        return
    
    print(f"📂 Loading {block3_path}")
    with open(block3_path, 'rb') as f:
        data = f.read()
    
    print(f"📏 Block size: {len(data):,} bytes\n")
    
    parser = CompsParser(data)
    components = parser.analyze_structure()
    
    # Save analysis results
    results = {
        'block_size': len(data),
        'components_found': {k: len(v) for k, v in components.items()},
        'sample_positions': components
    }
    
    with open('comps_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✅ Analysis saved to comps_analysis.json")

if __name__ == "__main__":
    main() 