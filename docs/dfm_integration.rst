DV Flow Manager Integration
============================

The HDLSim backend integrates with DV Flow Manager (DFM) to automate the build 
and run workflows for HDL testbenches.

Overview
--------

DFM provides a declarative, task-based workflow system for verification flows. 
The HDLSim backend provides a ``GenTB`` task that generates SystemVerilog 
testbenches from Zuspec components, which can then be compiled and run by 
simulator-specific tasks.

GenTB Task
----------

The ``GenTB`` task is the primary integration point with DFM.

Task Definition
^^^^^^^^^^^^^^^

.. code-block:: python

    from zuspec.be.hdlsim.dfm import GenTB

**Module**: ``zuspec.be.hdlsim.dfm.gen_tb``

**Class**: ``GenTB``

Parameters
^^^^^^^^^^

* **class_name** (required): Fully qualified Python path to testbench component class
  
  Example: ``"my_package.testbenches.CounterTB"``

Outputs
^^^^^^^

The GenTB task produces:

* **sv_files**: List of generated SystemVerilog files
* **py_files**: List of generated Python test files
* **api_files**: PyHDL-IF API definition JSON files
* **filesets**: Ordered compilation fileset including:
  
  - Generated transactor modules
  - Generated testbench modules
  - Extern component sources

Task Result Data
^^^^^^^^^^^^^^^^

The task result includes:

.. code-block:: python

    {
        "generated_files": {
            "sv": ["path/to/TB_tb.sv", "path/to/TB_hdl.sv", ...],
            "py": ["path/to/test_tb.py"],
            "api": ["path/to/Xtor_api.json", ...]
        },
        "top_module": "TB_tb",
        "filesets": [...]
    }

Flow Specification Example
---------------------------

Complete Example
^^^^^^^^^^^^^^^^

.. code-block:: yaml

    package:
      name: wishbone_tb
      
      # Define external dependencies
      dependencies:
      - name: fwvip-wb-zuspec
        git: https://github.com/example/fwvip-wb-zuspec.git
        
      tasks:
      
      # Generate testbench from Zuspec
      - name: GenTB
        uses: zuspec.be.hdlsim.dfm.GenTB
        with:
          class_name: wb_testbench.WishboneTB
      
      # Compile with Verilator
      - name: VltCompile
        uses: hdlsim.vlt.SimImage
        needs: [GenTB]
        with:
          top_module: WishboneTB_tb
          vlt_flags:
            - --trace
            - --trace-structs
      
      # Run simulation
      - name: VltRun
        uses: hdlsim.vlt.SimRun
        needs: [VltCompile]
        with:
          plusargs:
            - pyhdl.pytest=test_wishbone.py::test_basic_write
          timeout: 10000
      
      # Run full test suite
      - name: VltRunAll
        uses: hdlsim.vlt.SimRun
        needs: [VltCompile]
        with:
          plusargs:
            - pyhdl.pytest=test_wishbone.py
          timeout: 60000

Simulator Integration
---------------------

The generated testbench works with various simulators through DFM tasks.

Verilator
^^^^^^^^^

.. code-block:: yaml

    - name: VltImage
      uses: hdlsim.vlt.SimImage
      needs: [GenTB]
      with:
        top_module: ${{ tasks.GenTB.outputs.top_module }}
        sources: ${{ tasks.GenTB.outputs.filesets }}
        vlt_flags:
          - --trace
          - --trace-fst

VCS
^^^

.. code-block:: yaml

    - name: VcsImage
      uses: hdlsim.vcs.SimImage
      needs: [GenTB]
      with:
        top_module: ${{ tasks.GenTB.outputs.top_module }}
        sources: ${{ tasks.GenTB.outputs.filesets }}
        vcs_flags:
          - -debug_access+all

Questa/ModelSim
^^^^^^^^^^^^^^^

.. code-block:: yaml

    - name: QuestaImage
      uses: hdlsim.questa.SimImage
      needs: [GenTB]
      with:
        top_module: ${{ tasks.GenTB.outputs.top_module }}
        sources: ${{ tasks.GenTB.outputs.filesets }}

Running Tasks
-------------

Command Line
^^^^^^^^^^^^

.. code-block:: bash

    # Generate testbench only
    dfm run GenTB
    
    # Compile simulator image
    dfm run VltCompile
    
    # Run specific test
    dfm run VltRun
    
    # Run all tests
    dfm run VltRunAll
    
    # Run multiple tasks
    dfm run VltCompile VltRun

Task Dependencies
^^^^^^^^^^^^^^^^^

DFM automatically handles task dependencies. In this flow:

.. mermaid::

   flowchart LR
       GenTB --> VltCompile --> VltRun
       
       style GenTB fill:#e1f5ff
       style VltCompile fill:#ffe1e1
       style VltRun fill:#e1ffe1

Running ``dfm run VltRun`` will automatically:

1. Check if GenTB outputs are available
2. Run GenTB if needed
3. Check if VltCompile outputs are available
4. Run VltCompile if needed
5. Run VltRun

Advanced Patterns
-----------------

Parametric Generation
^^^^^^^^^^^^^^^^^^^^^

Generate multiple testbench variants:

.. code-block:: yaml

    tasks:
    - name: GenTB_Config1
      uses: zuspec.be.hdlsim.dfm.GenTB
      with:
        class_name: tb.MyTB
        params:
          data_width: 32
          
    - name: GenTB_Config2
      uses: zuspec.be.hdlsim.dfm.GenTB
      with:
        class_name: tb.MyTB
        params:
          data_width: 64

Multi-Test Execution
^^^^^^^^^^^^^^^^^^^^

Run different test scenarios:

.. code-block:: yaml

    tasks:
    - name: TestBasic
      uses: hdlsim.vlt.SimRun
      needs: [VltCompile]
      with:
        plusargs: [pyhdl.pytest=tests/test_basic.py]
        
    - name: TestStress
      uses: hdlsim.vlt.SimRun
      needs: [VltCompile]
      with:
        plusargs: [pyhdl.pytest=tests/test_stress.py]
        timeout: 120000

Regression Testing
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    tasks:
    - name: Regression
      uses: dfm.TaskGroup
      tasks:
        - TestBasic
        - TestStress
        - TestCornerCases
      parallel: true
      fail_fast: false

Working with Filesets
---------------------

Fileset Structure
^^^^^^^^^^^^^^^^^

GenTB outputs filesets in compilation order:

1. Package files (if any)
2. Extern component sources
3. Generated transactor modules
4. Generated testbench HDL module
5. Generated testbench wrapper module

Customizing Filesets
^^^^^^^^^^^^^^^^^^^^

You can add additional files to the compilation:

.. code-block:: yaml

    - name: VltCompile
      uses: hdlsim.vlt.SimImage
      needs: [GenTB]
      with:
        top_module: ${{ tasks.GenTB.outputs.top_module }}
        sources:
          - ${{ tasks.GenTB.outputs.filesets }}
          - additional/utility.sv
          - additional/assertions.sv

Debugging
---------

Generated File Inspection
^^^^^^^^^^^^^^^^^^^^^^^^^

Generated files are placed in the task's run directory:

.. code-block:: bash

    # View generated files
    ls -la .dfm/run/GenTB/generated/
    
    # Inspect testbench module
    cat .dfm/run/GenTB/generated/MyTB_tb.sv

Task Logging
^^^^^^^^^^^^

DFM provides task execution logs:

.. code-block:: bash

    # View task log
    dfm log GenTB
    
    # Tail running task
    dfm log -f VltRun

Error Handling
^^^^^^^^^^^^^^

If GenTB fails, check:

1. **Profile Validation**: Ensure component follows HDLTestbench profile rules
2. **Import Errors**: Verify testbench class can be imported
3. **Dependencies**: Check all required packages are installed

.. code-block:: bash

    # Test import manually
    python -c "from my_package import MyTB; print('OK')"
    
    # Check profile
    python -c "
    from my_package import MyTB
    from zuspec.be.hdlsim.checker import HDLTestbenchChecker
    checker = HDLTestbenchChecker()
    checker.check_component(MyTB)
    print(checker.get_errors())
    "

Best Practices
--------------

1. **Task Naming**: Use descriptive names (GenTB_ProjectName, VltRun_TestName)
2. **Dependencies**: Always specify ``needs`` to ensure correct execution order
3. **Parameterization**: Use task parameters for configurable generation
4. **Parallel Execution**: Mark independent tasks as ``parallel: true``
5. **Timeouts**: Set appropriate timeouts for simulation tasks
6. **Logging**: Use DFM logging to track execution and debug issues

See Also
--------

* `DV Flow Manager Documentation <https://github.com/dv-flow/dv-flow-mgr>`_
* :doc:`quickstart` - Basic workflow example
* :doc:`examples` - Complete testbench examples
