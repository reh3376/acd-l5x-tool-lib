#!/usr/bin/env python3
"""
Find complete ladder logic rungs by searching for instruction sequences
"""

import os
import struct
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract

class RungFinder:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("complete_rungs")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
        # Ladder instructions that might appear in rungs
        self.instructions = [
            b'XIC', b'XIO', b'OTE', b'OTL', b'OTU',
            b'TON', b'TOF', b'RTO', b'CTU', b'CTD',
            b'MOV', b'ADD', b'SUB', b'MUL', b'DIV',
            b'EQU', b'NEQ', b'LES', b'GRT', b'LEQ', b'GEQ',
            b'JSR', b'RET', b'JMP', b'LBL',
            b'AFI', b'NOP', b'MSG', b'GSV', b'SSV'
        ]
        
        # Common rung patterns
        self.rung_terminators = [
            b';',           # Common rung terminator
            b';\x00',       # With null
            b';\r\n',       # With newline
            b');\x00',      # Function call terminator
            b');',          # Function call terminator
        ]
        
    def find_rungs(self):
        """Find complete rungs"""
        print(f"\n🔍 Finding complete ladder logic rungs in {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Step 1: Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Search in Comps.Dat
        self.search_comps_for_rungs()
        
        # Search in extracted blocks
        self.search_blocks_for_rungs()
        
    def search_comps_for_rungs(self):
        """Search Comps.Dat for complete rungs"""
        print("\n📋 Step 2: Searching Comps.Dat for complete rungs...")
        
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        found_rungs = []
        instruction_sequences = []
        
        for i, record in enumerate(comps_db.records.record):
            if i % 1000 == 0:
                print(f"  Progress: {i}/{len(comps_db.records.record)}")
                
            if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                buffer = record.record.record_buffer
                
                # Look for instruction sequences
                sequences = self.find_instruction_sequences(buffer)
                if sequences:
                    instruction_sequences.extend(sequences)
                    
                # Look for rung patterns
                rungs = self.find_rung_patterns(buffer)
                if rungs:
                    found_rungs.extend(rungs)
                    print(f"\n  Found {len(rungs)} rungs in record {i}")
                    for rung in rungs[:2]:  # Show first 2
                        print(f"    Rung: {rung[:100]}...")
        
        print(f"\n✅ Found {len(found_rungs)} potential rungs")
        print(f"✅ Found {len(instruction_sequences)} instruction sequences")
        
        # Save results
        if found_rungs:
            rungs_file = self.output_dir / "found_rungs.json"
            with open(rungs_file, 'w') as f:
                json.dump(found_rungs, f, indent=2)
            print(f"  Rungs saved to: {rungs_file}")
            
        if instruction_sequences:
            seq_file = self.output_dir / "instruction_sequences.json"
            with open(seq_file, 'w') as f:
                json.dump(instruction_sequences, f, indent=2)
            print(f"  Sequences saved to: {seq_file}")
    
    def find_instruction_sequences(self, buffer):
        """Find sequences of instructions that might form rungs"""
        sequences = []
        
        # Look for patterns like: XIC(...) OTE(...)
        for i in range(len(buffer) - 10):
            # Check if we have an instruction
            for inst in self.instructions:
                if buffer[i:i+len(inst)] == inst:
                    # Found instruction, look for parentheses
                    if i + len(inst) < len(buffer) and buffer[i + len(inst)] == ord('('):
                        # Find closing parenthesis
                        paren_start = i + len(inst) + 1
                        paren_count = 1
                        j = paren_start
                        
                        while j < len(buffer) and j < paren_start + 200:  # Max 200 bytes for operands
                            if buffer[j] == ord('('):
                                paren_count += 1
                            elif buffer[j] == ord(')'):
                                paren_count -= 1
                                if paren_count == 0:
                                    # Found complete instruction
                                    inst_text = buffer[i:j+1].decode('ascii', errors='ignore')
                                    
                                    # Look for next instruction or terminator
                                    next_start = j + 1
                                    while next_start < len(buffer) and buffer[next_start] in [ord(' '), ord('\t')]:
                                        next_start += 1
                                    
                                    # Check for rung terminator
                                    for term in self.rung_terminators:
                                        if buffer[next_start:next_start+len(term)] == term:
                                            # Found complete rung
                                            rung_text = buffer[i:next_start].decode('ascii', errors='ignore')
                                            sequences.append({
                                                'type': 'single_instruction',
                                                'text': rung_text,
                                                'position': i
                                            })
                                            break
                                    
                                    # Or check for next instruction
                                    for next_inst in self.instructions:
                                        if buffer[next_start:next_start+len(next_inst)] == next_inst:
                                            # Continue building sequence
                                            seq_end = self.find_sequence_end(buffer, next_start)
                                            if seq_end > next_start:
                                                seq_text = buffer[i:seq_end].decode('ascii', errors='ignore')
                                                sequences.append({
                                                    'type': 'multi_instruction',
                                                    'text': seq_text,
                                                    'position': i
                                                })
                                            break
                                    break
                            j += 1
                    break
        
        return sequences
    
    def find_sequence_end(self, buffer, start):
        """Find the end of an instruction sequence"""
        pos = start
        
        while pos < len(buffer):
            # Check for terminator
            for term in self.rung_terminators:
                if buffer[pos:pos+len(term)] == term:
                    return pos + len(term)
            
            # Check for newline or other delimiters
            if buffer[pos] in [ord('\n'), ord('\r'), 0]:
                return pos
                
            pos += 1
            
            # Don't go too far
            if pos - start > 1000:
                break
                
        return pos
    
    def find_rung_patterns(self, buffer):
        """Find patterns that look like complete rungs"""
        rungs = []
        
        # Look for patterns like "NOP();" which we found in SbRegion
        nop_pattern = b'NOP();'
        pos = 0
        while True:
            pos = buffer.find(nop_pattern, pos)
            if pos == -1:
                break
            rungs.append("NOP();")
            pos += len(nop_pattern)
        
        # Look for other common patterns
        # Pattern: instruction(operands);
        for inst in self.instructions:
            pattern = inst + b'('
            pos = 0
            while True:
                pos = buffer.find(pattern, pos)
                if pos == -1:
                    break
                    
                # Find the end of this instruction
                end_pos = buffer.find(b');', pos)
                if end_pos != -1 and end_pos - pos < 500:  # Reasonable distance
                    rung_bytes = buffer[pos:end_pos+2]
                    try:
                        rung_text = rung_bytes.decode('ascii')
                        # Validate it looks like a real rung
                        if self.validate_rung(rung_text):
                            rungs.append(rung_text)
                    except:
                        pass
                
                pos += len(pattern)
        
        return list(set(rungs))  # Remove duplicates
    
    def validate_rung(self, rung_text):
        """Validate that text looks like a real ladder logic rung"""
        # Must have at least one instruction
        has_instruction = any(inst.decode() in rung_text for inst in self.instructions)
        
        # Must have proper parentheses
        paren_count = rung_text.count('(') - rung_text.count(')')
        
        # Must end with semicolon
        ends_properly = rung_text.endswith(';')
        
        # Should not have weird characters
        valid_chars = all(
            c.isalnum() or c in '()[].,;:_- \t\n' 
            for c in rung_text
        )
        
        return has_instruction and paren_count == 0 and ends_properly and valid_chars
    
    def search_blocks_for_rungs(self):
        """Search previously extracted blocks for rungs"""
        print("\n📋 Step 3: Searching extracted blocks for rungs...")
        
        # Look in the blocks we extracted earlier
        block_files = [
            "acd_extracted_blocks/block_1.bin",
            "acd_extracted_blocks/block_2.bin", 
            "acd_extracted_blocks/block_3.bin",
            "acd_extracted_blocks/block_20.bin"
        ]
        
        all_rungs = []
        
        for block_file in block_files:
            if Path(block_file).exists():
                print(f"\n  Searching {block_file}...")
                with open(block_file, 'rb') as f:
                    data = f.read()
                
                # Search for instruction patterns
                sequences = self.find_instruction_sequences(data)
                rungs = self.find_rung_patterns(data)
                
                if sequences or rungs:
                    print(f"    Found {len(sequences)} sequences, {len(rungs)} rungs")
                    all_rungs.extend(rungs)
                    
                    # Show samples
                    if sequences:
                        print(f"    Sample sequence: {sequences[0]['text'][:100]}...")
                    if rungs and rungs[0] != "NOP();":
                        print(f"    Sample rung: {rungs[0][:100]}...")
        
        if all_rungs:
            # Save unique rungs
            unique_rungs = list(set(all_rungs))
            block_rungs_file = self.output_dir / "block_rungs.json"
            with open(block_rungs_file, 'w') as f:
                json.dump(unique_rungs, f, indent=2)
            print(f"\n✅ Found {len(unique_rungs)} unique rungs in blocks")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    finder = RungFinder(acd_file)
    finder.find_rungs()

if __name__ == "__main__":
    main() 