#!/usr/bin/env python3
"""
Decode proprietary ladder logic format from ACD binary data
"""

import os
import struct
import json
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract

class LadderLogicDecoder:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("ladder_logic_decode")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
        # Known ladder instructions
        self.instructions = {
            b'XIC': 'Examine If Closed',
            b'XIO': 'Examine If Open', 
            b'OTE': 'Output Energize',
            b'OTL': 'Output Latch',
            b'OTU': 'Output Unlatch',
            b'TON': 'Timer On Delay',
            b'TOF': 'Timer Off Delay',
            b'CTU': 'Count Up',
            b'CTD': 'Count Down',
            b'MOV': 'Move',
            b'ADD': 'Add',
            b'SUB': 'Subtract',
            b'MUL': 'Multiply',
            b'DIV': 'Divide',
            b'EQU': 'Equal',
            b'NEQ': 'Not Equal',
            b'LES': 'Less Than',
            b'GRT': 'Greater Than',
            b'JSR': 'Jump to Subroutine',
            b'RET': 'Return',
            b'AFI': 'Always False',
            b'NOP': 'No Operation'
        }
        
    def decode(self):
        """Main decoding process"""
        print(f"\n🔍 Decoding ladder logic from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Step 1: Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Analyze Comps.Dat where we found instructions
        self.analyze_comps_for_logic()
        
        # Look for patterns in binary data
        self.find_instruction_patterns()
        
    def analyze_comps_for_logic(self):
        """Analyze Comps.Dat records containing ladder instructions"""
        print("\n📋 Step 2: Analyzing Comps.Dat for ladder logic patterns...")
        
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        # Records where we previously found instructions
        interesting_records = []
        
        for i, record in enumerate(comps_db.records.record):
            if hasattr(record, 'record') and hasattr(record.record, 'record_buffer'):
                buffer = record.record.record_buffer
                
                # Check for any ladder instruction
                for inst_bytes, inst_name in self.instructions.items():
                    if inst_bytes in buffer:
                        interesting_records.append({
                            'index': i,
                            'instruction': inst_name,
                            'inst_bytes': inst_bytes.decode(),
                            'buffer_size': len(buffer)
                        })
                        
                        # Analyze the structure around the instruction
                        self.analyze_instruction_context(buffer, inst_bytes, i)
                        break
        
        print(f"\n✅ Found {len(interesting_records)} records with ladder instructions")
        
        # Save findings
        findings_file = self.output_dir / "instruction_records.json"
        with open(findings_file, 'w') as f:
            json.dump(interesting_records, f, indent=2)
        
    def analyze_instruction_context(self, buffer, instruction, record_idx):
        """Analyze the binary structure around a found instruction"""
        pos = buffer.find(instruction)
        if pos == -1:
            return
            
        # Get context around instruction
        context_start = max(0, pos - 100)
        context_end = min(len(buffer), pos + 100)
        context = buffer[context_start:context_end]
        
        # Only analyze first few occurrences of each instruction type
        inst_name = instruction.decode()
        sample_file = self.output_dir / f"sample_{inst_name}_{record_idx}.bin"
        
        if not sample_file.exists():
            with open(sample_file, 'wb') as f:
                f.write(context)
            
            print(f"\n  Analyzing {inst_name} at record {record_idx}:")
            
            # Look for patterns before instruction
            before_start = pos - context_start - 20
            if before_start >= 0:
                before_data = context[before_start:pos - context_start]
                self.analyze_bytes(before_data, "Before instruction")
            
            # Look for patterns after instruction  
            after_start = pos - context_start + len(instruction)
            after_data = context[after_start:after_start + 50]
            self.analyze_bytes(after_data, "After instruction")
            
            # Try to find operands
            self.find_operands(buffer, pos, instruction)
    
    def analyze_bytes(self, data, label):
        """Analyze byte patterns"""
        if len(data) < 4:
            return
            
        # Try different interpretations
        print(f"    {label}:")
        
        # Check for length prefix (common in binary formats)
        if len(data) >= 4:
            length_le = struct.unpack('<I', data[:4])[0]
            length_be = struct.unpack('>I', data[:4])[0]
            if 0 < length_le < 1000:
                print(f"      Possible length prefix (LE): {length_le}")
            if 0 < length_be < 1000:
                print(f"      Possible length prefix (BE): {length_be}")
        
        # Check for ASCII strings
        ascii_chars = []
        for b in data:
            if 32 <= b <= 126:
                ascii_chars.append(chr(b))
            else:
                if len(ascii_chars) > 3:
                    print(f"      ASCII: {''.join(ascii_chars)}")
                ascii_chars = []
        
        # Check for UTF-16 strings
        utf16_chars = []
        for i in range(0, len(data) - 1, 2):
            try:
                char = data[i:i+2].decode('utf-16le')
                if char.isprintable():
                    utf16_chars.append(char)
                else:
                    if len(utf16_chars) > 3:
                        print(f"      UTF-16: {''.join(utf16_chars)}")
                    utf16_chars = []
            except:
                utf16_chars = []
    
    def find_operands(self, buffer, inst_pos, instruction):
        """Try to find operands for the instruction"""
        inst_name = instruction.decode()
        
        # Different instructions have different operand patterns
        if inst_name in ['XIC', 'XIO', 'OTE', 'OTL', 'OTU']:
            # Bit instructions - expect a tag name
            self.find_tag_operand(buffer, inst_pos + len(instruction))
        elif inst_name in ['TON', 'TOF', 'CTU', 'CTD']:
            # Timer/Counter - expect structure with preset, accumulator
            self.find_timer_operands(buffer, inst_pos + len(instruction))
        elif inst_name in ['MOV', 'ADD', 'SUB', 'MUL', 'DIV']:
            # Math instructions - expect source and dest
            self.find_math_operands(buffer, inst_pos + len(instruction))
    
    def find_tag_operand(self, buffer, pos):
        """Find tag name operand"""
        # Tags might be stored as:
        # - Pascal string (length byte + string)
        # - Null-terminated string
        # - Fixed-length field
        
        # Try Pascal string
        if pos < len(buffer):
            length = buffer[pos]
            if 0 < length < 100 and pos + length + 1 <= len(buffer):
                tag_bytes = buffer[pos + 1:pos + 1 + length]
                try:
                    tag_name = tag_bytes.decode('ascii')
                    if all(c.isalnum() or c in '_.' for c in tag_name):
                        print(f"      Possible tag (Pascal): {tag_name}")
                except:
                    pass
        
        # Try UTF-16 with length prefix
        if pos + 2 < len(buffer):
            length = struct.unpack('<H', buffer[pos:pos+2])[0]
            if 0 < length < 200 and pos + 2 + length * 2 <= len(buffer):
                tag_bytes = buffer[pos + 2:pos + 2 + length * 2]
                try:
                    tag_name = tag_bytes.decode('utf-16le')
                    if all(c.isalnum() or c in '_.' for c in tag_name):
                        print(f"      Possible tag (UTF-16): {tag_name}")
                except:
                    pass
    
    def find_timer_operands(self, buffer, pos):
        """Find timer/counter operands"""
        # Timers typically have:
        # - Timer tag name
        # - Preset value (DINT)
        # - Accumulator value (DINT)
        
        if pos + 12 < len(buffer):
            # Try to read as structure
            try:
                # Skip potential tag reference
                preset_pos = pos + 4  # Guess offset
                if preset_pos + 8 <= len(buffer):
                    preset = struct.unpack('<I', buffer[preset_pos:preset_pos+4])[0]
                    accum = struct.unpack('<I', buffer[preset_pos+4:preset_pos+8])[0]
                    
                    if 0 <= preset <= 2147483647 and 0 <= accum <= 2147483647:
                        print(f"      Possible timer values - Preset: {preset}, Accum: {accum}")
            except:
                pass
    
    def find_math_operands(self, buffer, pos):
        """Find math instruction operands"""
        # Math instructions typically have:
        # - Source A (tag or constant)
        # - Source B (tag or constant)  
        # - Destination (tag)
        
        # Look for tag names or numeric values
        print(f"      Analyzing math operands at position {pos}")
        
    def find_instruction_patterns(self):
        """Find common patterns in instruction encoding"""
        print("\n📋 Step 3: Finding instruction encoding patterns...")
        
        # Load samples we saved
        sample_files = list(self.output_dir.glob("sample_*.bin"))
        
        if not sample_files:
            print("  No sample files found")
            return
            
        # Analyze each instruction type
        instruction_patterns = {}
        
        for sample_file in sample_files[:10]:  # Analyze first 10
            with open(sample_file, 'rb') as f:
                data = f.read()
                
            # Extract instruction name from filename
            parts = sample_file.stem.split('_')
            if len(parts) >= 2:
                inst_name = parts[1]
                
                if inst_name not in instruction_patterns:
                    instruction_patterns[inst_name] = []
                
                # Find the instruction in the sample
                inst_bytes = inst_name.encode()
                pos = data.find(inst_bytes)
                
                if pos != -1:
                    # Look for patterns
                    pattern = self.extract_pattern(data, pos, inst_bytes)
                    instruction_patterns[inst_name].append(pattern)
        
        # Report patterns
        print("\n📊 Instruction Encoding Patterns:")
        for inst_name, patterns in instruction_patterns.items():
            print(f"\n  {inst_name}:")
            if patterns:
                # Find common patterns
                common_before = self.find_common_bytes([p['before'] for p in patterns])
                common_after = self.find_common_bytes([p['after'] for p in patterns])
                
                if common_before:
                    print(f"    Common before: {common_before.hex()}")
                if common_after:
                    print(f"    Common after: {common_after.hex()}")
    
    def extract_pattern(self, data, pos, instruction):
        """Extract pattern around instruction"""
        before_start = max(0, pos - 10)
        before = data[before_start:pos]
        
        after_start = pos + len(instruction)
        after = data[after_start:min(len(data), after_start + 10)]
        
        return {
            'before': before,
            'after': after,
            'instruction': instruction.decode()
        }
    
    def find_common_bytes(self, byte_arrays):
        """Find common bytes in multiple byte arrays"""
        if not byte_arrays:
            return b''
            
        # Find minimum length
        min_len = min(len(ba) for ba in byte_arrays)
        if min_len == 0:
            return b''
            
        # Find common prefix
        common = []
        for i in range(min_len):
            bytes_at_pos = [ba[i] for ba in byte_arrays]
            if len(set(bytes_at_pos)) == 1:
                common.append(bytes_at_pos[0])
            else:
                break
                
        return bytes(common)

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    decoder = LadderLogicDecoder(acd_file)
    decoder.decode()

if __name__ == "__main__":
    main() 