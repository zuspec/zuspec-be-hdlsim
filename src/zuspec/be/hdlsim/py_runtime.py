"""Python runtime factory for HDL simulation."""
from typing import Any, Type, Dict


# Import HdlObjRgy from PyHDL-IF
try:
    from hdl_if.hdl_obj_rgy import HdlObjRgy
except ImportError:
    # Fallback for testing without pyhdl-if installed
    HdlObjRgy = None


class PyTestbenchFactory:
    """Factory for creating executable Python testbench objects.
    
    This factory is invoked at simulation runtime (from within pyhdl_pytest)
    to create Python objects that match the API of Zuspec component classes.
    
    Key insight: XtorComponents are accessed through their generated API classes
    which are already registered with PyHDL-IF by the SV side.
    """
    
    def __init__(self):
        self._obj_rgy = HdlObjRgy.inst() if HdlObjRgy else None
        self._component_cache: Dict[Type, Type] = {}
    
    def create(self, component_cls: Type, inst_path: str = "top") -> Any:
        """Create executable instance of component class.
        
        Args:
            component_cls: Zuspec component class
            inst_path: Hierarchical instance path (default: "top")
            
        Returns:
            Executable Python object with proxy to SV components
        """
        # Create a simple object to hold the component hierarchy
        class TestbenchProxy:
            """Proxy object that holds references to SV components."""
            pass
        
        instance = TestbenchProxy()
        
        # Wire up sub-components
        self._wire_subcomponents(instance, component_cls, inst_path)
        
        return instance
    
    def _get_runtime_class(self, component_cls: Type) -> Type:
        """Get or generate runtime class for component."""
        if component_cls in self._component_cache:
            return self._component_cache[component_cls]
        
        # Determine implementation strategy
        if self._is_xtor_component(component_cls):
            runtime_cls = None  # Will create wrapper in _wire_subcomponents
        elif self._is_extern(component_cls):
            # Extern components are in SV, no Python proxy needed
            runtime_cls = None
        else:
            # Regular Python component - use as-is
            runtime_cls = component_cls
        
        self._component_cache[component_cls] = runtime_cls
        return runtime_cls
    
    def _create_xtor_wrapper(self, xtor_cls: Type, inst_path: str):
        """Create wrapper instance for XtorComponent.
        
        The wrapper retrieves the SV-registered API object and exposes
        the xtor_if interface.
        """
        class_name = f"{xtor_cls.__name__}_RuntimeWrapper"
        
        class RuntimeWrapper:
            """Runtime wrapper that provides xtor_if access."""
            
            def __init__(self):
                self._inst_path = inst_path
                self._api_obj = None
                self.xtor_if = XtorIfProxy(self)
            
            def _get_api_obj(self):
                """Lazy lookup of the registered API object.
                
                The object must have been registered by SV side using:
                    pyhdl_if_registerObject(api_impl.m_obj, path, 0)
                """
                if self._api_obj is None:
                    if self._inst_path is None:
                        raise RuntimeError(
                            f"Instance path not set for {class_name}"
                        )
                    
                    if HdlObjRgy is None:
                        raise RuntimeError(
                            "HdlObjRgy not available. Is pyhdl-if installed?"
                        )
                    
                    obj_rgy = HdlObjRgy.inst()
                    self._api_obj = obj_rgy.findObj(self._inst_path)
                    
                    if self._api_obj is None:
                        # Provide helpful error message
                        available = obj_rgy.getInstNames()
                        raise RuntimeError(
                            f"Transactor not found in registry: {self._inst_path}\n"
                            f"Available paths:\n" +
                            "\n".join(f"  - {p}" for p in available)
                        )
                return self._api_obj
        
        class XtorIfProxy:
            """Proxy that exposes xtor_if methods."""
            
            def __init__(self, wrapper):
                self._wrapper = wrapper
            
            def __getattr__(self, name):
                """Forward attribute access to the API object."""
                api_obj = self._wrapper._get_api_obj()
                return getattr(api_obj, name)
        
        RuntimeWrapper.__name__ = class_name
        RuntimeWrapper.__qualname__ = class_name
        
        return RuntimeWrapper()
    
    def _build_inst_path(self, parent_path: str, field_name: str) -> str:
        """Build hierarchical instance path.
        
        Args:
            parent_path: Path to parent component (e.g., "top")
            field_name: Name of the field (e.g., "initiator")
            
        Returns:
            Full path (e.g., "top.initiator")
        """
        if parent_path:
            return f"{parent_path}.{field_name}"
        else:
            return field_name
    
    def _wire_subcomponents(self, instance: Any, component_cls: Type, parent_path: str):
        """Set up sub-component instances with proper hierarchical paths."""
        # Check for dataclass fields
        if not hasattr(component_cls, '__dataclass_fields__'):
            return
        
        fields = component_cls.__dataclass_fields__
        
        for field_name, field in fields.items():
            if field_name.startswith('_'):
                continue
            
            # Check metadata for 'kind'
            metadata = field.metadata
            if metadata.get('kind') != 'instance':
                continue
            
            field_type = field.type
            if field_type is None:
                continue
            
            # Build hierarchical path for this sub-component
            sub_path = self._build_inst_path(parent_path, field_name)
            
            # Create sub-component based on type
            if self._is_xtor_component(field_type):
                # XtorComponent: create wrapper that looks up in registry
                sub_instance = self._create_xtor_wrapper(field_type, sub_path)
            elif self._is_extern(field_type):
                # Extern: no Python representation (exists only in SV)
                sub_instance = None
            else:
                # Regular component: recurse
                sub_instance = self.create(field_type, sub_path)
            
            # Set the attribute on the instance
            setattr(instance, field_name, sub_instance)
    
    def _is_extern(self, cls) -> bool:
        """Check if class is Extern-derived."""
        try:
            if hasattr(cls, '__mro__'):
                return any(base.__name__ == 'Extern' for base in cls.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
    
    def _is_xtor_component(self, cls) -> bool:
        """Check if class is XtorComponent-derived."""
        try:
            if hasattr(cls, '__mro__'):
                return any(base.__name__ == 'XtorComponent' for base in cls.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
