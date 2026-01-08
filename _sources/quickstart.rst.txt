Quick Start
===========

This guide walks you through creating your first HDL testbench with Zuspec HDLSim backend.

Prerequisites
-------------

* Python 3.9+
* Zuspec dataclasses
* PyHDL-IF
* HDL simulator (Verilator, VCS, etc.)
* DV Flow Manager (optional, for automated workflows)

Installation
------------

.. code-block:: bash

    pip install zuspec-be-hdlsim zuspec-dataclasses pyhdl-if

Step 1: Define Your Components
-------------------------------

Create a file ``my_testbench.py``:

.. code-block:: python

    import zuspec.dataclasses as zdc
    from zuspec.dataclasses.protocols import Extern, XtorComponent
    from zuspec.dataclasses import Signal, annotation_fileset
    
    # Define the DUT wrapper
    @zdc.dataclass
    class DutWrapper(zdc.Component, Extern):
        """Wrapper for existing counter.sv module."""
        
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        count_out: Signal = zdc.output()
        
        @annotation_fileset(sources=["rtl/counter.sv"])
        def __post_init__(self):
            pass
    
    # Define clock/reset transactor protocol
    class ClkRstIf:
        async def reset_pulse(self, cycles: int):
            """Assert reset for N cycles."""
            ...
        
        async def wait_cycles(self, cycles: int):
            """Wait for N clock cycles."""
            ...
    
    # Define clock/reset transactor
    @zdc.dataclass
    class ClkRstXtor(XtorComponent[ClkRstIf]):
        """Clock and reset generator."""
        
        clock: Signal = zdc.output()
        reset: Signal = zdc.output()
        
        # Implementation details handled by generator
    
    # Define top-level testbench
    @zdc.dataclass
    class CounterTB(zdc.Component):
        """Counter testbench."""
        
        dut: DutWrapper = zdc.inst()
        clkrst: ClkRstXtor = zdc.inst()
        
        def __bind__(self):
            """Define signal bindings."""
            return (
                (self.clkrst.clock, self.dut.clock),
                (self.clkrst.reset, self.dut.reset),
            )

Step 2: Create Your Test
-------------------------

Create ``test_counter.py``:

.. code-block:: python

    import pytest
    from zuspec.be.hdlsim import HDLSimRuntime
    from my_testbench import CounterTB
    
    @pytest.fixture
    def tb():
        """Testbench fixture."""
        # Runtime will be configured by SV before pytest runs
        return CounterTB()
    
    async def test_reset(tb):
        """Test counter reset behavior."""
        # Reset the DUT
        await tb.clkrst.reset_pulse(10)
        
        # Wait and observe
        await tb.clkrst.wait_cycles(100)
        
        # Assertions would go here
        assert True

Step 3: Create DFM Flow Specification
--------------------------------------

Create ``flow.yaml``:

.. code-block:: yaml

    package:
      name: counter_tb
      
      tasks:
      - name: GenTB
        uses: zuspec.be.hdlsim.dfm.GenTB
        with:
          class_name: my_testbench.CounterTB
          
      - name: SimImage
        uses: hdlsim.vlt.SimImage
        needs: [GenTB]
        with:
          top_module: CounterTB_tb
          
      - name: SimRun
        uses: hdlsim.vlt.SimRun
        needs: [SimImage]
        with:
          plusargs:
            - pyhdl.pytest=test_counter.py::test_reset

Step 4: Create RTL
------------------

Create ``rtl/counter.sv``:

.. code-block:: systemverilog

    module counter (
        input  logic       clock,
        input  logic       reset,
        output logic [7:0] count_out
    );
        logic [7:0] count;
        
        always_ff @(posedge clock) begin
            if (reset)
                count <= 8'h0;
            else
                count <= count + 1;
        end
        
        assign count_out = count;
    endmodule

Step 5: Generate and Run
-------------------------

Generate the testbench:

.. code-block:: bash

    dfm run GenTB

This produces:

* ``generated/CounterTB_hdl.sv`` - HDL module with component instances
* ``generated/CounterTB_tb.sv`` - Testbench wrapper module
* ``generated/ClkRstXtor.sv`` - Generated transactor
* ``generated/ClkRstXtor_api.json`` - PyHDL-IF API definition
* ``generated/test_countertb.py`` - Generated test wrapper

Build and run the simulation:

.. code-block:: bash

    dfm run SimImage   # Compile with Verilator
    dfm run SimRun     # Run simulation

What Happens at Runtime
------------------------

1. Verilator loads ``CounterTB_tb`` module
2. Initial block registers transactors with PyHDL-IF
3. Initial block calls ``pyhdl_pytest()``
4. pytest loads and runs ``test_counter.py``
5. Test accesses ``tb.clkrst`` which maps to SV transactor
6. Method calls cross Python/SV boundary via PyHDL-IF
7. Test completes, simulation finishes

Next Steps
----------

* :doc:`components` - Learn about component types in detail
* :doc:`dfm_integration` - Advanced DFM usage
* :doc:`examples` - More complex examples
* :doc:`api_reference` - API documentation

Troubleshooting
---------------

**Import errors**: Ensure all dependencies are installed:

.. code-block:: bash

    pip install -U zuspec-be-hdlsim zuspec-dataclasses pyhdl-if

**Generation fails**: Check that your component follows profile rules:

.. code-block:: python

    from zuspec.be.hdlsim.checker import HDLTestbenchChecker
    
    checker = HDLTestbenchChecker()
    checker.check_component(CounterTB)
    print(checker.get_errors())

**Runtime errors**: Verify PyHDL-IF registration in generated SV testbench module.
