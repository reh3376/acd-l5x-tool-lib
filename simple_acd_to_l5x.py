#!/usr/bin/env python3
"""
Simple ACD to L5X Converter
Works around hutcheb/acd limitations by directly extracting and parsing databases
"""

import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from datetime import datetime
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.record.comps import CompsRecord
import json

class SimpleACDtoL5XConverter:
    def __init__(self, acd_file_path):
        self.acd_file = Path(acd_file_path)
        self.output_dir = Path("simple_l5x_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.db_dir = self.output_dir / "databases"
        self.controller_info = None
        self.programs = {}
        self.tags = []
        self.datatypes = []
        self.modules = []
        
    def convert(self):
        """Main conversion process"""
        print(f"\n🔄 Converting {self.acd_file.name} to L5X...")
        
        # Step 1: Extract databases
        if not self.extract_databases():
            return False
        
        # Step 2: Parse TagInfo.XML for structure
        if not self.parse_taginfo_xml():
            return False
        
        # Step 3: Parse QuickInfo.XML for controller details
        self.parse_quickinfo_xml()
        
        # Step 4: Process Comps database for component details
        self.process_comps_database()
        
        # Step 5: Generate L5X file
        if self.generate_l5x():
            print("\n✅ Conversion successful!")
            return True
        
        return False
    
    def extract_databases(self):
        """Extract ACD database files"""
        print("\n📋 Step 1: Extracting ACD databases...")
        try:
            ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
            print("✅ Databases extracted")
            return True
        except Exception as e:
            print(f"❌ Error extracting databases: {e}")
            return False
    
    def parse_taginfo_xml(self):
        """Parse TagInfo.XML for complete structure"""
        print("\n📋 Step 2: Parsing TagInfo.XML...")
        taginfo_path = self.db_dir / "TagInfo.XML"
        
        if not taginfo_path.exists():
            print("❌ TagInfo.XML not found")
            return False
        
        try:
            with open(taginfo_path, 'r', encoding='utf-16', errors='ignore') as f:
                content = f.read()
            
            root = ET.fromstring(content)
            
            # Get controller name
            self.controller_info = {
                'name': root.get('Name', 'Unknown'),
                'processor_type': '1756-L85E',  # Default, will update from QuickInfo
                'major_rev': '35',
                'minor_rev': '0'
            }
            
            # Extract Programs with routines
            for program in root.findall('.//Program'):
                prog_name = program.get('Name')
                prog_info = {
                    'type': program.get('Type', 'Normal'),
                    'description': program.get('Description', ''),
                    'routines': {},
                    'tags': []
                }
                
                # Get routines
                for routine in program.findall('.//Routine'):
                    routine_name = routine.get('Name')
                    prog_info['routines'][routine_name] = {
                        'type': routine.get('Type', 'RLL'),
                        'rungs': []  # Will populate from Comps if possible
                    }
                
                # Get program-scoped tags
                for tag in program.findall('.//Tag'):
                    prog_info['tags'].append({
                        'name': tag.get('Name'),
                        'datatype': tag.get('DataType'),
                        'value': tag.get('Value', '')
                    })
                
                self.programs[prog_name] = prog_info
            
            # Extract controller-scoped tags
            for tag in root.findall('./Tags/Tag'):
                self.tags.append({
                    'name': tag.get('Name'),
                    'datatype': tag.get('DataType'),
                    'description': tag.get('Description', ''),
                    'value': tag.get('Value', '')
                })
            
            # Extract data types
            for dt in root.findall('.//DataType'):
                dt_info = {
                    'name': dt.get('Name'),
                    'family': dt.get('Family', 'NoFamily'),
                    'size': dt.get('Size', '0'),
                    'members': []
                }
                
                # Get members
                for member in dt.findall('.//Member'):
                    dt_info['members'].append({
                        'name': member.get('Name'),
                        'datatype': member.get('DataType'),
                        'dimension': member.get('Dimension', '0'),
                        'radix': member.get('Radix', 'Decimal')
                    })
                
                self.datatypes.append(dt_info)
            
            print(f"✅ Found {len(self.programs)} programs, {len(self.tags)} tags, {len(self.datatypes)} data types")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing TagInfo.XML: {e}")
            return False
    
    def parse_quickinfo_xml(self):
        """Parse QuickInfo.XML for controller details"""
        print("\n📋 Step 3: Parsing QuickInfo.XML...")
        quickinfo_path = self.db_dir / "QuickInfo.XML"
        
        if not quickinfo_path.exists():
            print("⚠️  QuickInfo.XML not found, using defaults")
            return
        
        try:
            with open(quickinfo_path, 'r', encoding='utf-16', errors='ignore') as f:
                content = f.read()
            
            root = ET.fromstring(content)
            
            # Get device identity
            device = root.find('.//DeviceIdentity')
            if device is not None:
                self.controller_info['major_rev'] = device.get('MajorRevision', '35')
                self.controller_info['minor_rev'] = device.get('MinorRevision', '0')
                
                # Infer processor type from product code
                product_code = device.get('ProductCode', '')
                if product_code == '213':
                    self.controller_info['processor_type'] = '1756-L85E'
                elif product_code == '212':
                    self.controller_info['processor_type'] = '1756-L84E'
            
            print(f"✅ Controller: {self.controller_info['processor_type']} v{self.controller_info['major_rev']}.{self.controller_info['minor_rev']}")
            
        except Exception as e:
            print(f"⚠️  Warning parsing QuickInfo.XML: {e}")
    
    def process_comps_database(self):
        """Process Comps database for additional details"""
        print("\n📋 Step 4: Processing Comps database...")
        
        try:
            # Create temporary SQLite database
            temp_db = self.output_dir / "temp_comps.db"
            if temp_db.exists():
                os.remove(temp_db)
            
            db = sqlite3.connect(str(temp_db))
            cur = db.cursor()
            
            # Create minimal schema for CompsRecord
            cur.execute("""
                CREATE TABLE comps(
                    object_id int, 
                    parent_id int, 
                    comp_name text, 
                    seq_number int, 
                    record_type int, 
                    record BLOB NOT NULL
                )
            """)
            
            # Read Comps.Dat
            comps_file = self.db_dir / "Comps.Dat"
            comps_db = DbExtract(str(comps_file)).read()
            
            print(f"  Processing {len(comps_db.records.record)} records...")
            
            # Process records
            component_count = 0
            for record in comps_db.records.record[:1000]:  # Process first 1000 for speed
                try:
                    CompsRecord(cur, record)
                    component_count += 1
                except Exception:
                    # Skip records that fail
                    pass
            
            db.commit()
            
            # Query for useful information
            cur.execute("SELECT DISTINCT comp_name FROM comps WHERE comp_name IS NOT NULL LIMIT 20")
            comp_names = [row[0] for row in cur.fetchall()]
            
            print(f"✅ Processed {component_count} component records")
            if comp_names:
                print(f"   Sample components: {', '.join(comp_names[:5])}")
            
            db.close()
            
        except Exception as e:
            print(f"⚠️  Warning processing Comps: {e}")
    
    def generate_l5x(self):
        """Generate L5X XML file"""
        print("\n📋 Step 5: Generating L5X file...")
        
        try:
            # Create root element
            root = ET.Element('RSLogix5000Content')
            root.set('SchemaRevision', '1.0')
            root.set('SoftwareRevision', f"{self.controller_info['major_rev']}.{self.controller_info['minor_rev'].zfill(2)}")
            root.set('TargetName', self.controller_info['name'])
            root.set('TargetType', 'Controller')
            root.set('ContainsContext', 'false')
            root.set('ExportDate', datetime.now().strftime('%a %b %d %H:%M:%S %Y'))
            root.set('ExportOptions', 'References NoRawData L5KData DecoratedData Context Dependencies ForceProtectedEncoding')
            
            # Add Controller element
            controller = ET.SubElement(root, 'Controller')
            controller.set('Name', self.controller_info['name'])
            controller.set('ProcessorType', self.controller_info['processor_type'])
            controller.set('MajorRev', self.controller_info['major_rev'])
            controller.set('MinorRev', self.controller_info['minor_rev'])
            controller.set('TimeSlice', '20')
            controller.set('ShareUnusedTimeSlice', 'true')
            controller.set('ProjectCreationDate', datetime.now().strftime('%a %b %d %H:%M:%S %Y'))
            controller.set('LastModifiedDate', datetime.now().strftime('%a %b %d %H:%M:%S %Y'))
            controller.set('SFCExecutionControl', 'CurrentActive')
            controller.set('SFCRestartPosition', 'MostRecent')
            controller.set('SFCLastScan', 'DontRestart')
            controller.set('ProjectSN', '16#0000_0000')
            controller.set('MatchProjectToController', 'false')
            controller.set('CanUseRPIFromProducer', 'false')
            controller.set('InhibitAutomaticFirmwareUpdate', '0')
            controller.set('PassThroughConfiguration', 'EnabledWithAppend')
            controller.set('DownloadProjectDocumentationAndExtendedProperties', 'true')
            controller.set('DownloadProjectCustomProperties', 'true')
            controller.set('ReportMinorOverflow', 'false')
            
            # Add DataTypes
            if self.datatypes:
                datatypes_elem = ET.SubElement(controller, 'DataTypes')
                for dt in self.datatypes[:50]:  # Limit for demo
                    dt_elem = ET.SubElement(datatypes_elem, 'DataType')
                    dt_elem.set('Name', dt['name'])
                    dt_elem.set('Family', dt['family'])
                    dt_elem.set('Class', 'User')
                    
                    if dt['members']:
                        members_elem = ET.SubElement(dt_elem, 'Members')
                        for member in dt['members']:
                            m_elem = ET.SubElement(members_elem, 'Member')
                            m_elem.set('Name', member['name'])
                            m_elem.set('DataType', member['datatype'])
                            if member['dimension'] != '0':
                                m_elem.set('Dimension', member['dimension'])
                            m_elem.set('Radix', member['radix'])
                            m_elem.set('Hidden', 'false')
                            m_elem.set('ExternalAccess', 'Read/Write')
            
            # Add Tags
            if self.tags:
                tags_elem = ET.SubElement(controller, 'Tags')
                for tag in self.tags[:100]:  # Limit for demo
                    tag_elem = ET.SubElement(tags_elem, 'Tag')
                    tag_elem.set('Name', tag['name'])
                    tag_elem.set('TagType', 'Base')
                    tag_elem.set('DataType', tag['datatype'])
                    tag_elem.set('Radix', 'Decimal')
                    tag_elem.set('Constant', 'false')
                    tag_elem.set('ExternalAccess', 'Read/Write')
                    
                    if tag['description']:
                        desc_elem = ET.SubElement(tag_elem, 'Description')
                        desc_elem.text = ET.CDATA(tag['description'])
            
            # Add Programs
            if self.programs:
                programs_elem = ET.SubElement(controller, 'Programs')
                for prog_name, prog_info in list(self.programs.items())[:10]:  # Limit for demo
                    prog_elem = ET.SubElement(programs_elem, 'Program')
                    prog_elem.set('Name', prog_name)
                    prog_elem.set('TestEdits', 'false')
                    prog_elem.set('MainRoutineName', 'Main' if 'Main' in prog_info['routines'] else '')
                    prog_elem.set('Disabled', 'false')
                    prog_elem.set('UseAsFolder', 'false')
                    
                    if prog_info['description']:
                        desc_elem = ET.SubElement(prog_elem, 'Description')
                        desc_elem.text = ET.CDATA(prog_info['description'])
                    
                    # Add program tags
                    if prog_info['tags']:
                        tags_elem = ET.SubElement(prog_elem, 'Tags')
                        for tag in prog_info['tags'][:20]:
                            tag_elem = ET.SubElement(tags_elem, 'Tag')
                            tag_elem.set('Name', tag['name'])
                            tag_elem.set('TagType', 'Base')
                            tag_elem.set('DataType', tag['datatype'])
                            tag_elem.set('Radix', 'Decimal')
                            tag_elem.set('Constant', 'false')
                            tag_elem.set('ExternalAccess', 'Read/Write')
                    
                    # Add routines
                    if prog_info['routines']:
                        routines_elem = ET.SubElement(prog_elem, 'Routines')
                        for routine_name, routine_info in prog_info['routines'].items():
                            routine_elem = ET.SubElement(routines_elem, 'Routine')
                            routine_elem.set('Name', routine_name)
                            routine_elem.set('Type', routine_info['type'])
                            
                            # Add empty RLL content
                            if routine_info['type'] == 'RLL':
                                rll_elem = ET.SubElement(routine_elem, 'RLLContent')
                                # Add a sample rung
                                rung_elem = ET.SubElement(rll_elem, 'Rung')
                                rung_elem.set('Number', '0')
                                rung_elem.set('Type', 'N')
                                text_elem = ET.SubElement(rung_elem, 'Text')
                                text_elem.text = ET.CDATA('NOP();')
            
            # Save to file
            output_file = self.output_dir / f"{self.controller_info['name']}.L5X"
            
            # Convert to string with pretty printing
            xml_str = ET.tostring(root, encoding='utf-8', method='xml')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent='  ', encoding='UTF-8')
            
            # Write to file
            with open(output_file, 'wb') as f:
                f.write(pretty_xml)
            
            print(f"✅ L5X file saved to: {output_file}")
            
            # Generate summary report
            self.generate_report()
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating L5X: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_report(self):
        """Generate conversion summary report"""
        report = {
            'conversion_date': datetime.now().isoformat(),
            'source_file': str(self.acd_file),
            'controller': self.controller_info,
            'statistics': {
                'programs': len(self.programs),
                'total_routines': sum(len(p['routines']) for p in self.programs.values()),
                'controller_tags': len(self.tags),
                'data_types': len(self.datatypes)
            },
            'programs': list(self.programs.keys())
        }
        
        report_file = self.output_dir / "conversion_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Conversion Summary:")
        print(f"  Controller: {report['controller']['name']}")
        print(f"  Processor: {report['controller']['processor_type']}")
        print(f"  Programs: {report['statistics']['programs']}")
        print(f"  Routines: {report['statistics']['total_routines']}")
        print(f"  Tags: {report['statistics']['controller_tags']}")
        print(f"  Data Types: {report['statistics']['data_types']}")
        print(f"\n  Report saved to: {report_file}")

def main():
    if len(sys.argv) < 2:
        acd_file = "docs/exports/PLC100_Mashing.ACD"
        print(f"No file specified, using default: {acd_file}")
    else:
        acd_file = sys.argv[1]
    
    if not Path(acd_file).exists():
        print(f"❌ Error: File not found: {acd_file}")
        sys.exit(1)
    
    converter = SimpleACDtoL5XConverter(acd_file)
    success = converter.convert()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 