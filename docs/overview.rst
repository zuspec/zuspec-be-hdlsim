Overview
========

What is Zuspec Backend HDLSim?
-------------------------------

Zuspec Backend HDLSim is a backend for the Zuspec verification framework that enables 
co-simulation between Python-based Zuspec testbenches and HDL (Hardware Description Language) 
designs in SystemVerilog/Verilog simulators.

Key Capabilities
----------------

* **HDL Co-Simulation**: Run Zuspec tests that drive and monitor actual HDL designs in 
  simulators like Verilator, VCS, or ModelSim
  
* **Transactor Generation**: Automatically generate SystemVerilog transactor modules 
  from Zuspec component definitions
  
* **Python/SV Bridge**: Seamless communication between Python test code and SystemVerilog 
  through PyHDL-IF
  
* **DV Flow Integration**: Integrate with DV Flow Manager (DFM) for automated build and 
  run workflows

When to Use HDLSim Backend
---------------------------

Use the HDLSim backend when you need to:

* Verify RTL designs with Zuspec-based testbenches
* Reuse existing SystemVerilog IP in Zuspec environments
* Execute performance-critical verification paths in hardware simulation
* Bridge between abstract Zuspec models and RTL implementations

Architecture Approach
---------------------

The HDLSim backend partitions your testbench into two domains:

**SystemVerilog Domain** (runs in simulator):
  * Extern components (existing HDL modules)
  * XtorComponent transactors (generated from Zuspec)
  * Signal-level connectivity

**Python Domain** (runs in pytest via PyHDL-IF):
  * Top-level test orchestration
  * Test scenarios and sequences
  * Pure Python components
  * High-level transactions

These domains communicate through PyHDL-IF's Python/SV bridge, with the HDLSim backend 
handling the code generation and integration automatically.

Comparison with Other Zuspec Backends
--------------------------------------

+------------------+------------------------+-------------------------+
| Backend          | Execution              | Use Case                |
+==================+========================+=========================+
| hdlsim           | HDL Simulator          | RTL verification        |
+------------------+------------------------+-------------------------+
| dataclasses      | Pure Python            | Model development       |
+------------------+------------------------+-------------------------+
| sv               | Pure SystemVerilog     | Embedded testbenches    |
+------------------+------------------------+-------------------------+

Next Steps
----------

* :doc:`architecture` - Understand the technical architecture
* :doc:`quickstart` - Get started with your first HDL testbench
* :doc:`components` - Learn about component types and profiles
