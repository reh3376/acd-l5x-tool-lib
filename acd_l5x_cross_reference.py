#!/usr/bin/env python3
"""
ACD to L5X Cross-Reference Tool
Maps ACD binary structures to L5X export data for reverse engineering
"""

import os
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib

class ACDtoL5XMapper:
    def __init__(self, acd_file, exports_dir):
        self.acd_file = Path(acd_file)
        self.exports_dir = Path(exports_dir)
        self.mapping = {
            'controller_info': {},
            'programs': {},
            'modules': {},
            'data_types': {},
            'aois': {},
            'tags': {},
            'routines': {}
        }
        
    def extract_l5x_identifiers(self):
        """Extract all identifiers from L5X exports"""
        print("📋 Extracting identifiers from L5X exports...")
        
        # Extract program names and routines
        for l5x_file in self.exports_dir.glob("*_Program.L5X"):
            try:
                tree = ET.parse(l5x_file)
                root = tree.getroot()
                
                target_name = root.get('TargetName')
                if target_name:
                    self.mapping['programs'][target_name] = {
                        'file': l5x_file.name,
                        'routines': []
                    }
                    
                    # Extract routine names
                    for routine in root.findall('.//Routine'):
                        routine_name = routine.get('Name')
                        if routine_name:
                            self.mapping['programs'][target_name]['routines'].append(routine_name)
                            self.mapping['routines'][routine_name] = target_name
                            
            except Exception as e:
                print(f"  ⚠️  Error parsing {l5x_file.name}: {e}")
        
        # Extract module names
        for l5x_file in self.exports_dir.glob("*_Module.L5X"):
            try:
                tree = ET.parse(l5x_file)
                root = tree.getroot()
                
                for module in root.findall('.//Module'):
                    module_name = module.get('Name')
                    if module_name:
                        self.mapping['modules'][module_name] = {
                            'file': l5x_file.name,
                            'catalog': module.get('CatalogNumber', '')
                        }
                        
            except Exception as e:
                print(f"  ⚠️  Error parsing {l5x_file.name}: {e}")
        
        print(f"  ✅ Found {len(self.mapping['programs'])} programs")
        print(f"  ✅ Found {len(self.mapping['routines'])} routines")
        print(f"  ✅ Found {len(self.mapping['modules'])} modules")
        
    def search_acd_for_identifiers(self):
        """Search ACD binary for L5X identifiers"""
        print("\n🔍 Searching ACD binary for L5X identifiers...")
        
        # Read ACD file
        with open(self.acd_file, 'rb') as f:
            acd_data = f.read()
        
        # Search for each identifier
        found_mappings = {
            'programs': {},
            'routines': {},
            'modules': {}
        }
        
        # Search for program names
        for prog_name in self.mapping['programs']:
            positions = []
            search_bytes = prog_name.encode('utf-8')
            start = 0
            while True:
                pos = acd_data.find(search_bytes, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            if positions:
                found_mappings['programs'][prog_name] = {
                    'count': len(positions),
                    'positions': positions[:5]  # First 5 positions
                }
                print(f"  📍 Found program '{prog_name}' at {len(positions)} positions")
        
        # Search for routine names
        for routine_name in self.mapping['routines']:
            positions = []
            search_bytes = routine_name.encode('utf-8')
            start = 0
            while True:
                pos = acd_data.find(search_bytes, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            if positions:
                found_mappings['routines'][routine_name] = {
                    'count': len(positions),
                    'positions': positions[:5]  # First 5 positions
                }
        
        # Search for module names
        for module_name in self.mapping['modules']:
            positions = []
            search_bytes = module_name.encode('utf-8')
            start = 0
            while True:
                pos = acd_data.find(search_bytes, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            if positions:
                found_mappings['modules'][module_name] = {
                    'count': len(positions),
                    'positions': positions[:5]  # First 5 positions
                }
        
        return found_mappings
    
    def analyze_acd_structure_around_identifiers(self, found_mappings):
        """Analyze ACD structure around found identifiers"""
        print("\n📊 Analyzing ACD structure around identifiers...")
        
        with open(self.acd_file, 'rb') as f:
            acd_data = f.read()
        
        patterns = {
            'before_programs': {},
            'before_routines': {},
            'before_modules': {}
        }
        
        # Analyze patterns before program names
        for prog_name, info in found_mappings['programs'].items():
            if info['positions']:
                pos = info['positions'][0]
                # Get 20 bytes before
                start = max(0, pos - 20)
                before_data = acd_data[start:pos]
                patterns['before_programs'][prog_name] = {
                    'hex': before_data.hex(),
                    'length_indicator': self._check_length_indicator(before_data, len(prog_name))
                }
        
        return patterns
    
    def _check_length_indicator(self, data, expected_length):
        """Check if data contains a length indicator"""
        if len(data) >= 2:
            # Check 2-byte little-endian
            length_le = int.from_bytes(data[-2:], 'little')
            if length_le == expected_length:
                return {'type': '2-byte-le', 'value': length_le}
            
            # Check 2-byte big-endian
            length_be = int.from_bytes(data[-2:], 'big')
            if length_be == expected_length:
                return {'type': '2-byte-be', 'value': length_be}
        
        if len(data) >= 4:
            # Check 4-byte little-endian
            length_le = int.from_bytes(data[-4:], 'little')
            if length_le == expected_length:
                return {'type': '4-byte-le', 'value': length_le}
        
        return None
    
    def generate_mapping_report(self, found_mappings, patterns):
        """Generate comprehensive mapping report"""
        report = {
            'acd_file': str(self.acd_file),
            'exports_analyzed': len(list(self.exports_dir.glob("*.L5X"))),
            'identifiers_extracted': {
                'programs': len(self.mapping['programs']),
                'routines': len(self.mapping['routines']),
                'modules': len(self.mapping['modules'])
            },
            'identifiers_found_in_acd': {
                'programs': len(found_mappings['programs']),
                'routines': len(found_mappings['routines']),
                'modules': len(found_mappings['modules'])
            },
            'mappings': found_mappings,
            'patterns': patterns
        }
        
        # Save report
        report_file = self.exports_dir / "acd_l5x_mapping.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Mapping report saved to: {report_file}")
        
        # Print summary
        print("\n📊 Mapping Summary:")
        print(f"  Programs found: {len(found_mappings['programs'])}/{len(self.mapping['programs'])}")
        print(f"  Routines found: {len(found_mappings['routines'])}/{len(self.mapping['routines'])}")
        print(f"  Modules found: {len(found_mappings['modules'])}/{len(self.mapping['modules'])}")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    exports_dir = "docs/exports"
    
    mapper = ACDtoL5XMapper(acd_file, exports_dir)
    
    # Extract identifiers from L5X files
    mapper.extract_l5x_identifiers()
    
    # Search for them in ACD
    found_mappings = mapper.search_acd_for_identifiers()
    
    # Analyze structure
    patterns = mapper.analyze_acd_structure_around_identifiers(found_mappings)
    
    # Generate report
    mapper.generate_mapping_report(found_mappings, patterns)

if __name__ == "__main__":
    main() 