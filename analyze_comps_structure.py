#!/usr/bin/env python3
"""
Analyze the structure of Comps.Dat records to understand how to extract ladder logic
"""

import os
import struct
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract

class CompsAnalyzer:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("comps_analysis")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
    def analyze(self):
        """Analyze Comps.Dat structure"""
        print(f"\n🔍 Analyzing Comps.Dat structure from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Read Comps.Dat
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        print(f"\n📊 Total records: {len(comps_db.records.record)}")
        
        # Analyze different record types
        record_types = {}
        string_patterns = {}
        
        print("\n📋 Analyzing record patterns...")
        
        for i, record in enumerate(comps_db.records.record[:1000]):  # First 1000
            if i % 100 == 0:
                print(f"  Progress: {i}/1000")
            
            try:
                # Get record buffer
                if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                    buffer = record.record.record_buffer
                    
                    # Record type statistics
                    if len(buffer) > 4:
                        # Try to identify record type from first bytes
                        type_indicator = struct.unpack('<I', buffer[:4])[0]
                        record_types[type_indicator] = record_types.get(type_indicator, 0) + 1
                    
                    # Look for text strings
                    text_found = self.extract_strings(buffer)
                    for text in text_found:
                        if len(text) > 5:  # Meaningful strings
                            string_patterns[text] = string_patterns.get(text, 0) + 1
                            
                            # Check for ladder logic patterns
                            if any(keyword in text for keyword in ['XIC', 'XIO', 'OTE', 'OTL', 'OTU', 'TON', 'RES']):
                                print(f"\n🎯 Found ladder instruction at record {i}: {text[:100]}")
                                self.save_sample_record(i, record, text)
                            
                            # Check for program/routine names
                            if any(keyword in text for keyword in ['Main', 'Program', 'Routine', 'Logic']):
                                print(f"📁 Found component name at record {i}: {text}")
                                
            except Exception as e:
                pass
        
        # Report findings
        print("\n📊 Analysis Results:")
        print(f"  Unique record type indicators: {len(record_types)}")
        print(f"  Unique strings found: {len(string_patterns)}")
        
        # Show most common strings
        common_strings = sorted(string_patterns.items(), key=lambda x: x[1], reverse=True)[:20]
        print("\n  Most common strings:")
        for string, count in common_strings:
            print(f"    '{string}': {count} times")
            
        # Look specifically for ladder logic
        self.search_for_ladder_logic(comps_db)
        
    def extract_strings(self, buffer):
        """Extract readable strings from buffer"""
        strings = []
        current = []
        
        # Try UTF-8
        for byte in buffer:
            if 32 <= byte <= 126:  # Printable ASCII
                current.append(chr(byte))
            else:
                if len(current) > 4:
                    strings.append(''.join(current))
                current = []
        
        if current:
            strings.append(''.join(current))
            
        # Try UTF-16LE
        for i in range(0, len(buffer) - 1, 2):
            try:
                char = buffer[i:i+2].decode('utf-16le')
                if char.isprintable():
                    current.append(char)
                else:
                    if len(current) > 4:
                        strings.append(''.join(current))
                    current = []
            except:
                if current:
                    strings.append(''.join(current))
                current = []
                
        return strings
    
    def save_sample_record(self, index, record, description):
        """Save a sample record for analysis"""
        sample_file = self.output_dir / f"sample_record_{index}.bin"
        
        if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
            with open(sample_file, 'wb') as f:
                f.write(record.record.record_buffer)
            print(f"    Saved to: {sample_file}")
    
    def search_for_ladder_logic(self, comps_db):
        """Search specifically for ladder logic patterns"""
        print("\n🔍 Searching for ladder logic patterns...")
        
        # Common ladder instruction patterns
        instructions = [
            b'XIC', b'XIO', b'OTE', b'OTL', b'OTU',  # Basic bits
            b'TON', b'TOF', b'RTO', b'CTU', b'CTD',  # Timers/Counters
            b'MOV', b'ADD', b'SUB', b'MUL', b'DIV',  # Math
            b'EQU', b'NEQ', b'LES', b'GRT', b'LEQ',  # Compare
            b'JSR', b'RET', b'JMP', b'LBL'           # Program flow
        ]
        
        found_instructions = {}
        
        for i, record in enumerate(comps_db.records.record):
            if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                buffer = record.record.record_buffer
                
                for instruction in instructions:
                    if instruction in buffer:
                        found_instructions[instruction.decode()] = found_instructions.get(instruction.decode(), 0) + 1
                        
                        # Find context around instruction
                        pos = buffer.find(instruction)
                        context_start = max(0, pos - 20)
                        context_end = min(len(buffer), pos + 50)
                        context = buffer[context_start:context_end]
                        
                        # Only print first occurrence of each instruction
                        if found_instructions[instruction.decode()] == 1:
                            print(f"\n  Found {instruction.decode()} in record {i}")
                            print(f"    Context: {context.hex()}")
                            
                            # Try to decode as text
                            text_parts = self.extract_strings(context)
                            if text_parts:
                                print(f"    Text: {' '.join(text_parts)}")
        
        print(f"\n📊 Instruction Summary:")
        for inst, count in sorted(found_instructions.items()):
            print(f"  {inst}: {count} occurrences")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    analyzer = CompsAnalyzer(acd_file)
    analyzer.analyze()

if __name__ == "__main__":
    main() 