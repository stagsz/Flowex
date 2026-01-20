/**
 * ISO 10628 P&ID Symbol Classes
 * Matches backend symbol definitions in backend/app/services/export/symbol_blocks.py
 */

export type SymbolCategory = "equipment" | "instrument" | "valve" | "other"

export interface SymbolClassDefinition {
  value: string
  label: string
  category: SymbolCategory
}

export const SYMBOL_CLASSES: SymbolClassDefinition[] = [
  // Equipment symbols
  { value: "Vessel_Vertical", label: "Vessel (Vertical)", category: "equipment" },
  { value: "Vessel_Horizontal", label: "Vessel (Horizontal)", category: "equipment" },
  { value: "Tank_Atmospheric", label: "Tank (Atmospheric)", category: "equipment" },
  { value: "Column_Distillation", label: "Column (Distillation)", category: "equipment" },
  { value: "Heat_Exchanger_Shell_Tube", label: "Heat Exchanger (Shell & Tube)", category: "equipment" },
  { value: "Heat_Exchanger_Plate", label: "Heat Exchanger (Plate)", category: "equipment" },
  { value: "Pump_Centrifugal", label: "Pump (Centrifugal)", category: "equipment" },
  { value: "Pump_Positive_Displacement", label: "Pump (Positive Displacement)", category: "equipment" },
  { value: "Compressor_Centrifugal", label: "Compressor (Centrifugal)", category: "equipment" },
  { value: "Compressor_Reciprocating", label: "Compressor (Reciprocating)", category: "equipment" },
  { value: "Filter", label: "Filter", category: "equipment" },
  { value: "Reactor", label: "Reactor", category: "equipment" },
  { value: "Furnace", label: "Furnace", category: "equipment" },
  { value: "Blower", label: "Blower", category: "equipment" },
  { value: "Agitator", label: "Agitator", category: "equipment" },

  // Instrument symbols
  { value: "Transmitter_Pressure", label: "Transmitter (Pressure)", category: "instrument" },
  { value: "Transmitter_Temperature", label: "Transmitter (Temperature)", category: "instrument" },
  { value: "Transmitter_Flow", label: "Transmitter (Flow)", category: "instrument" },
  { value: "Transmitter_Level", label: "Transmitter (Level)", category: "instrument" },
  { value: "Controller_Generic", label: "Controller", category: "instrument" },
  { value: "Indicator_Generic", label: "Indicator", category: "instrument" },
  { value: "Alarm_High", label: "Alarm (High)", category: "instrument" },
  { value: "Alarm_Low", label: "Alarm (Low)", category: "instrument" },
  { value: "Switch_Generic", label: "Switch", category: "instrument" },
  { value: "Control_Valve_Globe", label: "Control Valve (Globe)", category: "instrument" },
  { value: "Control_Valve_Butterfly", label: "Control Valve (Butterfly)", category: "instrument" },
  { value: "Orifice_Plate", label: "Orifice Plate", category: "instrument" },
  { value: "Thermowell", label: "Thermowell", category: "instrument" },
  { value: "Sample_Point", label: "Sample Point", category: "instrument" },
  { value: "Relief_Valve_Instrument", label: "Relief Valve (Instrument)", category: "instrument" },

  // Valve symbols
  { value: "Valve_Gate", label: "Gate Valve", category: "valve" },
  { value: "Valve_Globe", label: "Globe Valve", category: "valve" },
  { value: "Valve_Ball", label: "Ball Valve", category: "valve" },
  { value: "Valve_Butterfly", label: "Butterfly Valve", category: "valve" },
  { value: "Valve_Check", label: "Check Valve", category: "valve" },
  { value: "Valve_Relief_PSV", label: "Relief Valve (PSV)", category: "valve" },
  { value: "Valve_Control", label: "Control Valve", category: "valve" },
  { value: "Valve_Three_Way", label: "Three-Way Valve", category: "valve" },
  { value: "Valve_Diaphragm", label: "Diaphragm Valve", category: "valve" },
  { value: "Valve_Plug", label: "Plug Valve", category: "valve" },
  { value: "Valve_Needle", label: "Needle Valve", category: "valve" },
  { value: "Valve_Manual_Generic", label: "Manual Valve", category: "valve" },
  { value: "Actuator_Pneumatic", label: "Actuator (Pneumatic)", category: "valve" },
  { value: "Actuator_Electric", label: "Actuator (Electric)", category: "valve" },
  { value: "Actuator_Hydraulic", label: "Actuator (Hydraulic)", category: "valve" },

  // Other symbols
  { value: "Reducer", label: "Reducer", category: "other" },
  { value: "Flange", label: "Flange", category: "other" },
  { value: "Spectacle_Blind", label: "Spectacle Blind", category: "other" },
  { value: "Strainer", label: "Strainer", category: "other" },
  { value: "Steam_Trap", label: "Steam Trap", category: "other" },
]

// Group symbol classes by category for easier rendering
export const SYMBOL_CLASSES_BY_CATEGORY: Record<SymbolCategory, SymbolClassDefinition[]> = {
  equipment: SYMBOL_CLASSES.filter(s => s.category === "equipment"),
  instrument: SYMBOL_CLASSES.filter(s => s.category === "instrument"),
  valve: SYMBOL_CLASSES.filter(s => s.category === "valve"),
  other: SYMBOL_CLASSES.filter(s => s.category === "other"),
}

// Category labels for display
export const CATEGORY_LABELS: Record<SymbolCategory, string> = {
  equipment: "Equipment",
  instrument: "Instruments",
  valve: "Valves",
  other: "Other",
}

// Get symbol class definition by value
export function getSymbolClass(value: string): SymbolClassDefinition | undefined {
  return SYMBOL_CLASSES.find(s => s.value === value)
}

// Get display label for a symbol class value
export function getSymbolClassLabel(value: string): string {
  const def = getSymbolClass(value)
  return def?.label || value.replace(/_/g, " ")
}
