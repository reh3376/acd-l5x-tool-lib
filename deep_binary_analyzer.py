#!/usr/bin/env python3
"""
Deep binary analyzer for ACD format reverse engineering
"""

import struct
from pathlib import Path
from collections import defaultdict
import string
import json

class DeepBinaryAnalyzer:
    """Deep analysis of binary structures in ACD files"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.findings = {
            'strings': [],
            'patterns': [],
            'structures': [],
            'potential_headers': []
        }
    
    def find_all_strings(self, min_length=6):
        """Find all readable strings in the data"""
        strings = []
        current = []
        start_offset = 0
        
        for i, byte in enumerate(self.data):
            if chr(byte) in string.printable and byte not in [0, 10, 13]:
                if not current:
                    start_offset = i
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    text = ''.join(current)
                    # Filter out noise
                    if any(c.isalpha() for c in text):
                        strings.append({
                            'offset': f'0x{start_offset:X}',
                            'length': len(text),
                            'text': text
                        })
                current = []
        
        return strings
    
    def find_structured_data(self):
        """Look for structured data patterns"""
        patterns = []
        
        # Look for length-prefixed strings (Pascal style)
        print("🔍 Searching for Pascal-style strings...")
        for i in range(len(self.data) - 256):
            length = self.data[i]
            if 4 <= length <= 100:  # Reasonable string length
                if i + 1 + length <= len(self.data):
                    try:
                        text = self.data[i + 1:i + 1 + length].decode('utf-8', errors='ignore')
                        if all(c.isprintable() or c == ' ' for c in text) and any(c.isalpha() for c in text):
                            patterns.append({
                                'type': 'pascal_string',
                                'offset': f'0x{i:X}',
                                'length': length,
                                'value': text
                            })
                    except:
                        pass
        
        # Look for 2-byte length prefixed strings
        print("🔍 Searching for 2-byte prefixed strings...")
        for i in range(0, len(self.data) - 256, 2):
            if i + 2 > len(self.data):
                break
            length = struct.unpack('<H', self.data[i:i+2])[0]
            if 4 <= length <= 1000:
                if i + 2 + length <= len(self.data):
                    try:
                        text = self.data[i + 2:i + 2 + length].decode('utf-8', errors='ignore')
                        if all(c.isprintable() or c == ' ' for c in text) and any(c.isalpha() for c in text):
                            patterns.append({
                                'type': 'uint16_string',
                                'offset': f'0x{i:X}',
                                'length': length,
                                'value': text
                            })
                    except:
                        pass
        
        return patterns
    
    def find_component_patterns(self):
        """Find patterns specific to PLC components"""
        # Known component markers
        markers = {
            'Program': b'\x0CProgram',
            'Routine': b'\x0CRoutine',  
            'DataType': b'\x0EDataType',
            'Tag': b'\x03Tag',
            'Module': b'\x06Module',
            'Controller': b'\x0AController'
        }
        
        component_data = defaultdict(list)
        
        for name, marker in markers.items():
            offset = 0
            while True:
                pos = self.data.find(marker, offset)
                if pos == -1:
                    break
                
                # Try to extract associated data
                comp_info = {
                    'offset': f'0x{pos:X}',
                    'type': name
                }
                
                # Look for name after the marker
                name_offset = pos + len(marker)
                if name_offset + 1 < len(self.data):
                    name_len = self.data[name_offset]
                    if 0 < name_len < 100 and name_offset + 1 + name_len <= len(self.data):
                        try:
                            comp_name = self.data[name_offset + 1:name_offset + 1 + name_len].decode('utf-8', errors='ignore')
                            if all(c.isprintable() or c == ' ' for c in comp_name):
                                comp_info['name'] = comp_name
                        except:
                            pass
                
                component_data[name].append(comp_info)
                offset = pos + 1
        
        return dict(component_data)
    
    def analyze_block_structure(self):
        """Analyze the overall block structure"""
        print("\n📊 Analyzing Block Structure...")
        
        # Look for common headers/magic numbers
        magic_numbers = [
            (b'Comps\x00', 'Comps Database'),
            (b'.dat', 'Data Section'),
            (b'.idx', 'Index Section'),
            (b'RSLogix', 'RSLogix Marker'),
            (b'5000', 'Studio 5000 Marker')
        ]
        
        headers = []
        for magic, description in magic_numbers:
            offset = 0
            while True:
                pos = self.data.find(magic, offset)
                if pos == -1:
                    break
                headers.append({
                    'offset': f'0x{pos:X}',
                    'type': description,
                    'hex': ' '.join(f'{b:02X}' for b in self.data[pos:pos+16])
                })
                offset = pos + 1
        
        return headers
    
    def find_plc_specific_data(self):
        """Look for PLC-specific data patterns"""
        plc_data = {
            'tag_definitions': [],
            'routine_names': [],
            'program_names': [],
            'data_types': []
        }
        
        # Common PLC tag prefixes
        tag_prefixes = ['HMI_', 'PLC_', 'Local:', 'Program:', 'Controller:']
        
        all_strings = self.find_all_strings()
        
        for string_info in all_strings:
            text = string_info['text']
            
            # Check for tag-like patterns
            if any(text.startswith(prefix) for prefix in tag_prefixes):
                plc_data['tag_definitions'].append(string_info)
            
            # Check for routine names (often end with specific patterns)
            if text.endswith('_Routine') or text == 'MainRoutine' or text.endswith('_Logic'):
                plc_data['routine_names'].append(string_info)
            
            # Check for program names
            if text.endswith('_Program') or text == 'MainProgram':
                plc_data['program_names'].append(string_info)
            
            # Check for data types
            if text in ['BOOL', 'DINT', 'REAL', 'STRING', 'TIMER', 'COUNTER']:
                plc_data['data_types'].append(string_info)
        
        return plc_data
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        print("🔬 Deep Binary Analysis Report")
        print("=" * 60)
        
        # Find all strings
        print("\n📝 Finding all strings...")
        strings = self.find_all_strings()
        print(f"   Found {len(strings)} readable strings")
        
        # Find structured data
        print("\n🔍 Finding structured data...")
        patterns = self.find_structured_data()
        print(f"   Found {len(patterns)} structured patterns")
        
        # Find components
        print("\n🏗️ Finding PLC components...")
        components = self.find_component_patterns()
        for comp_type, items in components.items():
            print(f"   {comp_type}: {len(items)} found")
        
        # Find headers
        headers = self.analyze_block_structure()
        print(f"\n📋 Found {len(headers)} header/magic patterns")
        
        # Find PLC data
        print("\n🏭 Finding PLC-specific data...")
        plc_data = self.find_plc_specific_data()
        
        # Compile report
        report = {
            'summary': {
                'total_size': len(self.data),
                'strings_found': len(strings),
                'patterns_found': len(patterns),
                'headers_found': len(headers)
            },
            'components': {k: len(v) for k, v in components.items()},
            'plc_data_summary': {k: len(v) for k, v in plc_data.items()},
            'sample_strings': strings[:20],
            'sample_patterns': patterns[:10],
            'headers': headers,
            'sample_components': {k: v[:3] for k, v in components.items()},
            'sample_plc_data': {k: v[:5] for k, v in plc_data.items()}
        }
        
        return report

def main():
    """Perform deep analysis on Block 3"""
    block3_path = Path("extracted_blocks/block_003_offset_0x10c95.bin")
    
    if not block3_path.exists():
        print("❌ Block 3 not found!")
        return
    
    print(f"📂 Loading {block3_path}")
    with open(block3_path, 'rb') as f:
        data = f.read()
    
    print(f"📏 Size: {len(data):,} bytes\n")
    
    analyzer = DeepBinaryAnalyzer(data)
    report = analyzer.generate_report()
    
    # Save detailed report
    with open('deep_analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n✅ Detailed report saved to deep_analysis_report.json")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"   Total strings: {report['summary']['strings_found']}")
    print(f"   Structured patterns: {report['summary']['patterns_found']}")
    print(f"   Components found:")
    for comp, count in report['components'].items():
        if count > 0:
            print(f"      - {comp}: {count}")

if __name__ == "__main__":
    main() 