#!/usr/bin/env python3
"""
Parse extracted ACD database blocks and generate L5X file
"""

import struct
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from datetime import datetime

class ACDDatabaseParser:
    def __init__(self, block_file):
        self.block_file = block_file
        self.data = None
        self.project_name = None
        self.programs = []
        self.routines = []
        self.tags = []
        self.data_types = []
        
    def load_block(self):
        """Load the decompressed block data"""
        with open(self.block_file, 'rb') as f:
            self.data = f.read()
        print(f"📊 Loaded {len(self.data)} bytes")
        
    def find_strings(self, min_length=4):
        """Extract all readable strings from binary data"""
        strings = []
        current = []
        
        for byte in self.data:
            if 0x20 <= byte <= 0x7E:  # Printable ASCII
                current.append(chr(byte))
            else:
                if len(current) >= min_length:
                    strings.append(''.join(current))
                current = []
        
        return strings
    
    def parse_structure(self):
        """Parse the database structure"""
        print("\n🔍 Parsing database structure...")
        
        # Find all strings
        strings = self.find_strings()
        
        # Look for project name
        for s in strings:
            if 'PLC100' in s and 'Mashing' in s:
                self.project_name = s
                print(f"✅ Found project name: {self.project_name}")
                break
        
        # Look for programs, routines, tags
        for s in strings:
            if 'Program' in s and len(s) < 50:
                self.programs.append(s)
            elif 'Routine' in s and len(s) < 50:
                self.routines.append(s)
            elif 'Tag' in s and len(s) < 50:
                self.tags.append(s)
            elif 'DataType' in s and len(s) < 50:
                self.data_types.append(s)
        
        # Find binary patterns for structured data
        self.find_structured_data()
        
    def find_structured_data(self):
        """Look for structured binary patterns"""
        # Look for "Comps" database header
        comps_offset = self.data.find(b'Comps')
        if comps_offset > 0:
            print(f"📍 Found 'Comps' database at offset: 0x{comps_offset:x}")
            self.parse_comps_database(comps_offset)
    
    def parse_comps_database(self, offset):
        """Parse the Comps database structure"""
        # The Comps database contains component information
        # Structure appears to be:
        # - Header with field names (CompUId, CompName, etc.)
        # - Index data
        # - Actual component records
        
        # Extract field names after "Comps"
        field_start = offset + 6  # Skip "Comps\0"
        fields = []
        
        pos = field_start
        while pos < len(self.data) - 100:
            # Look for null-terminated strings
            end = self.data.find(b'\x00', pos)
            if end == -1 or end - pos > 50:
                break
            
            field = self.data[pos:end].decode('utf-8', errors='ignore')
            if field and all(c.isalnum() or c in '_' for c in field):
                fields.append(field)
                print(f"   Found field: {field}")
            
            pos = end + 1
            
            if len(fields) > 10:  # Reasonable limit
                break
    
    def generate_l5x(self, output_file):
        """Generate L5X file from parsed data"""
        print("\n💾 Generating L5X file...")
        
        # Create root element
        root = ET.Element("RSLogix5000Content", {
            "SchemaRevision": "1.0",
            "SoftwareRevision": "34.01",
            "TargetName": self.project_name or "PLC100_Mashing",
            "TargetType": "Controller",
            "ContainsContext": "true",
            "Owner": "Extracted from ACD",
            "ExportDate": datetime.now().strftime("%a %b %d %Y %H:%M:%S")
        })
        
        # Create Controller
        controller = ET.SubElement(root, "Controller", {
            "Use": "Target",
            "Name": self.project_name or "PLC100_Mashing",
            "ProcessorType": "1756-L85E",
            "MajorRev": "34",
            "MinorRev": "01",
            "TimeSlice": "20",
            "ShareUnusedTimeSlice": "1",
            "ProjectCreationDate": "Mon Jul 24 2025",
            "LastModifiedDate": datetime.now().strftime("%a %b %d %Y"),
            "SFCExecutionControl": "CurrentActive",
            "SFCRestartPosition": "MostRecent",
            "SFCLastScan": "DontScan",
            "ProjectSN": "16#0000_0000",
            "MatchProjectToController": "false",
            "CanUseRPIFromProducer": "false",
            "InhibitAutomaticFirmwareUpdate": "0",
            "PassThroughConfiguration": "EnabledWithAppend",
            "DownloadProjectDocumentationAndExtendedProperties": "true",
            "DownloadProjectCustomProperties": "true",
            "ReportMinorOverflow": "false"
        })
        
        # Add basic structure
        ET.SubElement(controller, "RedundancyInfo", {
            "Enabled": "false",
            "DataTablePadPercentage": "50",
            "AuxDataTablePadPercentage": "50",
            "KeepTestEditsOnSwitchOver": "false"
        })
        
        ET.SubElement(controller, "Security", {
            "Code": "0",
            "ChangesToDetect": "16#ffff_ffff_ffff_ffff"
        })
        
        ET.SubElement(controller, "SafetyInfo", {"SafetyEnabled": "false"})
        ET.SubElement(controller, "DataTypes")
        ET.SubElement(controller, "Modules")
        ET.SubElement(controller, "AddOnInstructionDefinitions")
        
        # Add Tags if found
        tags_elem = ET.SubElement(controller, "Tags")
        if self.tags:
            for tag_name in self.tags[:10]:  # Add first 10 tags
                ET.SubElement(tags_elem, "Tag", {
                    "Name": tag_name.replace("Tag", "").strip(),
                    "TagType": "Base",
                    "DataType": "DINT",
                    "Radix": "Decimal",
                    "Constant": "false",
                    "ExternalAccess": "Read/Write"
                })
        
        # Add Programs
        programs_elem = ET.SubElement(controller, "Programs")
        program = ET.SubElement(programs_elem, "Program", {
            "Name": "MainProgram",
            "TestEdits": "false",
            "MainRoutineName": "MainRoutine",
            "Disabled": "false",
            "UseAsFolder": "false"
        })
        
        ET.SubElement(program, "Tags")
        
        routines_elem = ET.SubElement(program, "Routines")
        routine = ET.SubElement(routines_elem, "Routine", {
            "Name": "MainRoutine",
            "Type": "RLL"
        })
        
        rll_content = ET.SubElement(routine, "RLLContent")
        
        # Add a rung with extracted information
        rung = ET.SubElement(rll_content, "Rung", {
            "Number": "0",
            "Type": "N"
        })
        comment = ET.SubElement(rung, "Comment")
        comment.text = f"Extracted from ACD file: {self.project_name or 'PLC100_Mashing.ACD'}"
        
        if self.programs:
            rung2 = ET.SubElement(rll_content, "Rung", {"Number": "1", "Type": "N"})
            comment2 = ET.SubElement(rung2, "Comment")
            comment2.text = f"Found programs: {', '.join(self.programs[:5])}"
        
        # Add Tasks
        tasks_elem = ET.SubElement(controller, "Tasks")
        task = ET.SubElement(tasks_elem, "Task", {
            "Name": "MainTask",
            "Type": "CONTINUOUS",
            "Priority": "10",
            "Watchdog": "500",
            "DisableUpdateOutputs": "false",
            "InhibitTask": "false"
        })
        
        scheduled = ET.SubElement(task, "ScheduledPrograms")
        ET.SubElement(scheduled, "ScheduledProgram", {"Name": "MainProgram"})
        
        # Additional elements
        ET.SubElement(controller, "CommissioningStatus", {"StatusFlags": "0"})
        ET.SubElement(controller, "TimeSynchronize", {
            "Priority1": "128",
            "Priority2": "128",
            "PTPEnable": "false"
        })
        
        # Format and save
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Clean up blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        pretty_xml = '\n'.join(lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"✅ L5X file saved: {output_file}")

def main():
    print("🚀 ACD Database Parser v1.0")
    print("===========================\n")
    
    # Parse the largest extracted block
    block_file = "extracted_blocks/block_003_offset_0x10c95.bin"
    
    if not os.path.exists(block_file):
        print(f"❌ Block file not found: {block_file}")
        return 1
    
    parser = ACDDatabaseParser(block_file)
    parser.load_block()
    parser.parse_structure()
    
    # Generate enhanced L5X
    output_file = "/Users/reh3376/repos/acd-l5x-tool-lib/docs/l5x-files/PLC100_Mashing_Enhanced.L5X"
    parser.generate_l5x(output_file)
    
    print("\n📊 Summary:")
    print(f"   Project: {parser.project_name}")
    print(f"   Programs found: {len(parser.programs)}")
    print(f"   Routines found: {len(parser.routines)}")
    print(f"   Tags found: {len(parser.tags)}")
    print(f"   Data types found: {len(parser.data_types)}")
    
    return 0

if __name__ == "__main__":
    exit(main()) 