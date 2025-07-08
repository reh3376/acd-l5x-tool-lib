"""
Enhanced Data Models for PLC Format Converter - Phase 3.9 (Migrated)
====================================================================

Comprehensive data models supporting 95%+ data preservation with full
PLC component extraction and validation capabilities.

Migrated from Phase 3.9 development to production acd-l5x-tool-lib.
"""

"""
Enhanced Data Models for PLC Format Converter - Phase 3.9
=========================================================

Comprehensive data models supporting 95%+ data preservation with full
PLC component extraction and validation capabilities.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback for environments without pydantic
    BaseModel = object
    Field = lambda **kwargs: None
    validator = lambda *args, **kwargs: lambda f: f
    PYDANTIC_AVAILABLE = False


class ConversionStatus(Enum):
    """Enhanced conversion status tracking"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    DATA_LOSS_DETECTED = "data_loss_detected"
    BINARY_PARSING_ERROR = "binary_parsing_error"
    XML_GENERATION_ERROR = "xml_generation_error"


class DataPreservationLevel(Enum):
    """Data preservation quality levels"""
    METADATA_ONLY = "metadata_only"      # 0-20% (current baseline)
    BASIC_STRUCTURE = "basic_structure"  # 20-50%
    PARTIAL_LOGIC = "partial_logic"      # 50-80%
    COMPREHENSIVE = "comprehensive"      # 80-95%
    INDUSTRY_STANDARD = "industry_standard"  # 95%+


class PLCInstructionType(Enum):
    """Comprehensive PLC instruction types"""
    # Basic Instructions
    XIC = "XIC"  # Examine if Closed
    XIO = "XIO"  # Examine if Open
    OTE = "OTE"  # Output Energize
    OTL = "OTL"  # Output Latch
    OTU = "OTU"  # Output Unlatch
    
    # Math Instructions
    ADD = "ADD"
    SUB = "SUB" 
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    
    # Motion Control Instructions
    MAM = "MAM"   # Motion Axis Move
    MAJ = "MAJ"   # Motion Axis Jog
    MAS = "MAS"   # Motion Axis Stop
    MAOC = "MAOC" # Motion Axis Output Cam
    MAPC = "MAPC" # Motion Axis Position Cam
    MAAT = "MAAT" # Motion Axis Absolute Time
    
    # Safety Instructions (GuardLogix)
    ESTOP = "ESTOP"
    SAFEIN = "SAFEIN"
    SAFEOUT = "SAFEOUT"
    
    # Process Control
    PID = "PID"
    PIDE = "PIDE"
    
    # Communication
    MSG = "MSG"
    CIP = "CIP"


@dataclass
class DataIntegrityScore:
    """Comprehensive data integrity scoring for conversion validation"""
    overall_score: float = 0.0  # 0-100%
    component_scores: Dict[str, float] = field(default_factory=dict)
    preservation_level: DataPreservationLevel = DataPreservationLevel.METADATA_ONLY
    
    # Detailed scoring breakdown
    logic_preservation: float = 0.0      # Ladder logic completeness
    tag_preservation: float = 0.0        # Tag database completeness  
    io_preservation: float = 0.0         # I/O configuration completeness
    motion_preservation: float = 0.0     # Motion control completeness
    safety_preservation: float = 0.0     # Safety system completeness
    
    # Quality metrics
    instruction_count: int = 0
    preserved_instructions: int = 0
    tag_count: int = 0
    preserved_tags: int = 0
    
    # Validation metadata
    validation_timestamp: datetime = field(default_factory=datetime.now)
    validation_method: str = "enhanced_phase39"
    
    def calculate_overall_score(self) -> float:
        """Calculate weighted overall score"""
        weights = {
            'logic_preservation': 0.4,
            'tag_preservation': 0.25,
            'io_preservation': 0.15,
            'motion_preservation': 0.1,
            'safety_preservation': 0.1
        }
        
        self.overall_score = sum(
            getattr(self, metric) * weight 
            for metric, weight in weights.items()
        )
        
        # Determine preservation level
        if self.overall_score >= 95:
            self.preservation_level = DataPreservationLevel.INDUSTRY_STANDARD
        elif self.overall_score >= 80:
            self.preservation_level = DataPreservationLevel.COMPREHENSIVE
        elif self.overall_score >= 50:
            self.preservation_level = DataPreservationLevel.PARTIAL_LOGIC
        elif self.overall_score >= 20:
            self.preservation_level = DataPreservationLevel.BASIC_STRUCTURE
        else:
            self.preservation_level = DataPreservationLevel.METADATA_ONLY
            
        return self.overall_score


@dataclass 
class BinaryDataBlock:
    """Represents a binary data block extracted from ACD file"""
    block_type: str
    offset: int
    size: int
    data: bytes
    checksum: str = ""
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.md5(self.data).hexdigest()


@dataclass
class ComponentExtraction:
    """Tracks component extraction from binary format"""
    component_type: str
    extraction_method: str
    success: bool
    data_blocks: List[BinaryDataBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)


class EnhancedPLCComponent(BaseModel if PYDANTIC_AVAILABLE else object):
    """Enhanced base class for all PLC components with binary extraction support"""
    
    if PYDANTIC_AVAILABLE:
        name: str = Field(..., description="Component name")
        component_type: str = Field(..., description="Type of PLC component")
        uuid: str = Field(default="", description="Unique identifier")
        
        # Enhanced Phase 3.9 fields
        binary_source: Optional[BinaryDataBlock] = Field(None, description="Source binary data")
        extraction_info: Optional[ComponentExtraction] = Field(None, description="Extraction metadata")
        data_integrity: Optional[DataIntegrityScore] = Field(None, description="Data integrity metrics")
        
        # Version tracking
        studio5000_version: Optional[str] = Field(None, description="Studio 5000 version")
        firmware_version: Optional[str] = Field(None, description="Controller firmware version")
        
        class Config:
            arbitrary_types_allowed = True
    else:
        def __init__(self, name: str, component_type: str, **kwargs):
            self.name = name
            self.component_type = component_type
            self.uuid = kwargs.get('uuid', '')
            self.binary_source = kwargs.get('binary_source')
            self.extraction_info = kwargs.get('extraction_info')
            self.data_integrity = kwargs.get('data_integrity')
            self.studio5000_version = kwargs.get('studio5000_version')
            self.firmware_version = kwargs.get('firmware_version')


class PLCInstruction(EnhancedPLCComponent):
    """Enhanced PLC instruction with complete parameter preservation"""
    
    if PYDANTIC_AVAILABLE:
        instruction_type: PLCInstructionType = Field(..., description="Instruction type")
        parameters: Dict[str, Any] = Field(default_factory=dict, description="Instruction parameters")
        operands: List[str] = Field(default_factory=list, description="Instruction operands")
        
        # Enhanced fields for Phase 3.9
        raw_binary: Optional[bytes] = Field(None, description="Raw instruction binary")
        assembly_code: Optional[str] = Field(None, description="Assembly representation")
        execution_time: Optional[float] = Field(None, description="Estimated execution time (ms)")
        
        # Motion control specific
        motion_parameters: Optional[Dict[str, Any]] = Field(None, description="Motion control parameters")
        safety_parameters: Optional[Dict[str, Any]] = Field(None, description="Safety parameters")


class PLCTag(EnhancedPLCComponent):
    """Enhanced PLC tag with complete data type preservation"""
    
    if PYDANTIC_AVAILABLE:
        data_type: str = Field(..., description="Tag data type")
        scope: str = Field(default="Controller", description="Tag scope")
        initial_value: Optional[Any] = Field(None, description="Initial value")
        
        # Enhanced Phase 3.9 fields
        memory_address: Optional[str] = Field(None, description="Physical memory address")
        access_rights: Optional[str] = Field(None, description="Read/Write permissions")
        alias_for: Optional[str] = Field(None, description="Alias target tag")
        
        # Complex data type support
        udt_definition: Optional[Dict[str, Any]] = Field(None, description="UDT structure definition")
        array_dimensions: Optional[List[int]] = Field(None, description="Array dimensions")
        
        # I/O mapping
        io_module: Optional[str] = Field(None, description="Associated I/O module")
        io_channel: Optional[int] = Field(None, description="I/O channel number")


class PLCRoutine(EnhancedPLCComponent):
    """Enhanced PLC routine with complete logic preservation"""
    
    if PYDANTIC_AVAILABLE:
        routine_type: str = Field(..., description="Routine type (RLL, ST, FBD)")
        instructions: List[PLCInstruction] = Field(default_factory=list, description="Routine instructions")
        
        # Enhanced Phase 3.9 fields
        raw_logic: Optional[str] = Field(None, description="Raw logic representation")
        compiled_code: Optional[bytes] = Field(None, description="Compiled routine code")
        execution_order: Optional[int] = Field(None, description="Execution order in program")
        
        # Performance metrics
        scan_time: Optional[float] = Field(None, description="Typical scan time (ms)")
        memory_usage: Optional[int] = Field(None, description="Memory usage (bytes)")
        
        # Dependencies
        called_routines: List[str] = Field(default_factory=list, description="Called routine names")
        used_tags: List[str] = Field(default_factory=list, description="Referenced tag names")
        used_aois: List[str] = Field(default_factory=list, description="Used AOI names")


class PLCAddOnInstruction(EnhancedPLCComponent):
    """Enhanced Add-On Instruction (AOI) definition"""
    
    if PYDANTIC_AVAILABLE:
        revision: str = Field(default="1.0", description="AOI revision")
        parameters: List[PLCTag] = Field(default_factory=list, description="AOI parameters")
        local_tags: List[PLCTag] = Field(default_factory=list, description="AOI local tags")
        logic: List[PLCRoutine] = Field(default_factory=list, description="AOI logic routines")
        
        # Enhanced Phase 3.9 fields
        help_text: str = Field(default="", description="AOI help documentation")
        change_history: List[Dict[str, Any]] = Field(default_factory=list, description="Change history")
        signature_id: Optional[str] = Field(None, description="AOI signature ID")
        
        # Safety AOI support
        safety_aoi: bool = Field(default=False, description="Is safety AOI")
        safety_signature: Optional[str] = Field(None, description="Safety signature")


class PLCProgram(EnhancedPLCComponent):
    """Enhanced PLC program with complete structure preservation"""
    
    if PYDANTIC_AVAILABLE:
        routines: List[PLCRoutine] = Field(default_factory=list, description="Program routines")
        main_routine: Optional[str] = Field(None, description="Main routine name")
        
        # Enhanced Phase 3.9 fields
        program_type: str = Field(default="Normal", description="Program type")
        task_assignment: Optional[str] = Field(None, description="Assigned task name")
        inhibit_state: bool = Field(default=False, description="Program inhibit state")
        
        # Safety program support
        safety_signature: Optional[str] = Field(None, description="Safety program signature")
        safety_lock_state: Optional[str] = Field(None, description="Safety lock state")


class PLCController(EnhancedPLCComponent):
    """Enhanced PLC controller with complete configuration preservation"""
    
    if PYDANTIC_AVAILABLE:
        processor_type: str = Field(..., description="Processor type")
        programs: List[PLCProgram] = Field(default_factory=list, description="Controller programs")
        tags: List[PLCTag] = Field(default_factory=list, description="Controller tags")
        
        # Enhanced Phase 3.9 fields
        catalog_number: str = Field(default="", description="Controller catalog number")
        series: str = Field(default="", description="Controller series")
        revision: str = Field(default="", description="Hardware revision")
        
        # Communication configuration
        ethernet_config: Optional[Dict[str, Any]] = Field(None, description="Ethernet configuration")
        serial_config: Optional[Dict[str, Any]] = Field(None, description="Serial configuration")
        
        # Motion configuration
        motion_groups: List[Dict[str, Any]] = Field(default_factory=list, description="Motion groups")
        axes_configuration: List[Dict[str, Any]] = Field(default_factory=list, description="Axes configuration")
        
        # Safety configuration (GuardLogix)
        safety_config: Optional[Dict[str, Any]] = Field(None, description="Safety configuration")
        safety_signature: Optional[str] = Field(None, description="Safety signature")


class PLCDevice(EnhancedPLCComponent):
    """Enhanced PLC device/module configuration"""
    
    if PYDANTIC_AVAILABLE:
        device_type: str = Field(..., description="Device type (Local, Remote, etc.)")
        catalog_number: str = Field(default="", description="Device catalog number")
        vendor_id: Optional[int] = Field(None, description="Vendor ID")
        product_code: Optional[int] = Field(None, description="Product code")
        
        # Enhanced Phase 3.9 fields
        slot_number: Optional[int] = Field(None, description="Chassis slot number")
        ip_address: Optional[str] = Field(None, description="IP address for Ethernet devices")
        node_address: Optional[int] = Field(None, description="Node address")
        
        # Configuration data
        configuration_data: Dict[str, Any] = Field(default_factory=dict, description="Device configuration")
        connection_parameters: Dict[str, Any] = Field(default_factory=dict, description="Connection parameters")
        
        # I/O mapping
        input_tags: List[str] = Field(default_factory=list, description="Input tag mappings")
        output_tags: List[str] = Field(default_factory=list, description="Output tag mappings")


class PLCProject(EnhancedPLCComponent):
    """Enhanced PLC project with complete project preservation"""
    
    if PYDANTIC_AVAILABLE:
        controllers: List[PLCController] = Field(default_factory=list, description="Project controllers")
        devices: List[PLCDevice] = Field(default_factory=list, description="Project devices/modules")
        
        # Enhanced Phase 3.9 fields
        project_creation_date: Optional[datetime] = Field(None, description="Project creation date")
        last_modified_date: Optional[datetime] = Field(None, description="Last modification date")
        created_by: Optional[str] = Field(None, description="Project creator")
        
        # Version information
        studio5000_version: str = Field(default="", description="Studio 5000 version")
        logix_designer_version: str = Field(default="", description="Logix Designer version")
        
        # Project settings
        project_description: str = Field(default="", description="Project description")
        company_name: str = Field(default="", description="Company name")
        
        # Enhanced metadata for migration
        source_file_path: Optional[Path] = Field(None, description="Source ACD file path")
        source_file_hash: Optional[str] = Field(None, description="Source file hash")
        conversion_metadata: Optional[Dict[str, Any]] = Field(None, description="Conversion metadata")


@dataclass
class ConversionResult:
    """Enhanced conversion result with comprehensive metrics"""
    success: bool
    status: ConversionStatus
    
    # File information
    source_file: Optional[Path] = None
    target_file: Optional[Path] = None
    source_size: int = 0
    target_size: int = 0
    
    # Enhanced Phase 3.9 metrics
    data_integrity: Optional[DataIntegrityScore] = None
    extraction_summary: Dict[str, ComponentExtraction] = field(default_factory=dict)
    
    # Performance metrics
    conversion_time: float = 0.0
    memory_usage: int = 0
    
    # Issues and warnings
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Validation results
    round_trip_validated: bool = False
    git_optimized: bool = False
    
    # Migration readiness
    migration_ready: bool = False
    compatibility_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'success': self.success,
            'status': self.status.value,
            'source_file': str(self.source_file) if self.source_file else None,
            'target_file': str(self.target_file) if self.target_file else None,
            'source_size': self.source_size,
            'target_size': self.target_size,
            'conversion_time': self.conversion_time,
            'memory_usage': self.memory_usage,
            'issues': self.issues,
            'warnings': self.warnings,
            'round_trip_validated': self.round_trip_validated,
            'git_optimized': self.git_optimized,
            'migration_ready': self.migration_ready,
            'compatibility_score': self.compatibility_score
        }
        
        if self.data_integrity:
            result['data_integrity'] = {
                'overall_score': self.data_integrity.overall_score,
                'preservation_level': self.data_integrity.preservation_level.value,
                'logic_preservation': self.data_integrity.logic_preservation,
                'tag_preservation': self.data_integrity.tag_preservation,
                'io_preservation': self.data_integrity.io_preservation,
                'motion_preservation': self.data_integrity.motion_preservation,
                'safety_preservation': self.data_integrity.safety_preservation,
                'instruction_count': self.data_integrity.instruction_count,
                'preserved_instructions': self.data_integrity.preserved_instructions,
                'tag_count': self.data_integrity.tag_count,
                'preserved_tags': self.data_integrity.preserved_tags
            }
        
        return result 

# Additional classes required by validation framework
class RoutineType(Enum):
    """PLC routine types"""
    LADDER = "RLL"
    STRUCTURED_TEXT = "ST"
    FUNCTION_BLOCK = "FBD"
    SEQUENTIAL_FUNCTION_CHART = "SFC"


class DataType(Enum):
    """PLC data types"""
    BOOL = "BOOL"
    SINT = "SINT"
    INT = "INT"
    DINT = "DINT"
    LINT = "LINT"
    REAL = "REAL"
    LREAL = "LREAL"
    STRING = "STRING"
    TIMER = "TIMER"
    COUNTER = "COUNTER"
    CONTROL = "CONTROL"


class PLCUserDefinedType(EnhancedPLCComponent):
    """Enhanced User Defined Type (UDT) definition"""
    
    if PYDANTIC_AVAILABLE:
        members: List[Dict[str, Any]] = Field(default_factory=list, description="UDT members")
        description: str = Field(default="", description="UDT description")
        family: str = Field(default="NoFamily", description="UDT family")
        
        # Enhanced Phase 3.9 fields
        size_bytes: Optional[int] = Field(None, description="UDT size in bytes")
        alignment: Optional[int] = Field(None, description="Memory alignment")


class PLCMetadata(BaseModel if PYDANTIC_AVAILABLE else object):
    """PLC project metadata"""
    
    if PYDANTIC_AVAILABLE:
        creation_date: Optional[datetime] = Field(None, description="Creation date")
        modification_date: Optional[datetime] = Field(None, description="Last modification date")
        created_by: str = Field(default="", description="Creator")
        company: str = Field(default="", description="Company name")
        description: str = Field(default="", description="Project description")


class PLCRung(EnhancedPLCComponent):
    """Enhanced ladder logic rung"""
    
    if PYDANTIC_AVAILABLE:
        number: int = Field(..., description="Rung number")
        comment: str = Field(default="", description="Rung comment")
        instructions: List[PLCInstruction] = Field(default_factory=list, description="Rung instructions")
        
        # Enhanced Phase 3.9 fields
        raw_text: Optional[str] = Field(None, description="Raw rung text")
        structured_text: Optional[str] = Field(None, description="Structured text representation")


class ConversionError(Exception):
    """Enhanced conversion error with detailed context"""
    
    def __init__(self, message: str, error_code: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.now()


class FormatError(ConversionError):
    """Format-specific error"""
    
    def __init__(self, message: str, format_type: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message, f"FORMAT_ERROR_{format_type.upper()}", context)
        self.format_type = format_type
