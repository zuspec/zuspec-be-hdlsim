# Zuspec Backend HDLSim

This backend package supports co-simulating Zuspec descriptions with
existing HDL (eg Verilog) designs. This process starts with a single top-level
Zuspec component class that instances all required elements:
- Extern classes that specify how existing Verilog sources are integrated
- XtorComponent classes that specify generation of Verilog transactors
  and their integration with Python
- Zuspec component classes that stay in Python
- Zuspec component classes that are retargetable, and could be implemented in SV

This description is processed two ways to create two views of the design:
- By a SystemVerilog generator that implements the portion simulated by the
  hardware simulator. This generator is called during the build flow
- By a Python runtime generator (similar to what's in 'rt' of zuspec-dataclasses)
  that produces an executable Python implementation for behavior that stays
  in Python (at minimum, the top level). This generator runs when the simulator
  runs and launches Zuspec. The implementation must attach to the elements 
  exposed by the simulation

## Initial Assumptions
- All Extern-derived component classes are implemented in SV
- All XtorComponent-derived classes generate SV code and are implemented in SV
- Everything else is implemented in Python
- Critical: A Python-implemented component cannot connect at the signal level
  to a SV-implemented component.

We will revisit these assumptions in the future as we make things more flexible.

## Checker
zuspec-dataclasses provides a Profile-driven checker framework. hdlsim must 
define an HDLTestbench profile and companion checker. This checker must enforce
rules, such as signal-level connection between domains.

## Operation: SV Generator
The SystemVerilog generator accepts the top-level testbench Zuspec component
class and generates SV for the elements that must be in SystemVerilog.

It creates two modules:
- <TBComp>_hdl: Implements the 'HDL' portions of the Zuspec description. Instances
  extern components and Xtors; Connects their input/output signals as required.
- <TBComp>: top-level module responsible for connecting HDL components to
  Python, and launching the Pytest at simulation runtime. This module instances
  the '_hdl' module.

Generation of XtorComponents is two-step:
- The SV generator (zuspec-be-sv) is used to produce the SystemVerilog portions 
  of the transactor
- A generator in hdlsim produces the PyHDL-IF wrapper classes. Let's define a
  proper public generator interface for PyHDL-IF as part of this project so we
  can call something reliable.

### SV / Python Connection
On startup (initial block), the <TBComp> module must:
- Create 

## Operation: Python Generator
The Python generator is an ObjFactory-like class that produces an executable Python
object having the same API as the input Zuspec class. This generator will be invoked
from within a simulation, and can access (via PyHDL-IF) wrapper classes registered
by the <TbComp> module prior to launching the pytest.

## DV Flow Manager Integration

The HDL generator must be packed as a DFM task. A parameter on the task specifies
the root Zuspec Testbench component typename. This task outputs filesets that specify
the ordered SV sources to be compiled.


## Zuspec Dataclasses Additions

