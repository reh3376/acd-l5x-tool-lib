#!/usr/bin/env python3
"""
L5X to ACD Converter Prototype
Exploring the hybrid template approach for L5X → ACD conversion
"""

import os
import gzip
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json

class L5XToACDConverter:
    """
    Prototype converter from L5X to ACD using hybrid template approach
    """
    
    def __init__(self, l5x_file, template_acd=None):
        self.l5x_file = Path(l5x_file)
        self.template_acd = Path(template_acd) if template_acd else None
        self.output_dir = Path("l5x_to_acd_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # ACD structure components
        self.text_header = None
        self.binary_blocks = []
        self.databases = {}
        
    def convert(self):
        """Main conversion process"""
        print(f"\n🔄 L5X to ACD Converter Prototype")
        print("="*50)
        
        # Step 1: Parse L5X
        print("\n📋 Step 1: Parsing L5X file...")
        l5x_data = self.parse_l5x()
        
        # Step 2: Extract template structure (if available)
        if self.template_acd and self.template_acd.exists():
            print("\n📋 Step 2: Extracting template ACD structure...")
            self.extract_template_structure()
        else:
            print("\n📋 Step 2: No template provided, generating from scratch...")
            self.create_default_structure()
        
        # Step 3: Generate databases
        print("\n📋 Step 3: Generating internal databases...")
        self.generate_databases(l5x_data)
        
        # Step 4: Create ACD file
        print("\n📋 Step 4: Assembling ACD file...")
        output_file = self.create_acd_file()
        
        print(f"\n✅ Prototype ACD created: {output_file}")
        return output_file
    
    def parse_l5x(self):
        """Parse L5X XML file"""
        tree = ET.parse(self.l5x_file)
        root = tree.getroot()
        
        data = {
            'controller': {},
            'programs': [],
            'tags': [],
            'datatypes': [],
            'modules': [],
            'rungs': []
        }
        
        # Extract controller info
        controller = root.find('.//Controller')
        if controller is not None:
            data['controller'] = {
                'name': controller.get('Name'),
                'processor_type': controller.get('ProcessorType'),
                'major_rev': controller.get('MajorRev'),
                'minor_rev': controller.get('MinorRev')
            }
            print(f"  Controller: {data['controller']['name']}")
        
        # Extract programs
        for program in root.findall('.//Program'):
            prog_data = {
                'name': program.get('Name'),
                'routines': []
            }
            
            # Extract routines
            for routine in program.findall('.//Routine'):
                routine_data = {
                    'name': routine.get('Name'),
                    'type': routine.get('Type'),
                    'rungs': []
                }
                
                # Extract rungs
                for rung in routine.findall('.//Rung'):
                    text_elem = rung.find('Text')
                    if text_elem is not None:
                        routine_data['rungs'].append({
                            'number': rung.get('Number'),
                            'text': text_elem.text
                        })
                
                prog_data['routines'].append(routine_data)
            
            data['programs'].append(prog_data)
        
        print(f"  Programs: {len(data['programs'])}")
        
        # Extract tags
        for tag in root.findall('.//Tag'):
            data['tags'].append({
                'name': tag.get('Name'),
                'datatype': tag.get('DataType'),
                'description': tag.get('Description', '')
            })
        
        print(f"  Tags: {len(data['tags'])}")
        
        return data
    
    def extract_template_structure(self):
        """Extract structure from template ACD file"""
        with open(self.template_acd, 'rb') as f:
            # Read text header
            header_data = f.read(0x9307)  # Known header size
            self.text_header = header_data.decode('utf-8', errors='ignore')
            
            # Read binary section
            binary_data = f.read()
            
            # Find GZIP blocks
            pos = 0
            while pos < len(binary_data):
                # Look for GZIP magic number
                idx = binary_data.find(b'\x1f\x8b', pos)
                if idx == -1:
                    break
                
                # Try to decompress
                try:
                    # Find end of GZIP block (heuristic)
                    end_idx = binary_data.find(b'\x1f\x8b', idx + 2)
                    if end_idx == -1:
                        end_idx = len(binary_data)
                    
                    gzip_data = binary_data[idx:end_idx]
                    decompressed = gzip.decompress(gzip_data)
                    
                    self.binary_blocks.append({
                        'start': idx,
                        'size': end_idx - idx,
                        'compressed': gzip_data,
                        'decompressed': decompressed
                    })
                    
                    pos = end_idx
                except:
                    pos = idx + 2
        
        print(f"  Extracted {len(self.binary_blocks)} binary blocks from template")
    
    def create_default_structure(self):
        """Create default ACD structure without template"""
        # Create minimal text header
        self.text_header = self.generate_text_header()
        
        # Initialize empty databases
        self.databases = {
            'Comps.Dat': b'',
            'TagInfo.XML': b'',
            'SbRegion.Dat': b'',
            'Comments.Dat': b'',
            'QuickInfo.XML': b'',
            'XRefs.Dat': b''
        }
    
    def generate_text_header(self):
        """Generate ACD text header"""
        timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        
        header = f"""=~=~=~=~=~=~=~=~=~=~=~= PLC Battery Information =~=~=~=~=~=~=~=~=~=~=~=

 Battery Operated: false

=~=~=~=~=~=~=~=~=~=~=~= Project Information =~=~=~=~=~=~=~=~=~=~=~=

 Project Created: {timestamp}
 Last Modified: {timestamp}
 
 Created With: L5X to ACD Converter Prototype
 Conversion Date: {timestamp}

=~=~=~=~=~=~=~=~=~=~=~= Security Information =~=~=~=~=~=~=~=~=~=~=~=

 Security: No Protection

=~=~=~=~=~=~=~=~=~=~=~= Controller Information =~=~=~=~=~=~=~=~=~=~=~=
"""
        
        # Pad to expected size
        while len(header.encode('utf-8')) < 0x9307:
            header += " "
        
        return header[:0x9307]
    
    def generate_databases(self, l5x_data):
        """Generate internal database files from L5X data"""
        
        # Generate TagInfo.XML
        print("  Generating TagInfo.XML...")
        self.databases['TagInfo.XML'] = self.generate_taginfo_xml(l5x_data)
        
        # Generate QuickInfo.XML
        print("  Generating QuickInfo.XML...")
        self.databases['QuickInfo.XML'] = self.generate_quickinfo_xml(l5x_data)
        
        # Generate Comps.Dat (simplified)
        print("  Generating Comps.Dat...")
        self.databases['Comps.Dat'] = self.generate_comps_dat(l5x_data)
        
        # Generate SbRegion.Dat (ladder logic)
        print("  Generating SbRegion.Dat...")
        self.databases['SbRegion.Dat'] = self.generate_sbregion_dat(l5x_data)
    
    def generate_taginfo_xml(self, l5x_data):
        """Generate TagInfo.XML database"""
        root = ET.Element("TagInfo")
        
        # Add controller
        controller = ET.SubElement(root, "Controller")
        controller.set("Name", l5x_data['controller'].get('name', 'Controller'))
        
        # Add programs
        programs = ET.SubElement(root, "Programs")
        for prog in l5x_data['programs']:
            program = ET.SubElement(programs, "Program")
            program.set("Name", prog['name'])
            
            # Add routines
            for routine in prog.get('routines', []):
                rout = ET.SubElement(program, "Routine")
                rout.set("Name", routine['name'])
                rout.set("Type", routine['type'])
        
        # Add tags
        tags = ET.SubElement(root, "Tags")
        for tag in l5x_data['tags']:
            tag_elem = ET.SubElement(tags, "Tag")
            tag_elem.set("Name", tag['name'])
            tag_elem.set("DataType", tag['datatype'])
            
        return ET.tostring(root, encoding='utf-8')
    
    def generate_quickinfo_xml(self, l5x_data):
        """Generate QuickInfo.XML database"""
        controller = l5x_data['controller']
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<QuickInfo>
    <Controller Name="{controller.get('name', 'Controller')}"
                ProcessorType="{controller.get('processor_type', '1756-L85E')}"
                MajorRev="{controller.get('major_rev', '35')}"
                MinorRev="{controller.get('minor_rev', '1')}" />
    <ProgramCount>{len(l5x_data['programs'])}</ProgramCount>
    <TagCount>{len(l5x_data['tags'])}</TagCount>
</QuickInfo>"""
        
        return xml_content.encode('utf-8')
    
    def generate_comps_dat(self, l5x_data):
        """Generate simplified Comps.Dat binary database"""
        # This is a highly simplified version
        # Real implementation would need proper binary format
        
        data = bytearray()
        
        # Add header (simplified)
        data.extend(b'COMPS\x00\x00\x00')
        
        # Add version
        data.extend(struct.pack('<I', 1))  # Version 1
        
        # Add record count
        record_count = len(l5x_data['programs']) + len(l5x_data['tags'])
        data.extend(struct.pack('<I', record_count))
        
        # Add simplified records
        object_id = 1
        
        # Add program records
        for prog in l5x_data['programs']:
            # Record header
            data.extend(struct.pack('<I', object_id))  # object_id
            data.extend(struct.pack('<I', 0))         # parent_id
            data.extend(struct.pack('<I', 256))       # record_type (program)
            
            # Name (UTF-16LE)
            name_bytes = prog['name'].encode('utf-16le')
            data.extend(struct.pack('<H', len(name_bytes)))
            data.extend(name_bytes)
            
            object_id += 1
        
        return bytes(data)
    
    def generate_sbregion_dat(self, l5x_data):
        """Generate SbRegion.Dat with ladder logic"""
        data = bytearray()
        
        # Add header
        data.extend(b'SBREGION\x00')
        
        # Add rungs
        for prog in l5x_data['programs']:
            for routine in prog.get('routines', []):
                for rung in routine.get('rungs', []):
                    if rung.get('text'):
                        # Encode rung text as UTF-16LE
                        rung_bytes = rung['text'].encode('utf-16le')
                        
                        # Add length prefix
                        data.extend(struct.pack('<I', len(rung_bytes)))
                        data.extend(rung_bytes)
        
        return bytes(data)
    
    def create_acd_file(self):
        """Assemble final ACD file"""
        output_file = self.output_dir / f"{self.l5x_file.stem}.ACD"
        
        with open(output_file, 'wb') as f:
            # Write text header
            if isinstance(self.text_header, str):
                f.write(self.text_header.encode('utf-8'))
            else:
                f.write(self.text_header)
            
            # Write binary section marker
            f.write(b'\x00' * 16)  # Separator
            
            # Compress and write databases
            for db_name, db_data in self.databases.items():
                if db_data:
                    compressed = gzip.compress(db_data)
                    
                    # Write database header
                    name_bytes = db_name.encode('utf-8')
                    f.write(struct.pack('<I', len(name_bytes)))
                    f.write(name_bytes)
                    f.write(struct.pack('<I', len(compressed)))
                    
                    # Write compressed data
                    f.write(compressed)
        
        # Calculate file size
        file_size = output_file.stat().st_size
        print(f"  Output file size: {file_size:,} bytes")
        
        return output_file
    
    def validate_conversion(self):
        """Validate the generated ACD file"""
        print("\n📋 Validation:")
        
        # Check file exists and has content
        if self.output_file.exists():
            size = self.output_file.stat().st_size
            print(f"  ✓ File created: {size:,} bytes")
            
            # Check header
            with open(self.output_file, 'rb') as f:
                header = f.read(100).decode('utf-8', errors='ignore')
                if 'PLC Battery Information' in header:
                    print("  ✓ Valid header detected")
                else:
                    print("  ✗ Header validation failed")
        else:
            print("  ✗ Output file not created")

def main():
    """Test the prototype converter"""
    
    # Use our generated L5X file
    l5x_file = "FINAL_COMPLETE_L5X/ULTIMATE_COMPLETE_PLC100_Mashing.L5X"
    
    # Check if we have a template ACD
    template_acd = "docs/exports/PLC100_Mashing.ACD"
    
    if not Path(l5x_file).exists():
        print(f"❌ L5X file not found: {l5x_file}")
        return
    
    # Create converter
    converter = L5XToACDConverter(l5x_file, template_acd)
    
    # Run conversion
    output_file = converter.convert()
    
    # Validate
    converter.output_file = output_file
    converter.validate_conversion()
    
    print("\n⚠️  WARNING: This is a PROTOTYPE")
    print("The generated ACD file is NOT compatible with Studio 5000")
    print("This demonstrates the concept and challenges of L5X → ACD conversion")
    
    # Save findings
    findings = {
        'approach': 'Hybrid Template',
        'status': 'Prototype Only',
        'challenges': [
            'Proprietary binary format',
            'Unknown checksums/validation',
            'Complex database structures',
            'Object ID generation',
            'Binary record formats'
        ],
        'recommendations': [
            'Use Studio 5000 for production conversions',
            'Continue reverse engineering for open source solution',
            'Consider contributing to hutcheb/acd project'
        ]
    }
    
    findings_file = converter.output_dir / "conversion_findings.json"
    with open(findings_file, 'w') as f:
        json.dump(findings, f, indent=2)
    
    print(f"\n📄 Findings saved to: {findings_file}")

if __name__ == "__main__":
    main() 