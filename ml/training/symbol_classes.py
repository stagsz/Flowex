"""
ISO 10628 P&ID Symbol Classes

Defines the 50 symbol classes used for P&ID digitization.
Based on ISO 10628-1:2014 and ISO 10628-2:2012 standards.
"""

from dataclasses import dataclass
from enum import Enum


class SymbolCategory(str, Enum):
    EQUIPMENT = "equipment"
    INSTRUMENT = "instrument"
    VALVE = "valve"
    PIPING = "piping"
    OTHER = "other"


@dataclass
class SymbolClass:
    id: int
    name: str
    category: SymbolCategory
    description: str
    iso_reference: str


# Define all 50 symbol classes
SYMBOL_CLASSES = [
    # Equipment (1-15)
    SymbolClass(1, "vessel_vertical", SymbolCategory.EQUIPMENT, "Vertical pressure vessel", "ISO 10628-2"),
    SymbolClass(2, "vessel_horizontal", SymbolCategory.EQUIPMENT, "Horizontal pressure vessel", "ISO 10628-2"),
    SymbolClass(3, "tank_atmospheric", SymbolCategory.EQUIPMENT, "Atmospheric storage tank", "ISO 10628-2"),
    SymbolClass(4, "tank_cone_roof", SymbolCategory.EQUIPMENT, "Cone roof tank", "ISO 10628-2"),
    SymbolClass(5, "pump_centrifugal", SymbolCategory.EQUIPMENT, "Centrifugal pump", "ISO 10628-2"),
    SymbolClass(6, "pump_positive", SymbolCategory.EQUIPMENT, "Positive displacement pump", "ISO 10628-2"),
    SymbolClass(7, "compressor", SymbolCategory.EQUIPMENT, "Compressor", "ISO 10628-2"),
    SymbolClass(8, "blower", SymbolCategory.EQUIPMENT, "Blower/Fan", "ISO 10628-2"),
    SymbolClass(9, "heat_exchanger_shell", SymbolCategory.EQUIPMENT, "Shell and tube heat exchanger", "ISO 10628-2"),
    SymbolClass(10, "heat_exchanger_plate", SymbolCategory.EQUIPMENT, "Plate heat exchanger", "ISO 10628-2"),
    SymbolClass(11, "cooler_air", SymbolCategory.EQUIPMENT, "Air cooler", "ISO 10628-2"),
    SymbolClass(12, "column_distillation", SymbolCategory.EQUIPMENT, "Distillation column", "ISO 10628-2"),
    SymbolClass(13, "reactor", SymbolCategory.EQUIPMENT, "Reactor vessel", "ISO 10628-2"),
    SymbolClass(14, "filter", SymbolCategory.EQUIPMENT, "Filter", "ISO 10628-2"),
    SymbolClass(15, "mixer", SymbolCategory.EQUIPMENT, "Mixer/Agitator", "ISO 10628-2"),

    # Instruments (16-35)
    SymbolClass(16, "instrument_local", SymbolCategory.INSTRUMENT, "Local instrument (circle)", "ISO 10628-2"),
    SymbolClass(17, "instrument_panel", SymbolCategory.INSTRUMENT, "Panel-mounted instrument", "ISO 10628-2"),
    SymbolClass(18, "instrument_dcs", SymbolCategory.INSTRUMENT, "DCS/PLC instrument", "ISO 10628-2"),
    SymbolClass(19, "transmitter_pressure", SymbolCategory.INSTRUMENT, "Pressure transmitter (PT)", "ISO 10628-2"),
    SymbolClass(20, "transmitter_temperature", SymbolCategory.INSTRUMENT, "Temperature transmitter (TT)", "ISO 10628-2"),
    SymbolClass(21, "transmitter_flow", SymbolCategory.INSTRUMENT, "Flow transmitter (FT)", "ISO 10628-2"),
    SymbolClass(22, "transmitter_level", SymbolCategory.INSTRUMENT, "Level transmitter (LT)", "ISO 10628-2"),
    SymbolClass(23, "indicator_pressure", SymbolCategory.INSTRUMENT, "Pressure indicator (PI)", "ISO 10628-2"),
    SymbolClass(24, "indicator_temperature", SymbolCategory.INSTRUMENT, "Temperature indicator (TI)", "ISO 10628-2"),
    SymbolClass(25, "indicator_flow", SymbolCategory.INSTRUMENT, "Flow indicator (FI)", "ISO 10628-2"),
    SymbolClass(26, "indicator_level", SymbolCategory.INSTRUMENT, "Level indicator (LI)", "ISO 10628-2"),
    SymbolClass(27, "controller", SymbolCategory.INSTRUMENT, "Controller (XC)", "ISO 10628-2"),
    SymbolClass(28, "alarm_high", SymbolCategory.INSTRUMENT, "High alarm (XAH)", "ISO 10628-2"),
    SymbolClass(29, "alarm_low", SymbolCategory.INSTRUMENT, "Low alarm (XAL)", "ISO 10628-2"),
    SymbolClass(30, "switch_pressure", SymbolCategory.INSTRUMENT, "Pressure switch (PSH/PSL)", "ISO 10628-2"),
    SymbolClass(31, "switch_temperature", SymbolCategory.INSTRUMENT, "Temperature switch (TSH/TSL)", "ISO 10628-2"),
    SymbolClass(32, "switch_level", SymbolCategory.INSTRUMENT, "Level switch (LSH/LSL)", "ISO 10628-2"),
    SymbolClass(33, "switch_flow", SymbolCategory.INSTRUMENT, "Flow switch (FSH/FSL)", "ISO 10628-2"),
    SymbolClass(34, "orifice_plate", SymbolCategory.INSTRUMENT, "Orifice plate", "ISO 10628-2"),
    SymbolClass(35, "control_valve_actuator", SymbolCategory.INSTRUMENT, "Control valve with actuator", "ISO 10628-2"),

    # Valves (36-48)
    SymbolClass(36, "valve_gate", SymbolCategory.VALVE, "Gate valve", "ISO 10628-2"),
    SymbolClass(37, "valve_globe", SymbolCategory.VALVE, "Globe valve", "ISO 10628-2"),
    SymbolClass(38, "valve_ball", SymbolCategory.VALVE, "Ball valve", "ISO 10628-2"),
    SymbolClass(39, "valve_butterfly", SymbolCategory.VALVE, "Butterfly valve", "ISO 10628-2"),
    SymbolClass(40, "valve_check", SymbolCategory.VALVE, "Check valve", "ISO 10628-2"),
    SymbolClass(41, "valve_relief", SymbolCategory.VALVE, "Relief/Safety valve", "ISO 10628-2"),
    SymbolClass(42, "valve_control", SymbolCategory.VALVE, "Control valve", "ISO 10628-2"),
    SymbolClass(43, "valve_3way", SymbolCategory.VALVE, "3-way valve", "ISO 10628-2"),
    SymbolClass(44, "valve_plug", SymbolCategory.VALVE, "Plug valve", "ISO 10628-2"),
    SymbolClass(45, "valve_needle", SymbolCategory.VALVE, "Needle valve", "ISO 10628-2"),
    SymbolClass(46, "valve_diaphragm", SymbolCategory.VALVE, "Diaphragm valve", "ISO 10628-2"),
    SymbolClass(47, "valve_solenoid", SymbolCategory.VALVE, "Solenoid valve", "ISO 10628-2"),
    SymbolClass(48, "valve_manual", SymbolCategory.VALVE, "Manual valve (generic)", "ISO 10628-2"),

    # Piping & Other (49-50)
    SymbolClass(49, "reducer", SymbolCategory.PIPING, "Pipe reducer", "ISO 10628-2"),
    SymbolClass(50, "blind_flange", SymbolCategory.PIPING, "Blind flange/Spectacle blind", "ISO 10628-2"),
]

# Create lookup dictionaries
SYMBOL_BY_ID = {s.id: s for s in SYMBOL_CLASSES}
SYMBOL_BY_NAME = {s.name: s for s in SYMBOL_CLASSES}
NUM_CLASSES = len(SYMBOL_CLASSES)

# Category groups for easier filtering
EQUIPMENT_SYMBOLS = [s for s in SYMBOL_CLASSES if s.category == SymbolCategory.EQUIPMENT]
INSTRUMENT_SYMBOLS = [s for s in SYMBOL_CLASSES if s.category == SymbolCategory.INSTRUMENT]
VALVE_SYMBOLS = [s for s in SYMBOL_CLASSES if s.category == SymbolCategory.VALVE]
PIPING_SYMBOLS = [s for s in SYMBOL_CLASSES if s.category == SymbolCategory.PIPING]


def get_class_names() -> list[str]:
    """Get list of all class names for model training."""
    return [s.name for s in SYMBOL_CLASSES]


def get_class_id(name: str) -> int:
    """Get class ID from name."""
    return SYMBOL_BY_NAME[name].id


def get_class_name(class_id: int) -> str:
    """Get class name from ID."""
    return SYMBOL_BY_ID[class_id].name
