"""Generate PyHDL-IF JSON API definitions from Zuspec XtorComponents."""
import json
import inspect
from typing import Dict, List, Any, get_origin, get_args


class TransactorJsonApiGenerator:
    """Generate JSON API definition for PyHDL-IF from XtorComponent.
    
    Produces JSON conforming to pyhdl-if.schema.json
    """
    
    def __init__(self, xtor_cls, module_name: str = "generated_api"):
        self.xtor_cls = xtor_cls
        self.xtor_name = xtor_cls.__name__
        self.module_name = module_name
        self.xtor_if = self._get_xtor_interface()
    
    def _get_xtor_interface(self):
        """Extract the xtor_if Protocol type from XtorComponent[Protocol]."""
        if hasattr(self.xtor_cls, '__orig_bases__'):
            for base in self.xtor_cls.__orig_bases__:
                # Check if this is XtorComponent[...]
                if hasattr(base, '__origin__') and hasattr(base, '__args__'):
                    if len(base.__args__) > 0:
                        return base.__args__[0]
        return None
    
    def generate(self) -> Dict[str, Any]:
        """Generate JSON API definition.
        
        Returns:
            Dictionary that can be serialized to JSON
        """
        methods = []
        
        if self.xtor_if:
            # Extract methods from the Protocol
            for method_name in dir(self.xtor_if):
                if method_name.startswith('_'):
                    continue
                
                method = getattr(self.xtor_if, method_name, None)
                if not callable(method):
                    continue
                
                method_def = self._generate_method_def(method_name, method)
                if method_def:
                    methods.append(method_def)
        
        return {
            "fullname": f"{self.module_name}.{self.xtor_name}Api",
            "methods": methods
        }
    
    def _generate_method_def(self, method_name: str, method) -> Dict[str, Any]:
        """Generate method definition for JSON."""
        try:
            sig = inspect.signature(method)
        except (ValueError, TypeError):
            # Can't get signature, skip this method
            return None
        
        # Determine kind (imp_task for async, imp_func for sync)
        is_async = inspect.iscoroutinefunction(method)
        kind = "imp_task" if is_async else "imp_func"
        
        # Extract parameters
        params = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = self._map_type_to_json(param.annotation)
            params.append({
                "name": param_name,
                "type": param_type
            })
        
        method_def = {
            "name": method_name,
            "kind": kind,
            "params": params
        }
        
        # Add return type if present and not None/void
        if sig.return_annotation != inspect.Signature.empty:
            if sig.return_annotation is not type(None):
                ret_type = self._map_return_type(sig.return_annotation)
                if ret_type and ret_type not in ('void', 'None'):
                    method_def["return_type"] = ret_type
        
        return method_def
    
    def _map_type_to_json(self, zuspec_type) -> str:
        """Map Zuspec type to JSON type string."""
        # Handle Annotated types (e.g., Annotated[int, U(width=32)])
        origin = get_origin(zuspec_type)
        if origin is not None:
            # This is a generic type like Annotated[int, ...]
            args = get_args(zuspec_type)
            if args:
                # For Annotated, first arg is the actual type
                # Check the metadata for width information
                if len(args) > 1:
                    metadata = args[1:]
                    for meta in metadata:
                        # Check if it's a U (unsigned) or I (signed) width spec
                        if hasattr(meta, 'width'):
                            width = meta.width
                            signed = getattr(meta, 'signed', False)
                            
                            # Map based on width and signedness
                            if signed:
                                if width <= 8:
                                    return 'int8'
                                elif width <= 16:
                                    return 'int16'
                                elif width <= 32:
                                    return 'int32'
                                elif width <= 64:
                                    return 'int64'
                            else:
                                if width == 1:
                                    return 'bool'
                                elif width <= 8:
                                    return 'uint8'
                                elif width <= 16:
                                    return 'uint16'
                                elif width <= 32:
                                    return 'uint32'
                                elif width <= 64:
                                    return 'uint64'
        
        # Handle basic types by name
        if hasattr(zuspec_type, '__name__'):
            type_name = zuspec_type.__name__
            
            type_map = {
                'u8': 'uint8',
                'u16': 'uint16',
                'u32': 'uint32',
                'u64': 'uint64',
                'i8': 'int8',
                'i16': 'int16',
                'i32': 'int32',
                'i64': 'int64',
                'bit': 'bool',
                'bool': 'bool',
                'str': 'string',
            }
            
            if type_name in type_map:
                return type_map[type_name]
        
        # Default to pyobject for complex types
        return 'pyobject'
    
    def _map_return_type(self, ret_annotation) -> str:
        """Map return type annotation to JSON type string.
        
        Handles tuples (returns pyobject) and primitives.
        """
        # Check for Tuple type
        origin = get_origin(ret_annotation)
        if origin is tuple:
            # Multiple return values - use pyobject
            return 'pyobject'
        
        # Single return type
        return self._map_type_to_json(ret_annotation)
    
    def to_json_string(self, indent: int = 2) -> str:
        """Generate formatted JSON string."""
        api_def = self.generate()
        return json.dumps(api_def, indent=indent)
