"""Zuspec HDLSim backend - Python runtime support."""
from typing import Type, Any, Optional

from .py_runtime import PyTestbenchFactory


class HDLSimRuntime:
    """HDL simulation runtime - manages ObjFactory and testbench registration.
    
    This singleton is configured by SystemVerilog before pytest runs.
    It intercepts testbench class construction to provide runtime proxies.
    """
    
    _instance = None
    
    def __init__(self):
        self._factory = PyTestbenchFactory()
        self._registered_tb_class: Optional[Type] = None
        self._original_init = {}
    
    @classmethod
    def get_instance(cls) -> 'HDLSimRuntime':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_tb_class(self, tb_class: Type) -> None:
        """Register testbench class from SystemVerilog.
        
        This configures the ObjFactory and patches the class __init__
        to intercept construction.
        
        Args:
            tb_class: Top-level testbench component class
        """
        self._registered_tb_class = tb_class
        
        # Save original __init__ if not already saved
        if tb_class not in self._original_init:
            self._original_init[tb_class] = tb_class.__init__
        
        # Patch __init__ to intercept construction
        # Capture runtime in closure for dynamic check
        runtime = self
        
        def patched_init(inst):
            # Dynamically check against currently registered class
            actual_class = type(inst)
            current_registered = runtime._registered_tb_class
            
            if actual_class is not current_registered:
                raise RuntimeError(
                    f"Cannot instantiate {actual_class.__name__}: "
                    f"Only {current_registered.__name__} is registered for this simulation. "
                    f"The testbench class must match the one specified in the "
                    f"SystemVerilog testbench module."
                )
            
            # Create runtime proxy using the factory
            proxy = runtime._factory.create(actual_class, inst_path="top")
            
            # Copy proxy attributes to the instance
            for attr_name in dir(proxy):
                if not attr_name.startswith('_'):
                    setattr(inst, attr_name, getattr(proxy, attr_name))
        
        tb_class.__init__ = patched_init
    
    def get_registered_tb_class(self) -> Optional[Type]:
        """Get the currently registered testbench class."""
        return self._registered_tb_class


def configure_objfactory(tb_class_path: str) -> None:
    """Configure ObjFactory from SystemVerilog.
    
    This function is called by the generated SV testbench module
    before launching pyhdl_pytest. It:
    1. Imports the testbench class
    2. Registers it with the runtime
    3. Patches the class to intercept construction
    
    Args:
        tb_class_path: Fully qualified class path (e.g., "mymodule.MyTB")
    """
    # Import the testbench class
    module_path, class_name = tb_class_path.rsplit('.', 1)
    
    import importlib
    module = importlib.import_module(module_path)
    tb_class = getattr(module, class_name)
    
    # Register with runtime
    runtime = HDLSimRuntime.get_instance()
    runtime.register_tb_class(tb_class)


__all__ = ['HDLSimRuntime', 'configure_objfactory']

