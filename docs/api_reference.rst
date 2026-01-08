API Reference
=============

Core Modules
------------

zuspec.be.hdlsim
^^^^^^^^^^^^^^^^

Main module providing runtime integration.

.. py:class:: HDLSimRuntime

   Singleton runtime that manages testbench registration and factory configuration.
   
   .. py:method:: get_instance() -> HDLSimRuntime
      :classmethod:
      
      Get or create the singleton runtime instance.
      
   .. py:method:: register_tb_class(tb_class: Type) -> None
   
      Register a testbench class for this simulation. Called by generated SV.
      
      :param tb_class: Top-level testbench component class
      
   .. py:method:: get_registered_tb_class() -> Optional[Type]
   
      Get the currently registered testbench class.
      
      :returns: Registered testbench class or None

.. py:function:: configure_objfactory(tb_class_path: str) -> None

   Configure ObjFactory from SystemVerilog before launching pytest.
   
   :param tb_class_path: Fully qualified class path (e.g., "mymodule.MyTB")

zuspec.be.hdlsim.sv_generator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SystemVerilog code generation.

.. py:class:: SVTestbenchGenerator

   Generates SystemVerilog testbench from Zuspec component class.
   
   .. py:method:: __init__(top_component_cls)
   
      Initialize generator with top-level component.
      
      :param top_component_cls: Zuspec component class for top-level testbench
      
   .. py:method:: generate() -> Dict[str, str]
   
      Generate all SystemVerilog and Python files.
      
      :returns: Dictionary mapping filename to file content
      
   .. py:method:: get_source_filesets() -> List[Any]
   
      Get source filesets from all Extern components.
      
      :returns: List of AnnotationFileSet objects

zuspec.be.hdlsim.py_runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Python runtime factory for creating testbench proxies.

.. py:class:: PyTestbenchFactory

   Factory for creating executable Python testbench objects at simulation runtime.
   
   .. py:method:: __init__()
   
      Initialize factory with `PyHDL-IF <https://fvutils.github.io/pyhdl-if>`_ object registry.
      
   .. py:method:: create(component_cls: Type, inst_path: str = "top") -> Any
   
      Create executable instance of component class.
      
      :param component_cls: Zuspec component class
      :param inst_path: Hierarchical instance path
      :returns: Proxy object with connections to SV components

zuspec.be.hdlsim.checker
^^^^^^^^^^^^^^^^^^^^^^^^^

Profile validation and checking.

.. py:class:: HDLTestbenchChecker

   Validates HDLTestbench profile rules for domain separation.
   
   .. py:method:: __init__()
   
      Initialize checker with empty error list.
      
   .. py:method:: check_component(comp) -> None
   
      Check a component definition against profile rules.
      
      :param comp: Component class to validate
      
   .. py:method:: get_errors() -> List[str]
   
      Get list of validation errors found.
      
      :returns: List of error messages
      
   .. py:method:: has_errors() -> bool
   
      Check if any validation errors were found.
      
      :returns: True if errors exist

zuspec.be.hdlsim.profile
^^^^^^^^^^^^^^^^^^^^^^^^^

Profile definition for HDL testbenches.

.. py:data:: HDLTestbenchProfile

   Singleton profile instance for HDL testbench components.
   
   .. py:method:: get_checker()
   
      Return the HDLTestbenchChecker for this profile.
      
      :returns: HDLTestbenchChecker instance

zuspec.be.hdlsim.json_api_gen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`PyHDL-IF <https://fvutils.github.io/pyhdl-if>`_ API generation.

.. py:class:: TransactorJsonApiGenerator

   Generate `PyHDL-IF <https://fvutils.github.io/pyhdl-if>`_ JSON API definitions from XtorComponent classes.
   
   .. py:method:: __init__(xtor_cls, module_name: str = "generated_api")
   
      Initialize generator.
      
      :param xtor_cls: XtorComponent class
      :param module_name: Module name for generated API
      
   .. py:method:: generate() -> Dict[str, Any]
   
      Generate JSON API definition conforming to pyhdl-if.schema.json.
      
      :returns: Dictionary suitable for JSON serialization

zuspec.be.hdlsim.dfm.gen_tb
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`DV Flow Manager <https://dv-flow.github.io>`_ integration.

.. py:class:: GenTB

   `DFM <https://dv-flow.github.io>`_ task for generating HDL testbench from Zuspec component.
   
   .. py:method:: run(ctxt) -> TaskDataResult
      :async:
      
      Execute the testbench generation task.
      
      :param ctxt: Task context with rundir, params, log
      :returns: TaskDataResult with status and output files
      
   **Task Parameters**:
   
   * ``class_name`` (required): Fully qualified testbench class name
   
   **Task Outputs**:
   
   * ``sv_files``: List of generated SystemVerilog files
   * ``py_files``: List of generated Python files  
   * ``filesets``: Ordered compilation fileset

Type Definitions
----------------

Protocols
^^^^^^^^^

.. py:class:: Extern

   Protocol marker for external HDL components.
   
   Components inheriting from Extern are expected to provide SystemVerilog 
   source files via ``@annotation_fileset`` decorator.

.. py:class:: XtorComponent[ProtocolT]

   Generic base for transactor components.
   
   :param ProtocolT: Protocol class defining transaction-level API
   
   Transactors generate both SystemVerilog implementation and Python API wrapper.

Annotations
^^^^^^^^^^^

.. py:decorator:: annotation_fileset(sources: List[str], incdirs: List[str] = None, defines: Dict[str, str] = None)

   Annotate component with HDL source file information.
   
   :param sources: List of source file paths (relative or absolute)
   :param incdirs: Optional list of include directories
   :param defines: Optional dictionary of preprocessor defines
   
   Example::
   
       @annotation_fileset(
           sources=["rtl/dut.sv", "rtl/dut_pkg.sv"],
           incdirs=["rtl/include"],
           defines={"DEBUG": "1"}
       )
       def __post_init__(self):
           pass

Examples
--------

Basic Testbench
^^^^^^^^^^^^^^^

.. code-block:: python

    from zuspec.dataclasses import dataclass, Component, Signal
    from zuspec.dataclasses.protocols import Extern, XtorComponent
    from zuspec.be.hdlsim import HDLSimRuntime
    
    # Define protocol
    class MyProtocol:
        async def send(self, data: int): ...
    
    # Define components
    @dataclass
    class DUT(Component, Extern):
        clock: Signal = zdc.input()
        
        @annotation_fileset(sources=["dut.sv"])
        def __post_init__(self): pass
    
    @dataclass
    class Driver(XtorComponent[MyProtocol]):
        clock: Signal = zdc.input()
        data_out: Signal = zdc.output()
    
    @dataclass
    class TB(Component):
        dut: DUT = zdc.inst()
        drv: Driver = zdc.inst()
        
        def __bind__(self):
            return (
                (self.drv.clock, self.dut.clock),
                (self.drv.data_out, self.dut.data_in),
            )

Profile Checking
^^^^^^^^^^^^^^^^

.. code-block:: python

    from zuspec.be.hdlsim.checker import HDLTestbenchChecker
    
    # Create and run checker
    checker = HDLTestbenchChecker()
    checker.check_component(TB)
    
    # Handle errors
    if checker.has_errors():
        for error in checker.get_errors():
            print(f"Validation error: {error}")
        sys.exit(1)

SV Generation
^^^^^^^^^^^^^

.. code-block:: python

    from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
    
    # Generate files
    gen = SVTestbenchGenerator(TB)
    files = gen.generate()
    
    # Write to disk
    for filename, content in files.items():
        with open(f"generated/{filename}", 'w') as f:
            f.write(content)

See Also
--------

* :doc:`quickstart` - Getting started guide
* :doc:`components` - Component types and usage
* :doc:`examples` - More detailed examples
