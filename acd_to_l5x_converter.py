#!/usr/bin/env python3
"""
ACD to L5X Converter using hutcheb/acd library
"""

import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from datetime import datetime
from acd.api import ImportProjectFromFile, ExtractAcdDatabase
import json

class ACDtoL5XConverter:
    def __init__(self, acd_file_path):
        self.acd_file = Path(acd_file_path)
        self.output_dir = Path("acd_to_l5x_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Extract databases for additional info
        self.db_dir = self.output_dir / "databases"
        self.taginfo_data = None
        self.controller_info = None
        
    def extract_databases(self):
        """Extract ACD database files for additional parsing"""
        print("📋 Extracting ACD databases...")
        try:
            ExtractAcdDatabase(str(self.acd_file), str(self.db_dir)).extract()
            print("✅ Databases extracted")
            
            # Parse TagInfo.XML for complete information
            taginfo_path = self.db_dir / "TagInfo.XML"
            if taginfo_path.exists():
                self.parse_taginfo_xml(taginfo_path)
                
        except Exception as e:
            print(f"⚠️  Warning: Could not extract databases: {e}")
    
    def parse_taginfo_xml(self, taginfo_path):
        """Parse TagInfo.XML for complete controller information"""
        try:
            with open(taginfo_path, 'r', encoding='utf-16', errors='ignore') as f:
                content = f.read()
            
            root = ET.fromstring(content)
            self.taginfo_data = {
                'controller_name': root.get('Name'),
                'programs': {},
                'tags': [],
                'datatypes': []
            }
            
            # Extract program details with routines
            for program in root.findall('.//Program'):
                prog_name = program.get('Name')
                self.taginfo_data['programs'][prog_name] = {
                    'type': program.get('Type', 'Normal'),
                    'routines': []
                }
                
                for routine in program.findall('.//Routine'):
                    self.taginfo_data['programs'][prog_name]['routines'].append({
                        'name': routine.get('Name'),
                        'type': routine.get('Type', 'RLL')
                    })
            
            # Extract tags
            for tag in root.findall('.//Tag'):
                self.taginfo_data['tags'].append({
                    'name': tag.get('Name'),
                    'datatype': tag.get('DataType'),
                    'scope': tag.get('Scope', 'Controller')
                })
                
            print(f"✅ Parsed TagInfo.XML: {len(self.taginfo_data['programs'])} programs found")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not parse TagInfo.XML: {e}")
    
    def convert_to_l5x(self):
        """Convert ACD to L5X format"""
        print(f"\n🔄 Converting {self.acd_file.name} to L5X...")
        
        # Apply patch to skip Comments parsing
        from patch_hutcheb_acd import patch_acd_library
        patch_acd_library()
        
        # First extract databases for additional info
        self.extract_databases()
        
        try:
            # Import project using hutcheb/acd
            print("\n📋 Importing ACD project...")
            project = ImportProjectFromFile(str(self.acd_file)).import_project()
            
            if not project or not project.controller:
                print("❌ Failed to import project or no controller found")
                return False
            
            controller = project.controller
            print(f"✅ Controller imported: {controller.name}")
            
            # Create L5X XML structure
            root = self.create_l5x_root()
            
            # Add controller element
            controller_elem = self.create_controller_element(controller)
            root.append(controller_elem)
            
            # Save L5X file
            output_file = self.output_dir / f"{self.acd_file.stem}.L5X"
            self.save_l5x(root, output_file)
            
            print(f"\n✅ L5X file saved to: {output_file}")
            
            # Generate conversion report
            self.generate_report(controller)
            
            return True
            
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_l5x_root(self):
        """Create L5X root element with proper attributes"""
        root = ET.Element('RSLogix5000Content')
        root.set('SchemaRevision', '1.0')
        root.set('SoftwareRevision', '35.00')
        root.set('TargetName', self.taginfo_data['controller_name'] if self.taginfo_data else 'Controller')
        root.set('TargetType', 'Controller')
        root.set('ContainsContext', 'false')
        root.set('ExportDate', datetime.now().strftime('%a %b %d %H:%M:%S %Y'))
        root.set('ExportOptions', 'References NoRawData L5KData DecoratedData Context Dependencies ForceProtectedEncoding')
        
        return root
    
    def create_controller_element(self, controller):
        """Create controller XML element with all sub-elements"""
        ctrl_elem = ET.Element('Controller')
        ctrl_elem.set('Name', controller.name)
        ctrl_elem.set('ProcessorType', controller.processor_type or 'Unknown')
        ctrl_elem.set('MajorRev', str(controller.major_revision or 35))
        ctrl_elem.set('MinorRev', str(controller.minor_revision or 0))
        
        # Add description if available
        if hasattr(controller, 'description') and controller.description:
            desc_elem = ET.SubElement(ctrl_elem, 'Description')
            desc_elem.text = ET.CDATA(controller.description)
        
        # Add DataTypes
        if controller.data_types:
            dt_elem = ET.SubElement(ctrl_elem, 'DataTypes')
            for dt in controller.data_types:
                self.add_datatype_element(dt_elem, dt)
        
        # Add Modules
        if controller.modules:
            modules_elem = ET.SubElement(ctrl_elem, 'Modules')
            for module in controller.modules:
                self.add_module_element(modules_elem, module)
        
        # Add Add-On Instructions if available
        if hasattr(controller, 'add_on_instructions') and controller.add_on_instructions:
            aoi_elem = ET.SubElement(ctrl_elem, 'AddOnInstructionDefinitions')
            for aoi in controller.add_on_instructions:
                self.add_aoi_element(aoi_elem, aoi)
        
        # Add Tags
        if controller.tags:
            tags_elem = ET.SubElement(ctrl_elem, 'Tags')
            for tag in controller.tags:
                self.add_tag_element(tags_elem, tag)
        
        # Add Programs
        if controller.programs:
            programs_elem = ET.SubElement(ctrl_elem, 'Programs')
            for program in controller.programs:
                self.add_program_element(programs_elem, program)
        
        # Add Tasks if available
        if hasattr(controller, 'tasks') and controller.tasks:
            tasks_elem = ET.SubElement(ctrl_elem, 'Tasks')
            for task in controller.tasks:
                self.add_task_element(tasks_elem, task)
        
        return ctrl_elem
    
    def add_datatype_element(self, parent, datatype):
        """Add DataType element"""
        dt_elem = ET.SubElement(parent, 'DataType')
        dt_elem.set('Name', datatype.name)
        dt_elem.set('Family', getattr(datatype, 'family', 'NoFamily'))
        dt_elem.set('Class', getattr(datatype, 'class_name', 'User'))
        
        # Add members if available
        if hasattr(datatype, 'members') and datatype.members:
            members_elem = ET.SubElement(dt_elem, 'Members')
            for member in datatype.members:
                self.add_member_element(members_elem, member)
    
    def add_member_element(self, parent, member):
        """Add Member element for DataType"""
        member_elem = ET.SubElement(parent, 'Member')
        member_elem.set('Name', member.name)
        member_elem.set('DataType', member.data_type)
        
        if hasattr(member, 'dimension') and member.dimension:
            member_elem.set('Dimension', str(member.dimension))
        
        member_elem.set('Radix', getattr(member, 'radix', 'Decimal'))
        member_elem.set('Hidden', str(getattr(member, 'hidden', False)).lower())
    
    def add_module_element(self, parent, module):
        """Add Module element"""
        module_elem = ET.SubElement(parent, 'Module')
        module_elem.set('Name', module.name)
        module_elem.set('CatalogNumber', getattr(module, 'catalog_number', ''))
        module_elem.set('Vendor', str(getattr(module, 'vendor', 1)))
        module_elem.set('ProductType', str(getattr(module, 'product_type', 0)))
        module_elem.set('ProductCode', str(getattr(module, 'product_code', 0)))
        module_elem.set('Major', str(getattr(module, 'major', 1)))
        module_elem.set('Minor', str(getattr(module, 'minor', 1)))
        
        # Add module configuration if available
        if hasattr(module, 'config_data'):
            config_elem = ET.SubElement(module_elem, 'ConfigData')
            config_elem.text = str(module.config_data)
    
    def add_tag_element(self, parent, tag):
        """Add Tag element"""
        tag_elem = ET.SubElement(parent, 'Tag')
        tag_elem.set('Name', tag.tag_name)
        tag_elem.set('TagType', getattr(tag, 'tag_type', 'Base'))
        tag_elem.set('DataType', tag.data_type)
        tag_elem.set('Radix', getattr(tag, 'radix', 'Decimal'))
        tag_elem.set('Constant', str(getattr(tag, 'constant', False)).lower())
        tag_elem.set('ExternalAccess', getattr(tag, 'external_access', 'Read/Write'))
        
        # Add tag data if available
        if hasattr(tag, 'value') and tag.value:
            data_elem = ET.SubElement(tag_elem, 'Data')
            data_elem.text = str(tag.value)
    
    def add_program_element(self, parent, program):
        """Add Program element"""
        prog_elem = ET.SubElement(parent, 'Program')
        prog_elem.set('Name', program.name)
        prog_elem.set('Class', getattr(program, 'class_name', 'Standard'))
        
        # Add program tags if available
        if hasattr(program, 'tags') and program.tags:
            tags_elem = ET.SubElement(prog_elem, 'Tags')
            for tag in program.tags:
                self.add_tag_element(tags_elem, tag)
        
        # Add routines
        if hasattr(program, 'routines') and program.routines:
            routines_elem = ET.SubElement(prog_elem, 'Routines')
            for routine in program.routines:
                self.add_routine_element(routines_elem, routine)
        elif self.taginfo_data and program.name in self.taginfo_data['programs']:
            # Use TagInfo data if available
            routines_elem = ET.SubElement(prog_elem, 'Routines')
            for routine_info in self.taginfo_data['programs'][program.name]['routines']:
                routine_elem = ET.SubElement(routines_elem, 'Routine')
                routine_elem.set('Name', routine_info['name'])
                routine_elem.set('Type', routine_info['type'])
    
    def add_routine_element(self, parent, routine):
        """Add Routine element"""
        routine_elem = ET.SubElement(parent, 'Routine')
        routine_elem.set('Name', routine.name)
        routine_elem.set('Type', getattr(routine, 'type', 'RLL'))
        
        # Add rungs if available
        if hasattr(routine, 'rungs') and routine.rungs:
            rll_elem = ET.SubElement(routine_elem, 'RLLContent')
            for i, rung in enumerate(routine.rungs):
                self.add_rung_element(rll_elem, rung, i)
    
    def add_rung_element(self, parent, rung, number):
        """Add Rung element"""
        rung_elem = ET.SubElement(parent, 'Rung')
        rung_elem.set('Number', str(number))
        rung_elem.set('Type', getattr(rung, 'type', 'N'))
        
        # Add rung comment if available
        if hasattr(rung, 'comment') and rung.comment:
            comment_elem = ET.SubElement(rung_elem, 'Comment')
            comment_elem.text = ET.CDATA(rung.comment)
        
        # Add rung text (ladder logic)
        if hasattr(rung, 'text') and rung.text:
            text_elem = ET.SubElement(rung_elem, 'Text')
            text_elem.text = ET.CDATA(rung.text)
    
    def add_task_element(self, parent, task):
        """Add Task element"""
        task_elem = ET.SubElement(parent, 'Task')
        task_elem.set('Name', task.name)
        task_elem.set('Type', getattr(task, 'type', 'PERIODIC'))
        task_elem.set('Priority', str(getattr(task, 'priority', 10)))
        task_elem.set('Watchdog', str(getattr(task, 'watchdog', 500)))
        
        # Add scheduled programs
        if hasattr(task, 'scheduled_programs') and task.scheduled_programs:
            for prog_name in task.scheduled_programs:
                prog_elem = ET.SubElement(task_elem, 'ScheduledProgram')
                prog_elem.set('Name', prog_name)
    
    def add_aoi_element(self, parent, aoi):
        """Add AddOnInstructionDefinition element"""
        aoi_elem = ET.SubElement(parent, 'AddOnInstructionDefinition')
        aoi_elem.set('Name', aoi.name)
        aoi_elem.set('Revision', str(getattr(aoi, 'revision', '1.0')))
        aoi_elem.set('ExecutePrescan', str(getattr(aoi, 'execute_prescan', True)).lower())
        aoi_elem.set('ExecutePostscan', str(getattr(aoi, 'execute_postscan', True)).lower())
        aoi_elem.set('ExecuteEnableInFalse', str(getattr(aoi, 'execute_enable_in_false', True)).lower())
        
        # Add parameters
        if hasattr(aoi, 'parameters') and aoi.parameters:
            params_elem = ET.SubElement(aoi_elem, 'Parameters')
            for param in aoi.parameters:
                param_elem = ET.SubElement(params_elem, 'Parameter')
                param_elem.set('Name', param.name)
                param_elem.set('TagType', getattr(param, 'tag_type', 'Base'))
                param_elem.set('DataType', param.data_type)
                param_elem.set('Usage', getattr(param, 'usage', 'Input'))
                param_elem.set('Required', str(getattr(param, 'required', True)).lower())
    
    def save_l5x(self, root, output_file):
        """Save XML to L5X file with proper formatting"""
        # Convert to string with pretty printing
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        
        # Parse with minidom for pretty printing
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ', encoding='UTF-8')
        
        # Write to file
        with open(output_file, 'wb') as f:
            f.write(pretty_xml)
    
    def generate_report(self, controller):
        """Generate conversion report"""
        report = {
            'conversion_date': datetime.now().isoformat(),
            'source_file': str(self.acd_file),
            'controller': {
                'name': controller.name,
                'processor_type': controller.processor_type,
                'revision': f"{controller.major_revision}.{controller.minor_revision}"
            },
            'statistics': {
                'programs': len(controller.programs) if controller.programs else 0,
                'tags': len(controller.tags) if controller.tags else 0,
                'data_types': len(controller.data_types) if controller.data_types else 0,
                'modules': len(controller.modules) if controller.modules else 0
            }
        }
        
        # Add program details
        if controller.programs:
            report['programs'] = []
            for prog in controller.programs:
                prog_info = {
                    'name': prog.name,
                    'routines': len(prog.routines) if hasattr(prog, 'routines') and prog.routines else 0
                }
                report['programs'].append(prog_info)
        
        # Save report
        report_file = self.output_dir / f"{self.acd_file.stem}_conversion_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Conversion Report:")
        print(f"  Controller: {report['controller']['name']}")
        print(f"  Programs: {report['statistics']['programs']}")
        print(f"  Tags: {report['statistics']['tags']}")
        print(f"  Data Types: {report['statistics']['data_types']}")
        print(f"  Modules: {report['statistics']['modules']}")
        print(f"\n  Report saved to: {report_file}")

def main():
    if len(sys.argv) < 2:
        # Use default file if no argument provided
        acd_file = "docs/exports/PLC100_Mashing.ACD"
        print(f"No file specified, using default: {acd_file}")
    else:
        acd_file = sys.argv[1]
    
    if not Path(acd_file).exists():
        print(f"❌ Error: File not found: {acd_file}")
        sys.exit(1)
    
    converter = ACDtoL5XConverter(acd_file)
    success = converter.convert_to_l5x()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 