"""
Core data models for the unified PLC representation.

This module defines the internal data structures that represent PLC components
in a format-agnostic way, enabling lossless conversion between ACD and L5X formats.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator


class PLCComponentType(str, Enum):
    """Types of PLC components."""
    CONTROLLER = "controller"
    PROGRAM = "program"
    ROUTINE = "routine"
    AOI = "aoi"
    UDT = "udt"
    TAG = "tag"
    DEVICE = "device"


class DataType(str, Enum):
    """PLC data types."""
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
    UDT = "UDT"  # User Defined Type
    ARRAY = "ARRAY"


class RoutineType(str, Enum):
    """Types of PLC routines."""
    LADDER = "RLL"  # Relay Ladder Logic
    STRUCTURED_TEXT = "ST"
    FUNCTION_BLOCK = "FBD"
    SEQUENTIAL_FUNCTION_CHART = "SFC"


class ConversionStatus(str, Enum):
    """Status of conversion operations."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PARTIAL = "partial"


class PLCMetadata(BaseModel):
    """Metadata for PLC components."""
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    comment: Optional[str] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class PLCTag(BaseModel):
    """Represents a PLC tag."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    data_type: DataType
    scope: str  # Controller, Program name, or AOI name
    value: Optional[Any] = None
    description: Optional[str] = None
    comment: Optional[str] = None
    alias_for: Optional[str] = None  # For alias tags
    dimensions: Optional[List[int]] = None  # For arrays
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)
    
    class Config:
        use_enum_values = True


class PLCParameter(BaseModel):
    """Represents a parameter in an AOI."""
    name: str
    data_type: DataType
    usage: str  # Input, Output, InOut
    default_value: Optional[Any] = None
    description: Optional[str] = None
    required: bool = True
    
    class Config:
        use_enum_values = True


class PLCUDTMember(BaseModel):
    """Represents a member of a User Defined Type."""
    name: str
    data_type: DataType
    offset: Optional[int] = None
    bit_position: Optional[int] = None
    dimensions: Optional[List[int]] = None
    description: Optional[str] = None
    
    class Config:
        use_enum_values = True


class PLCUserDefinedType(BaseModel):
    """Represents a User Defined Type (UDT)."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    members: List[PLCUDTMember] = Field(default_factory=list)
    family: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class PLCRung(BaseModel):
    """Represents a rung in ladder logic."""
    number: int
    text: Optional[str] = None
    comment: Optional[str] = None
    logic: Optional[str] = None  # Ladder logic representation
    structured_text: Optional[str] = None  # ST equivalent if available


class PLCRoutine(BaseModel):
    """Represents a PLC routine."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    type: RoutineType
    description: Optional[str] = None
    comment: Optional[str] = None
    program_name: str
    rungs: List[PLCRung] = Field(default_factory=list)
    structured_text: Optional[str] = None
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)
    
    class Config:
        use_enum_values = True


class PLCAddOnInstruction(BaseModel):
    """Represents an Add-On Instruction (AOI)."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    comment: Optional[str] = None
    revision: Optional[str] = None
    parameters: List[PLCParameter] = Field(default_factory=list)
    local_tags: List[PLCTag] = Field(default_factory=list)
    routines: List[PLCRoutine] = Field(default_factory=list)
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class PLCProgram(BaseModel):
    """Represents a PLC program."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: Optional[str] = None
    comment: Optional[str] = None
    main_routine: Optional[str] = None
    fault_routine: Optional[str] = None
    routines: List[PLCRoutine] = Field(default_factory=list)
    tags: List[PLCTag] = Field(default_factory=list)
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class PLCDevice(BaseModel):
    """Represents a PLC I/O device or module."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    catalog_number: Optional[str] = None
    product_code: Optional[int] = None
    vendor_id: Optional[int] = None
    device_type: Optional[str] = None
    parent_module: Optional[str] = None
    slot: Optional[int] = None
    ip_address: Optional[str] = None
    comm_format: Optional[str] = None
    inhibited: bool = False
    keying: Optional[str] = None
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class PLCController(BaseModel):
    """Represents the PLC controller."""
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    processor_type: Optional[str] = None
    major_revision: Optional[int] = None
    minor_revision: Optional[int] = None
    time_slice: Optional[int] = None
    share_unused_time_slice: bool = True
    project_creation_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    description: Optional[str] = None
    comm_path: Optional[str] = None
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class PLCProject(BaseModel):
    """
    Unified representation of a PLC project that can be converted 
    between ACD and L5X formats.
    """
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    
    # Core components
    controller: PLCController
    programs: List[PLCProgram] = Field(default_factory=list)
    add_on_instructions: List[PLCAddOnInstruction] = Field(default_factory=list)
    user_defined_types: List[PLCUserDefinedType] = Field(default_factory=list)
    controller_tags: List[PLCTag] = Field(default_factory=list)
    devices: List[PLCDevice] = Field(default_factory=list)
    
    # Format-specific data preservation
    source_format: Optional[str] = None  # "ACD" or "L5X"
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    format_specific_data: Dict[str, Any] = Field(default_factory=dict)
    
    metadata: PLCMetadata = Field(default_factory=PLCMetadata)


class ConversionIssue(BaseModel):
    """Represents an issue encountered during conversion."""
    severity: ConversionStatus
    component_type: PLCComponentType
    component_name: Optional[str] = None
    message: str
    details: Optional[str] = None
    suggested_action: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ConversionResult(BaseModel):
    """Result of a conversion operation."""
    success: bool
    status: ConversionStatus
    source_format: str
    target_format: str
    source_file: Optional[str] = None
    target_file: Optional[str] = None
    conversion_time: Optional[float] = None
    project: Optional[PLCProject] = None
    issues: List[ConversionIssue] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """Check if conversion has any errors."""
        return any(issue.severity == ConversionStatus.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if conversion has any warnings."""
        return any(issue.severity == ConversionStatus.WARNING for issue in self.issues)
    
    class Config:
        use_enum_values = True


class ConversionError(Exception):
    """Exception raised during conversion operations."""
    
    def __init__(
        self, 
        message: str, 
        component_type: Optional[PLCComponentType] = None,
        component_name: Optional[str] = None,
        details: Optional[str] = None
    ):
        self.message = message
        self.component_type = component_type
        self.component_name = component_name
        self.details = details
        super().__init__(self.message)


class ValidationError(ConversionError):
    """Exception raised during validation operations."""
    pass


class FormatError(ConversionError):
    """Exception raised for format-specific errors."""
    pass 