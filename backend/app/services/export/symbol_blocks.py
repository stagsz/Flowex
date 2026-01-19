"""ISO 10628 symbol block definitions for DXF export."""

from dataclasses import dataclass
from typing import Any

import ezdxf
from ezdxf.document import Drawing as DXFDocument


@dataclass
class ConnectionPoint:
    """Symbol connection point (nozzle/port)."""
    name: str
    x: float
    y: float


@dataclass
class SymbolBlockDefinition:
    """Definition of a P&ID symbol block."""
    name: str
    category: str  # equipment, instrument, valve, other
    geometry: list[dict[str, Any]]
    attributes: list[dict[str, Any]]
    connection_points: list[ConnectionPoint]
    base_point: tuple[float, float] = (0.0, 0.0)


# Standard sizes for symbols (in mm)
EQUIPMENT_SIZE = 40.0
INSTRUMENT_SIZE = 15.0
VALVE_SIZE = 12.0


def _create_circle(msp: Any, cx: float, cy: float, radius: float) -> None:
    """Add a circle to the block."""
    msp.add_circle((cx, cy), radius)


def _create_line(msp: Any, x1: float, y1: float, x2: float, y2: float) -> None:
    """Add a line to the block."""
    msp.add_line((x1, y1), (x2, y2))


def _create_arc(
    msp: Any, cx: float, cy: float, radius: float, start_angle: float, end_angle: float
) -> None:
    """Add an arc to the block."""
    msp.add_arc((cx, cy), radius, start_angle, end_angle)


def _create_polyline(msp: Any, points: list[tuple[float, float]], close: bool = False) -> None:
    """Add a polyline to the block."""
    msp.add_lwpolyline(points, close=close)


def _create_rectangle(msp: Any, x: float, y: float, width: float, height: float) -> None:
    """Add a rectangle (closed polyline) to the block."""
    points = [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    ]
    msp.add_lwpolyline(points, close=True)


class ISO10628BlockLibrary:
    """Library of ISO 10628 P&ID symbol blocks."""

    def __init__(self, doc: DXFDocument):
        self.doc = doc
        self._created_blocks: set[str] = set()

    def get_or_create_block(self, symbol_class: str) -> str:
        """Get or create a block for the given symbol class."""
        block_name = self._normalize_block_name(symbol_class)

        if block_name in self._created_blocks:
            return block_name

        # Create the block based on symbol class
        creator_method = self._get_block_creator(symbol_class)
        if creator_method:
            creator_method(block_name)
            self._created_blocks.add(block_name)
        else:
            # Create generic block for unknown symbols
            self._create_generic_block(block_name)
            self._created_blocks.add(block_name)

        return block_name

    def _normalize_block_name(self, symbol_class: str) -> str:
        """Normalize symbol class to valid DXF block name."""
        return symbol_class.upper().replace(" ", "_")

    def _get_block_creator(self, symbol_class: str):
        """Get the block creator method for a symbol class."""
        creators = {
            # Equipment symbols
            "Vessel_Vertical": self._create_vessel_vertical,
            "Vessel_Horizontal": self._create_vessel_horizontal,
            "Tank_Atmospheric": self._create_tank_atmospheric,
            "Column_Distillation": self._create_column_distillation,
            "Heat_Exchanger_Shell_Tube": self._create_heat_exchanger_shell_tube,
            "Heat_Exchanger_Plate": self._create_heat_exchanger_plate,
            "Pump_Centrifugal": self._create_pump_centrifugal,
            "Pump_Positive_Displacement": self._create_pump_positive_displacement,
            "Compressor_Centrifugal": self._create_compressor_centrifugal,
            "Compressor_Reciprocating": self._create_compressor_reciprocating,
            "Filter": self._create_filter,
            "Reactor": self._create_reactor,
            "Furnace": self._create_furnace,
            "Blower": self._create_blower,
            "Agitator": self._create_agitator,
            # Instrument symbols
            "Transmitter_Pressure": self._create_transmitter_circle,
            "Transmitter_Temperature": self._create_transmitter_circle,
            "Transmitter_Flow": self._create_transmitter_circle,
            "Transmitter_Level": self._create_transmitter_circle,
            "Controller_Generic": self._create_controller,
            "Indicator_Generic": self._create_indicator,
            "Alarm_High": self._create_alarm,
            "Alarm_Low": self._create_alarm,
            "Switch_Generic": self._create_switch,
            "Control_Valve_Globe": self._create_control_valve,
            "Control_Valve_Butterfly": self._create_control_valve_butterfly,
            "Orifice_Plate": self._create_orifice_plate,
            "Thermowell": self._create_thermowell,
            "Sample_Point": self._create_sample_point,
            "Relief_Valve_Instrument": self._create_relief_valve,
            # Valve symbols
            "Valve_Gate": self._create_valve_gate,
            "Valve_Globe": self._create_valve_globe,
            "Valve_Ball": self._create_valve_ball,
            "Valve_Butterfly": self._create_valve_butterfly,
            "Valve_Check": self._create_valve_check,
            "Valve_Relief_PSV": self._create_valve_relief_psv,
            "Valve_Control": self._create_control_valve,
            "Valve_Three_Way": self._create_valve_three_way,
            "Valve_Diaphragm": self._create_valve_diaphragm,
            "Valve_Plug": self._create_valve_plug,
            "Valve_Needle": self._create_valve_needle,
            "Valve_Manual_Generic": self._create_valve_manual_generic,
            "Actuator_Pneumatic": self._create_actuator_pneumatic,
            "Actuator_Electric": self._create_actuator_electric,
            "Actuator_Hydraulic": self._create_actuator_hydraulic,
            # Other symbols
            "Reducer": self._create_reducer,
            "Flange": self._create_flange,
            "Spectacle_Blind": self._create_spectacle_blind,
            "Strainer": self._create_strainer,
            "Steam_Trap": self._create_steam_trap,
        }
        return creators.get(symbol_class)

    # ========== Equipment Symbol Creators ==========

    def _create_vessel_vertical(self, block_name: str) -> None:
        """Create vertical vessel block (cylinder with dished ends)."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Vertical cylinder
        _create_line(block, -s / 4, -s / 2, -s / 4, s / 2)
        _create_line(block, s / 4, -s / 2, s / 4, s / 2)
        # Top dished head (arc)
        _create_arc(block, 0, s / 2, s / 4, 0, 180)
        # Bottom dished head (arc)
        _create_arc(block, 0, -s / 2, s / 4, 180, 360)

    def _create_vessel_horizontal(self, block_name: str) -> None:
        """Create horizontal vessel block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Horizontal cylinder
        _create_line(block, -s / 2, -s / 4, s / 2, -s / 4)
        _create_line(block, -s / 2, s / 4, s / 2, s / 4)
        # Left dished head
        _create_arc(block, -s / 2, 0, s / 4, 90, 270)
        # Right dished head
        _create_arc(block, s / 2, 0, s / 4, 270, 90)

    def _create_tank_atmospheric(self, block_name: str) -> None:
        """Create atmospheric tank block (open top)."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Tank body (rectangle with open top)
        _create_line(block, -s / 3, -s / 2, -s / 3, s / 3)
        _create_line(block, s / 3, -s / 2, s / 3, s / 3)
        _create_line(block, -s / 3, -s / 2, s / 3, -s / 2)
        # Roof indication (slight angle)
        _create_line(block, -s / 3, s / 3, 0, s / 2)
        _create_line(block, s / 3, s / 3, 0, s / 2)

    def _create_column_distillation(self, block_name: str) -> None:
        """Create distillation column block (tall vessel with trays)."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE * 1.5
        w = s / 4
        # Column body
        _create_line(block, -w, -s / 2, -w, s / 2)
        _create_line(block, w, -s / 2, w, s / 2)
        # Top and bottom
        _create_arc(block, 0, s / 2, w, 0, 180)
        _create_arc(block, 0, -s / 2, w, 180, 360)
        # Internal trays (horizontal lines)
        for i in range(-2, 3):
            y = i * s / 6
            _create_line(block, -w, y, w, y)

    def _create_heat_exchanger_shell_tube(self, block_name: str) -> None:
        """Create shell and tube heat exchanger block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Shell (ellipse approximation)
        _create_circle(block, 0, 0, s / 3)
        # Tube bundle indication (diagonal lines)
        _create_line(block, -s / 4, -s / 4, s / 4, s / 4)
        _create_line(block, -s / 4, s / 4, s / 4, -s / 4)

    def _create_heat_exchanger_plate(self, block_name: str) -> None:
        """Create plate heat exchanger block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Rectangular body with zigzag pattern
        _create_rectangle(block, -s / 3, -s / 3, 2 * s / 3, 2 * s / 3)
        # Plate pattern (zigzag)
        pts = [(-s / 4, -s / 4), (s / 4, 0), (-s / 4, s / 4)]
        _create_polyline(block, pts)

    def _create_pump_centrifugal(self, block_name: str) -> None:
        """Create centrifugal pump block (circle with discharge)."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Pump casing (circle)
        _create_circle(block, 0, 0, s / 3)
        # Suction line
        _create_line(block, -s / 2, 0, -s / 3, 0)
        # Discharge (tangential)
        _create_line(block, 0, s / 3, 0, s / 2)
        _create_line(block, 0, s / 3, s / 4, s / 3)
        _create_line(block, s / 4, s / 3, s / 4, s / 2)

    def _create_pump_positive_displacement(self, block_name: str) -> None:
        """Create positive displacement pump block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Rectangular body
        _create_rectangle(block, -s / 3, -s / 4, 2 * s / 3, s / 2)
        # Inlet/outlet lines
        _create_line(block, -s / 2, 0, -s / 3, 0)
        _create_line(block, s / 3, 0, s / 2, 0)
        # Piston indication (triangle)
        pts = [(-s / 6, -s / 6), (s / 6, 0), (-s / 6, s / 6)]
        _create_polyline(block, pts, close=True)

    def _create_compressor_centrifugal(self, block_name: str) -> None:
        """Create centrifugal compressor block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Circle with impeller indication
        _create_circle(block, 0, 0, s / 3)
        # Impeller blades
        for angle in [0, 90, 180, 270]:
            import math
            rad = math.radians(angle)
            x1, y1 = s / 6 * math.cos(rad), s / 6 * math.sin(rad)
            x2, y2 = s / 3 * math.cos(rad), s / 3 * math.sin(rad)
            _create_line(block, x1, y1, x2, y2)

    def _create_compressor_reciprocating(self, block_name: str) -> None:
        """Create reciprocating compressor block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Cylinder
        _create_rectangle(block, -s / 3, -s / 4, 2 * s / 3, s / 2)
        # Piston rod
        _create_line(block, s / 3, 0, s / 2, 0)
        # Crosshead
        _create_circle(block, s / 2, 0, s / 8)

    def _create_filter(self, block_name: str) -> None:
        """Create filter block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Triangle shape
        pts = [(-s / 3, -s / 3), (s / 3, -s / 3), (0, s / 3)]
        _create_polyline(block, pts, close=True)

    def _create_reactor(self, block_name: str) -> None:
        """Create reactor vessel block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Vessel with jacket indication
        _create_circle(block, 0, 0, s / 3)
        _create_circle(block, 0, 0, s / 2.5)
        # Agitator shaft
        _create_line(block, 0, -s / 2, 0, s / 2)

    def _create_furnace(self, block_name: str) -> None:
        """Create furnace/heater block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Box with flame indication
        _create_rectangle(block, -s / 3, -s / 3, 2 * s / 3, 2 * s / 3)
        # Flame symbol (zigzag)
        pts = [(-s / 6, -s / 6), (0, s / 6), (s / 6, -s / 6)]
        _create_polyline(block, pts)

    def _create_blower(self, block_name: str) -> None:
        """Create blower/fan block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Circle with fan blades
        _create_circle(block, 0, 0, s / 3)
        import math
        for angle in [0, 120, 240]:
            rad = math.radians(angle)
            x1, y1 = 0, 0
            x2, y2 = s / 3 * math.cos(rad), s / 3 * math.sin(rad)
            _create_line(block, x1, y1, x2, y2)

    def _create_agitator(self, block_name: str) -> None:
        """Create agitator/mixer block."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE
        # Motor
        _create_rectangle(block, -s / 6, s / 4, s / 3, s / 4)
        # Shaft
        _create_line(block, 0, s / 4, 0, -s / 4)
        # Impeller
        _create_line(block, -s / 4, -s / 4, s / 4, -s / 4)

    # ========== Instrument Symbol Creators ==========

    def _create_transmitter_circle(self, block_name: str) -> None:
        """Create instrument transmitter (circle with horizontal line)."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        _create_circle(block, 0, 0, s / 2)
        _create_line(block, -s / 2, 0, s / 2, 0)

    def _create_controller(self, block_name: str) -> None:
        """Create controller block (square)."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        _create_rectangle(block, -s / 2, -s / 2, s, s)
        _create_line(block, -s / 2, 0, s / 2, 0)

    def _create_indicator(self, block_name: str) -> None:
        """Create indicator block (circle)."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        _create_circle(block, 0, 0, s / 2)

    def _create_alarm(self, block_name: str) -> None:
        """Create alarm block (hexagon)."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        import math
        pts = []
        for i in range(6):
            angle = math.radians(60 * i + 30)
            pts.append((s / 2 * math.cos(angle), s / 2 * math.sin(angle)))
        _create_polyline(block, pts, close=True)

    def _create_switch(self, block_name: str) -> None:
        """Create switch block (diamond)."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        pts = [(0, s / 2), (s / 2, 0), (0, -s / 2), (-s / 2, 0)]
        _create_polyline(block, pts, close=True)

    def _create_control_valve(self, block_name: str) -> None:
        """Create control valve block (two triangles)."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles meeting at center (bowtie shape)
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)
        # Actuator stem
        _create_line(block, 0, 0, 0, s / 2)
        _create_circle(block, 0, s / 2 + s / 4, s / 4)

    def _create_control_valve_butterfly(self, block_name: str) -> None:
        """Create butterfly control valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles (butterfly shape)
        pts1 = [(-s / 2, 0), (0, -s / 3), (0, s / 3)]
        pts2 = [(s / 2, 0), (0, -s / 3), (0, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)

    def _create_orifice_plate(self, block_name: str) -> None:
        """Create orifice plate block."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        # Two vertical lines with restriction
        _create_line(block, -s / 4, -s / 2, -s / 4, s / 2)
        _create_line(block, s / 4, -s / 2, s / 4, s / 2)
        # Horizontal lines at top and bottom
        _create_line(block, -s / 4, -s / 2, s / 4, -s / 2)
        _create_line(block, -s / 4, s / 2, s / 4, s / 2)

    def _create_thermowell(self, block_name: str) -> None:
        """Create thermowell block."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        # Rectangular insertion point
        _create_rectangle(block, -s / 6, -s / 2, s / 3, s)

    def _create_sample_point(self, block_name: str) -> None:
        """Create sample point block."""
        block = self.doc.blocks.new(name=block_name)
        s = INSTRUMENT_SIZE
        # Circle with S inside
        _create_circle(block, 0, 0, s / 2)

    def _create_relief_valve(self, block_name: str) -> None:
        """Create relief valve (instrument type) block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Triangle pointing up with spring
        pts = [(-s / 3, -s / 3), (0, s / 3), (s / 3, -s / 3)]
        _create_polyline(block, pts, close=True)
        # Spring indication
        _create_line(block, 0, s / 3, 0, s / 2)

    # ========== Valve Symbol Creators ==========

    def _create_valve_gate(self, block_name: str) -> None:
        """Create gate valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles (bowtie)
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)

    def _create_valve_globe(self, block_name: str) -> None:
        """Create globe valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles (bowtie) with globe indication
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)
        _create_circle(block, 0, 0, s / 6)

    def _create_valve_ball(self, block_name: str) -> None:
        """Create ball valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles with filled circle
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)

    def _create_valve_butterfly(self, block_name: str) -> None:
        """Create butterfly valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles pointing inward
        pts1 = [(-s / 2, 0), (0, -s / 3), (0, s / 3)]
        pts2 = [(s / 2, 0), (0, -s / 3), (0, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)

    def _create_valve_check(self, block_name: str) -> None:
        """Create check valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Triangle with vertical line
        pts = [(-s / 2, -s / 3), (s / 4, 0), (-s / 2, s / 3)]
        _create_polyline(block, pts, close=True)
        _create_line(block, s / 4, -s / 3, s / 4, s / 3)

    def _create_valve_relief_psv(self, block_name: str) -> None:
        """Create relief/safety valve (PSV) block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Angled triangle
        pts = [(-s / 3, -s / 3), (s / 3, 0), (-s / 3, s / 3)]
        _create_polyline(block, pts, close=True)
        # Spring symbol
        _create_line(block, 0, s / 4, 0, s / 2)
        _create_line(block, -s / 6, s / 2, s / 6, s / 2)

    def _create_valve_three_way(self, block_name: str) -> None:
        """Create three-way valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # T-shaped valve body
        _create_circle(block, 0, 0, s / 3)
        _create_line(block, -s / 2, 0, -s / 3, 0)
        _create_line(block, s / 3, 0, s / 2, 0)
        _create_line(block, 0, s / 3, 0, s / 2)

    def _create_valve_diaphragm(self, block_name: str) -> None:
        """Create diaphragm valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles with curved top
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)
        _create_arc(block, 0, s / 4, s / 4, 0, 180)

    def _create_valve_plug(self, block_name: str) -> None:
        """Create plug valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)
        # Plug indicator (vertical line through center)
        _create_line(block, 0, -s / 4, 0, s / 4)

    def _create_valve_needle(self, block_name: str) -> None:
        """Create needle valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two triangles with point indication
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)
        # Needle indication
        _create_line(block, 0, 0, 0, s / 4)

    def _create_valve_manual_generic(self, block_name: str) -> None:
        """Create generic manual valve block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Standard bowtie shape
        pts1 = [(-s / 2, -s / 3), (0, 0), (-s / 2, s / 3)]
        pts2 = [(s / 2, -s / 3), (0, 0), (s / 2, s / 3)]
        _create_polyline(block, pts1, close=True)
        _create_polyline(block, pts2, close=True)

    def _create_actuator_pneumatic(self, block_name: str) -> None:
        """Create pneumatic actuator block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Diaphragm actuator (circle)
        _create_circle(block, 0, s / 3, s / 4)
        # Stem
        _create_line(block, 0, 0, 0, s / 3 - s / 4)

    def _create_actuator_electric(self, block_name: str) -> None:
        """Create electric actuator block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Motor (rectangle)
        _create_rectangle(block, -s / 4, s / 4, s / 2, s / 3)
        # Stem
        _create_line(block, 0, 0, 0, s / 4)
        # M for motor
        block.add_text("M", dxfattribs={"height": s / 6}).set_placement((0, s / 4 + s / 6))

    def _create_actuator_hydraulic(self, block_name: str) -> None:
        """Create hydraulic actuator block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Cylinder (rectangle)
        _create_rectangle(block, -s / 4, s / 4, s / 2, s / 3)
        # Stem
        _create_line(block, 0, 0, 0, s / 4)

    # ========== Other Symbol Creators ==========

    def _create_reducer(self, block_name: str) -> None:
        """Create pipe reducer block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Concentric reducer shape
        pts = [(-s / 2, -s / 4), (s / 2, -s / 6), (s / 2, s / 6), (-s / 2, s / 4)]
        _create_polyline(block, pts, close=True)

    def _create_flange(self, block_name: str) -> None:
        """Create flange block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two parallel lines
        _create_line(block, 0, -s / 3, 0, s / 3)
        _create_line(block, s / 6, -s / 3, s / 6, s / 3)

    def _create_spectacle_blind(self, block_name: str) -> None:
        """Create spectacle blind block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Two circles connected (figure 8)
        _create_circle(block, -s / 3, 0, s / 4)
        _create_circle(block, s / 3, 0, s / 4)
        _create_line(block, -s / 3 + s / 4, 0, s / 3 - s / 4, 0)

    def _create_strainer(self, block_name: str) -> None:
        """Create strainer/filter block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Y-strainer shape
        _create_line(block, -s / 2, 0, 0, 0)
        _create_line(block, 0, 0, s / 2, 0)
        _create_line(block, 0, 0, 0, -s / 2)
        _create_circle(block, 0, -s / 2, s / 6)

    def _create_steam_trap(self, block_name: str) -> None:
        """Create steam trap block."""
        block = self.doc.blocks.new(name=block_name)
        s = VALVE_SIZE
        # Inverted bucket shape
        _create_rectangle(block, -s / 4, -s / 3, s / 2, s * 2 / 3)
        # Internal bucket indication
        _create_arc(block, 0, 0, s / 6, 0, 180)

    def _create_generic_block(self, block_name: str) -> None:
        """Create generic block for unknown symbol types."""
        block = self.doc.blocks.new(name=block_name)
        s = EQUIPMENT_SIZE / 2
        # Simple rectangle with X
        _create_rectangle(block, -s / 2, -s / 2, s, s)
        _create_line(block, -s / 2, -s / 2, s / 2, s / 2)
        _create_line(block, -s / 2, s / 2, s / 2, -s / 2)
