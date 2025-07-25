#!/usr/bin/env python3
"""
Comprehensive search for L5X identifiers in extracted ACD blocks
Using exact names from L5X exports
"""

import os
import json
import struct
from pathlib import Path

class ComprehensiveIdentifierSearch:
    def __init__(self, blocks_dir):
        self.blocks_dir = Path(blocks_dir)
        self.results = {}
        
        # Exact program names from L5X exports
        self.program_names = [
            "Main",
            "Master_Main", 
            "SafetyProgram",
            "Milling_Device_Config",
            "Milling_Device_Logic",
            "Milling_DeviceLogic",
            "Milling_AutoLogic",
            "Milling_PID_Logic",
            "GrainLoadin_Device_Config",
            "GrainLoadin_Device_Logic",
            "GrainLoadin_PID_Logic",
            "Receiving_DeviceLogic",
            "Receiving_AutoLogic",
            "MashWater_Device_Config",
            "MashWater_Device_Logic",
            "MashWater_DeviceLogic", 
            "MashWater_AutoLogic",
            "MashWater_PID_Logic",
            "MashCooler_Device_Config",
            "MashCooler_Device_Logic",
            "MashCooler_DeviceLogic",
            "MashCooler_AutoLogic",
            "MashCooler_PID_Logic",
            "Cookers_Device_Config",
            "Cookers_Device_Logic",
            "Cookers_PID_Logic",
            "Cooker_DeviceLogic",
            "Cooker_AutoLogic",
            "Cooker_1_DeviceLogic",
            "Cooker_1_AutoLogic",
            "Cooker_2_DeviceLogic",
            "Cooker_2_AutoLogic",
            "DropTub_Device_Config",
            "DropTub_Device_Logic",
            "DropTub_DeviceLogic",
            "DropTub_AutoLogic",
            "DropTub_PID_Logic",
            "Mashing01_FBD01"
        ]
        
        # Sample module names
        self.module_names = [
            "PLC100_EN4TR",
            "ENET_ECP100_C_0",
            "DI_ECP100_A_1",
            "DI_ECP100_A_2",
            "DO_ECP100_B_1",
            "AI_ECP100_C_1",
            "AO_ECP100_C_6",
            "FAN_025",
            "CONV_005",
            "PMP_2000",
            "AGI_2014"
        ]
        
        # Controller name
        self.controller_name = "PLC100_Mashing"
        
    def search_block(self, block_path):
        """Search a single block for identifiers"""
        print(f"\n📦 Searching in {block_path.name}...")
        
        with open(block_path, 'rb') as f:
            data = f.read()
        
        block_results = {
            'programs': {},
            'modules': {},
            'controller': {},
            'patterns': {}
        }
        
        # Search for controller name
        self._search_identifier(data, self.controller_name, block_results['controller'])
        
        # Search for program names
        for prog_name in self.program_names:
            found = self._search_identifier(data, prog_name, block_results['programs'])
            if found:
                print(f"  ✅ Found program '{prog_name}'")
        
        # Search for module names
        for module_name in self.module_names:
            found = self._search_identifier(data, module_name, block_results['modules'])
            if found:
                print(f"  ✅ Found module '{module_name}'")
        
        # Look for string patterns
        self._analyze_string_patterns(data, block_results['patterns'])
        
        return block_results
    
    def _search_identifier(self, data, identifier, results_dict):
        """Search for an identifier in multiple encodings"""
        found = False
        
        # Try UTF-8
        try:
            search_bytes = identifier.encode('utf-8')
            positions = []
            start = 0
            while True:
                pos = data.find(search_bytes, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            if positions:
                results_dict[identifier] = {
                    'encoding': 'utf-8',
                    'count': len(positions),
                    'positions': positions[:5],
                    'context': self._get_context(data, positions[0], len(search_bytes))
                }
                found = True
        except:
            pass
        
        # Try UTF-16LE
        if not found:
            try:
                search_bytes = identifier.encode('utf-16le')
                positions = []
                start = 0
                while True:
                    pos = data.find(search_bytes, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1
                
                if positions:
                    results_dict[identifier] = {
                        'encoding': 'utf-16le',
                        'count': len(positions),
                        'positions': positions[:5],
                        'context': self._get_context(data, positions[0], len(search_bytes))
                    }
                    found = True
            except:
                pass
        
        # Try Pascal string (1-byte length prefix)
        if not found:
            pascal_bytes = bytes([len(identifier)]) + identifier.encode('utf-8')
            if pascal_bytes in data:
                pos = data.find(pascal_bytes)
                results_dict[identifier] = {
                    'encoding': 'pascal-1byte',
                    'count': 1,
                    'positions': [pos],
                    'context': self._get_context(data, pos, len(pascal_bytes))
                }
                found = True
        
        # Try 2-byte length prefix (little-endian)
        if not found:
            length_bytes = struct.pack('<H', len(identifier))
            prefixed_bytes = length_bytes + identifier.encode('utf-8')
            if prefixed_bytes in data:
                pos = data.find(prefixed_bytes)
                results_dict[identifier] = {
                    'encoding': 'length-prefixed-2byte-le',
                    'count': 1,
                    'positions': [pos],
                    'context': self._get_context(data, pos, len(prefixed_bytes))
                }
                found = True
        
        return found
    
    def _get_context(self, data, position, length):
        """Get context around a found identifier"""
        start = max(0, position - 20)
        end = min(len(data), position + length + 20)
        
        return {
            'before': data[start:position].hex(),
            'match': data[position:position + length].hex(),
            'after': data[position + length:end].hex()
        }
    
    def _analyze_string_patterns(self, data, patterns):
        """Analyze common string patterns in the block"""
        # Look for Pascal strings
        pascal_strings = []
        i = 0
        while i < len(data) - 1:
            length = data[i]
            if 0 < length < 100:  # Reasonable string length
                try:
                    string_data = data[i+1:i+1+length].decode('utf-8')
                    if all(c.isprintable() or c.isspace() for c in string_data):
                        pascal_strings.append({
                            'position': i,
                            'length': length,
                            'content': string_data
                        })
                        i += length + 1
                        continue
                except:
                    pass
            i += 1
        
        if pascal_strings:
            patterns['pascal_strings'] = {
                'count': len(pascal_strings),
                'samples': pascal_strings[:10]
            }
        
        # Look for null-terminated strings
        null_strings = []
        parts = data.split(b'\x00')
        for i, part in enumerate(parts[:-1]):
            if len(part) > 3:
                try:
                    text = part.decode('utf-8')
                    if all(c.isprintable() or c.isspace() for c in text):
                        null_strings.append(text)
                except:
                    pass
        
        if null_strings:
            patterns['null_terminated_strings'] = {
                'count': len(null_strings),
                'samples': null_strings[:10]
            }
    
    def search_all_blocks(self):
        """Search all blocks for identifiers"""
        print(f"🔍 Starting comprehensive identifier search...")
        print(f"  Programs to find: {len(self.program_names)}")
        print(f"  Modules to find: {len(self.module_names)}")
        
        for block_file in sorted(self.blocks_dir.glob("*.bin")):
            block_results = self.search_block(block_file)
            if any(block_results[k] for k in ['programs', 'modules', 'controller']):
                self.results[block_file.name] = block_results
        
        # Save results
        output_file = Path("comprehensive_search_results.json")
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✅ Results saved to {output_file}")
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print search summary"""
        print("\n" + "="*60)
        print("📊 SEARCH SUMMARY")
        print("="*60)
        
        total_programs = 0
        total_modules = 0
        controller_found = False
        
        for block_name, block_data in self.results.items():
            programs = len(block_data.get('programs', {}))
            modules = len(block_data.get('modules', {}))
            
            if programs > 0 or modules > 0:
                print(f"\n📦 {block_name}:")
                if programs > 0:
                    print(f"   Programs found: {programs}")
                    total_programs += programs
                if modules > 0:
                    print(f"   Modules found: {modules}")
                    total_modules += modules
                if self.controller_name in block_data.get('controller', {}):
                    print(f"   ✓ Controller name found")
                    controller_found = True
        
        print(f"\n📈 TOTALS:")
        print(f"   Programs found: {total_programs}/{len(self.program_names)}")
        print(f"   Modules found: {total_modules}/{len(self.module_names)}")
        print(f"   Controller found: {'Yes' if controller_found else 'No'}")

def main():
    blocks_dir = "extracted_blocks"
    searcher = ComprehensiveIdentifierSearch(blocks_dir)
    searcher.search_all_blocks()

if __name__ == "__main__":
    main() 