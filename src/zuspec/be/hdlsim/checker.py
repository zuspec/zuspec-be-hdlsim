"""Checker implementation for HDLTestbench profile."""
from typing import Set, List
import zuspec.dataclasses as zdc


class HDLTestbenchChecker:
    """Validates HDLTestbench profile rules.
    
    Key rules:
    1. No signal-level connections between Python and SV domains
    2. Extern components must only use bundles/interfaces
    3. XtorComponents can only connect to signals in __bind__
    4. Python components use TLM-style connections only
    """
    
    def __init__(self):
        self._sv_components: Set[str] = set()
        self._py_components: Set[str] = set()
        self._errors: List[str] = []
    
    def check_component(self, comp) -> None:
        """Check a component definition.
        
        Args:
            comp: Component class to check
        """
        # Classify component by domain
        comp_name = comp.__name__ if hasattr(comp, '__name__') else str(comp)
        
        if self._is_extern(comp):
            self._sv_components.add(comp_name)
        elif self._is_xtor_component(comp):
            self._sv_components.add(comp_name)
        else:
            self._py_components.add(comp_name)
        
        # Check bindings if present
        if hasattr(comp, '__bind__'):
            self._check_bindings(comp)
    
    def _is_extern(self, comp) -> bool:
        """Check if component is Extern-derived."""
        # Extern is a Protocol, so check MRO for it
        try:
            if hasattr(comp, '__mro__'):
                return any(base.__name__ == 'Extern' for base in comp.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
    
    def _is_xtor_component(self, comp) -> bool:
        """Check if component is XtorComponent-derived."""
        # Check MRO for XtorComponent
        try:
            if hasattr(comp, '__mro__'):
                return any(base.__name__ == 'XtorComponent' for base in comp.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
    
    def _check_bindings(self, comp) -> None:
        """Verify bindings follow domain separation rules.
        
        Note: This is a placeholder for now. Full implementation
        will analyze binding tuples and verify domain separation.
        """
        # Get bindings
        try:
            bindings = comp.__bind__(None)  # Static call for class analysis
        except:
            # If __bind__ needs instance, we'll skip for now
            return
        
        # TODO: Implement full binding analysis
        # For now, just verify bindings is a tuple/list
        if bindings and not isinstance(bindings, (tuple, list)):
            self._errors.append(
                f"Component {comp.__name__}.__bind__ must return tuple or list"
            )
    
    def get_errors(self) -> List[str]:
        """Return list of validation errors."""
        return self._errors
    
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return len(self._errors) > 0
