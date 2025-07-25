#!/usr/bin/env python3
"""
Extract Module I/O configurations from ACD file
"""

import os
import sqlite3
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from acd.api import ExtractAcdDatabase
from acd.database.dbextract import DbExtract
from acd.record.comps import CompsRecord

class ModuleIOExtractor:
    def __init__(self, acd_file):
        self.acd_file = Path(acd_file)
        self.output_dir = Path("module_io_extracted")
        self.output_dir.mkdir(exist_ok=True)
        self.db_dir = self.output_dir / "databases"
        
        # Known module types in Rockwell systems
        self.module_types = {
            4: 'Module',
            16: 'Ethernet Module',
            32: 'DeviceNet Module', 
            64: 'ControlNet Module',
            128: 'Serial Module'
        }
        
    def extract(self):
        """Extract module configurations"""
        print(f"\n🔍 Extracting Module I/O configurations from {self.acd_file.name}")
        print("="*60)
        
        # Extract databases
        print("\n📋 Step 1: Extracting databases...")
        ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
        
        # Parse modules from multiple sources
        modules = {}
        
        # From Comps.Dat
        print("\n📋 Step 2: Parsing modules from Comps.Dat...")
        comps_modules = self.extract_comps_modules()
        modules.update(comps_modules)
        
        # From TagInfo.XML
        print("\n📋 Step 3: Parsing modules from TagInfo.XML...")
        taginfo_modules = self.extract_taginfo_modules()
        modules.update(taginfo_modules)
        
        # From QuickInfo.XML
        print("\n📋 Step 4: Parsing modules from QuickInfo.XML...")
        quickinfo_modules = self.extract_quickinfo_modules()
        modules.update(quickinfo_modules)
        
        # Merge and analyze
        print("\n📋 Step 5: Analyzing module configurations...")
        self.analyze_modules(modules)
        
        # Generate L5X module sections
        print("\n📋 Step 6: Generating L5X module configurations...")
        self.generate_l5x_modules(modules)
        
    def extract_comps_modules(self):
        """Extract modules from Comps.Dat"""
        modules = {}
        
        # Create SQLite database for queries
        db_file = self.output_dir / "modules.db"
        if db_file.exists():
            os.remove(db_file)
            
        db = sqlite3.connect(str(db_file))
        cur = db.cursor()
        
        # Create table
        cur.execute("""
            CREATE TABLE comps(
                object_id int PRIMARY KEY,
                parent_id int,
                comp_name text,
                seq_number int,
                record_type int,
                record BLOB NOT NULL
            )
        """)
        
        # Load Comps.Dat
        comps_file = self.db_dir / "Comps.Dat"
        comps_db = DbExtract(str(comps_file)).read()
        
        print(f"  Processing {len(comps_db.records.record)} records...")
        
        for record in comps_db.records.record:
            try:
                CompsRecord(cur, record)
            except:
                pass
                
        db.commit()
        
        # Query for modules (record_type = 4)
        cur.execute("SELECT object_id, comp_name, parent_id FROM comps WHERE record_type = 4")
        module_records = cur.fetchall()
        
        print(f"  Found {len(module_records)} module records")
        
        for obj_id, name, parent_id in module_records:
            if name:  # Skip empty names
                modules[name] = {
                    'object_id': obj_id,
                    'name': name,
                    'parent_id': parent_id,
                    'type': 'Module',
                    'source': 'Comps.Dat',
                    'catalog_number': None,
                    'vendor': None,
                    'product_type': None,
                    'product_code': None,
                    'major_rev': None,
                    'minor_rev': None,
                    'parent_module': None,
                    'parent_port': None,
                    'slot': None,
                    'configuration': None
                }
        
        # Try to find additional module information in raw records
        cur.execute("SELECT object_id, comp_name, record FROM comps WHERE record_type = 4")
        for obj_id, name, record_blob in cur.fetchall():
            if name and name in modules:
                # Try to extract configuration from binary data
                config_data = self.parse_module_record(record_blob)
                if config_data:
                    modules[name].update(config_data)
        
        db.close()
        return modules
    
    def parse_module_record(self, record_blob):
        """Parse module configuration from binary record"""
        try:
            # Look for common module configuration patterns
            config = {}
            
            # Try to find catalog number (often ASCII strings)
            text_parts = []
            for i in range(len(record_blob) - 10):
                # Look for printable ASCII sequences
                seq = []
                for j in range(i, min(i + 50, len(record_blob))):
                    if 32 <= record_blob[j] <= 126:
                        seq.append(chr(record_blob[j]))
                    else:
                        break
                
                if len(seq) > 4:
                    text = ''.join(seq)
                    # Check if it looks like a catalog number
                    if any(pattern in text for pattern in ['1756', '1769', '1734', '1794', 'ENBT', 'IF16']):
                        config['catalog_number'] = text
                        break
            
            # Look for vendor ID (Rockwell = 1)
            for i in range(0, len(record_blob) - 4, 4):
                try:
                    value = int.from_bytes(record_blob[i:i+4], 'little')
                    if value == 1:  # Rockwell vendor ID
                        config['vendor'] = 'Rockwell Automation'
                        break
                except:
                    pass
            
            return config if config else None
            
        except Exception as e:
            return None
    
    def extract_taginfo_modules(self):
        """Extract module info from TagInfo.XML"""
        modules = {}
        
        taginfo_file = self.db_dir / "TagInfo.XML"
        if not taginfo_file.exists():
            print("  TagInfo.XML not found")
            return modules
            
        try:
            tree = ET.parse(taginfo_file)
            root = tree.getroot()
            
            # Look for module-related tags
            module_count = 0
            for tag in root.findall('.//Tag'):
                name = tag.get('Name', '')
                data_type = tag.get('DataType', '')
                
                # Common module tag patterns
                if any(pattern in name.upper() for pattern in ['MODULE', 'IO', 'INPUT', 'OUTPUT', 'CONFIG']):
                    module_count += 1
                    
                    # Extract module name from tag name
                    if ':' in name:
                        module_name = name.split(':')[0]
                        if module_name not in modules:
                            modules[module_name] = {
                                'name': module_name,
                                'type': 'I/O Module',
                                'source': 'TagInfo.XML',
                                'data_type': data_type,
                                'tags': []
                            }
                        modules[module_name]['tags'].append({
                            'name': name,
                            'data_type': data_type
                        })
            
            print(f"  Found {module_count} module-related tags")
            
        except Exception as e:
            print(f"  Error parsing TagInfo.XML: {e}")
            
        return modules
    
    def extract_quickinfo_modules(self):
        """Extract module info from QuickInfo.XML"""
        modules = {}
        
        quickinfo_file = self.db_dir / "QuickInfo.XML"
        if not quickinfo_file.exists():
            print("  QuickInfo.XML not found")
            return modules
            
        try:
            tree = ET.parse(quickinfo_file)
            root = tree.getroot()
            
            # Look for module configurations
            for module_elem in root.findall('.//Module'):
                name = module_elem.get('Name')
                catalog_number = module_elem.get('CatalogNumber')
                vendor = module_elem.get('Vendor')
                
                if name:
                    modules[name] = {
                        'name': name,
                        'catalog_number': catalog_number,
                        'vendor': vendor,
                        'type': 'Module',
                        'source': 'QuickInfo.XML'
                    }
                    
                    # Look for ports and connections
                    ports = []
                    for port in module_elem.findall('.//Port'):
                        port_info = {
                            'id': port.get('Id'),
                            'type': port.get('Type'),
                            'address': port.get('Address')
                        }
                        ports.append(port_info)
                    
                    if ports:
                        modules[name]['ports'] = ports
            
            print(f"  Found {len(modules)} modules in QuickInfo.XML")
            
        except Exception as e:
            print(f"  Error parsing QuickInfo.XML: {e}")
            
        return modules
    
    def analyze_modules(self, modules):
        """Analyze collected module data"""
        print(f"\n📊 Module Analysis:")
        print(f"  Total modules found: {len(modules)}")
        
        # Group by source
        by_source = {}
        for name, module in modules.items():
            source = module.get('source', 'Unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(name)
        
        for source, module_names in by_source.items():
            print(f"  {source}: {len(module_names)} modules")
            if len(module_names) <= 10:
                print(f"    {', '.join(module_names)}")
            else:
                print(f"    {', '.join(module_names[:10])}... ({len(module_names) - 10} more)")
        
        # Look for catalog numbers
        with_catalog = [name for name, module in modules.items() if module.get('catalog_number')]
        print(f"\n  Modules with catalog numbers: {len(with_catalog)}")
        
        # Show sample configurations
        print(f"\n📄 Sample Module Configurations:")
        for i, (name, module) in enumerate(list(modules.items())[:5]):
            print(f"\n  Module {i + 1}: {name}")
            for key, value in module.items():
                if key != 'tags':  # Skip tag lists for brevity
                    print(f"    {key}: {value}")
            
            if 'tags' in module and module['tags']:
                print(f"    tags: {len(module['tags'])} tags")
        
        # Save analysis
        analysis_file = self.output_dir / "module_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(modules, f, indent=2, default=str)
        print(f"\n✅ Module analysis saved to: {analysis_file}")
    
    def generate_l5x_modules(self, modules):
        """Generate L5X XML for modules"""
        print(f"\n📝 Generating L5X module configurations...")
        
        # Create modules section for L5X
        modules_xml = ET.Element("Modules")
        
        for name, module in modules.items():
            module_elem = ET.SubElement(modules_xml, "Module")
            module_elem.set("Name", name)
            module_elem.set("CatalogNumber", module.get('catalog_number', 'Unknown'))
            module_elem.set("Vendor", module.get('vendor', 'Rockwell Automation'))
            module_elem.set("ProductType", str(module.get('product_type', 0)))
            module_elem.set("ProductCode", str(module.get('product_code', 0)))
            module_elem.set("Major", str(module.get('major_rev', 1)))
            module_elem.set("Minor", str(module.get('minor_rev', 0)))
            module_elem.set("ParentModule", module.get('parent_module', 'Local'))
            module_elem.set("ParentModPortId", str(module.get('parent_port', 1)))
            module_elem.set("Inhibited", "false")
            module_elem.set("MajorFault", "false")
            
            # Add EKey if available
            ekey_elem = ET.SubElement(module_elem, "EKey")
            ekey_elem.set("State", "ExactMatch")
            
            # Add ports if available
            if 'ports' in module and module['ports']:
                ports_elem = ET.SubElement(module_elem, "Ports")
                for port_info in module['ports']:
                    port_elem = ET.SubElement(ports_elem, "Port")
                    port_elem.set("Id", str(port_info.get('id', 1)))
                    port_elem.set("Type", port_info.get('type', 'ICP'))
                    port_elem.set("Address", port_info.get('address', '0'))
        
        # Save L5X modules
        l5x_file = self.output_dir / "modules_l5x.xml"
        
        # Pretty print XML
        from xml.dom import minidom
        rough_string = ET.tostring(modules_xml, 'unicode')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        with open(l5x_file, 'w') as f:
            f.write(pretty)
        
        print(f"✅ L5X modules saved to: {l5x_file}")
        
        # Also create a complete L5X file with modules
        self.create_complete_l5x_with_modules(modules)
    
    def create_complete_l5x_with_modules(self, modules):
        """Create a complete L5X file including modules and previously extracted rungs"""
        print(f"\n📋 Creating complete L5X file with modules...")
        
        # Load previously extracted rungs
        rungs_file = Path("real_rungs_extracted/extracted_rungs_complete.json")
        rungs_data = []
        if rungs_file.exists():
            with open(rungs_file, 'r') as f:
                rungs_data = json.load(f)
            print(f"  Loaded {len(rungs_data)} rungs")
        
        # Create L5X structure
        root = ET.Element("RSLogix5000Content")
        root.set("SchemaRevision", "1.0")
        root.set("SoftwareRevision", "35.01")
        root.set("TargetName", "PLC100_Mashing")
        root.set("TargetType", "Controller")
        root.set("TargetRevision", "35.01")
        root.set("TargetLastEdited", "2025-01-01T00:00:00.000Z")
        root.set("ContainsContext", "true")
        
        # Controller
        controller = ET.SubElement(root, "Controller")
        controller.set("Use", "Context")
        controller.set("Name", "PLC100_Mashing")
        controller.set("ProcessorType", "1756-L85E")
        controller.set("MajorRev", "35")
        controller.set("MinorRev", "1")
        controller.set("TimeSlice", "20")
        controller.set("ShareUnusedTimeSlice", "1")
        
        # RedundancyInfo
        redundancy = ET.SubElement(controller, "RedundancyInfo")
        redundancy.set("Enabled", "false")
        redundancy.set("KeepTestEditsOnSwitchOver", "false")
        redundancy.set("IOMemoryPadPercentage", "90")
        redundancy.set("DataTablePadPercentage", "50")
        
        # Security
        security = ET.SubElement(controller, "Security")
        security.set("Code", "0")
        security.set("ChangesToDetect", "16#ffff_ffff_ffff_ffff")
        
        # SafetyInfo
        safety = ET.SubElement(controller, "SafetyInfo")
        safety.set("SafetySignature", "16#0000_0000_0000_0000")
        
        # DataTypes (placeholder)
        datatypes = ET.SubElement(controller, "DataTypes")
        
        # Modules section
        modules_elem = ET.SubElement(controller, "Modules")
        
        for name, module in modules.items():
            module_elem = ET.SubElement(modules_elem, "Module")
            module_elem.set("Name", name)
            module_elem.set("CatalogNumber", module.get('catalog_number', 'Generic'))
            module_elem.set("Vendor", module.get('vendor', 'Rockwell Automation'))
            module_elem.set("ProductType", str(module.get('product_type', 0)))
            module_elem.set("ProductCode", str(module.get('product_code', 0)))
            module_elem.set("Major", str(module.get('major_rev', 1)))
            module_elem.set("Minor", str(module.get('minor_rev', 0)))
            module_elem.set("ParentModule", module.get('parent_module', 'Local'))
            module_elem.set("ParentModPortId", str(module.get('parent_port', 1)))
            module_elem.set("Inhibited", "false")
            module_elem.set("MajorFault", "false")
            
            # EKey
            ekey = ET.SubElement(module_elem, "EKey")
            ekey.set("State", "CompatibleModule")
        
        # AOIDefinitions (placeholder)
        aoi_defs = ET.SubElement(controller, "AddOnInstructionDefinitions")
        
        # Tags (placeholder)
        tags = ET.SubElement(controller, "Tags")
        
        # Programs with rungs
        programs_elem = ET.SubElement(controller, "Programs")
        
        # Group rungs by program (simplified approach)
        program_elem = ET.SubElement(programs_elem, "Program")
        program_elem.set("Name", "MainProgram")
        program_elem.set("TestEdits", "false")
        program_elem.set("MainRoutineName", "MainRoutine")
        program_elem.set("Disabled", "false")
        program_elem.set("UseAsFolder", "false")
        
        # Tags for program
        prog_tags = ET.SubElement(program_elem, "Tags")
        
        # Routines
        routines_elem = ET.SubElement(program_elem, "Routines")
        
        # Main routine with all rungs
        routine_elem = ET.SubElement(routines_elem, "Routine")
        routine_elem.set("Name", "MainRoutine")
        routine_elem.set("Type", "RLL")
        
        # RLL Content
        rll_elem = ET.SubElement(routine_elem, "RLLContent")
        
        # Add rungs
        for i, rung_data in enumerate(rungs_data[:100]):  # Limit to first 100 rungs
            rung_elem = ET.SubElement(rll_elem, "Rung")
            rung_elem.set("Number", str(i))
            rung_elem.set("Type", "N")
            
            text_elem = ET.SubElement(rung_elem, "Text")
            text_elem.text = rung_data['text']
        
        # Tasks
        tasks_elem = ET.SubElement(controller, "Tasks")
        task_elem = ET.SubElement(tasks_elem, "Task")
        task_elem.set("Name", "MainTask")
        task_elem.set("Type", "CONTINUOUS")
        task_elem.set("Priority", "10")
        task_elem.set("Watchdog", "500")
        task_elem.set("DisableUpdateOutputs", "false")
        task_elem.set("InhibitTask", "false")
        
        # Scheduled programs
        scheduled_progs = ET.SubElement(task_elem, "ScheduledPrograms")
        sched_prog = ET.SubElement(scheduled_progs, "ScheduledProgram")
        sched_prog.set("Name", "MainProgram")
        
        # Save complete L5X
        complete_l5x_file = self.output_dir / "complete_with_modules.l5x"
        
        # Pretty print
        from xml.dom import minidom
        rough_string = ET.tostring(root, 'unicode')
        reparsed = minidom.parseString(rough_string)
        pretty = reparsed.toprettyxml(indent="  ")
        
        with open(complete_l5x_file, 'w') as f:
            f.write(pretty)
        
        print(f"✅ Complete L5X with modules saved to: {complete_l5x_file}")
        print(f"   Includes {len(modules)} modules and {len(rungs_data)} rungs")

def main():
    acd_file = "docs/exports/PLC100_Mashing.ACD"
    extractor = ModuleIOExtractor(acd_file)
    extractor.extract()

if __name__ == "__main__":
    main() 