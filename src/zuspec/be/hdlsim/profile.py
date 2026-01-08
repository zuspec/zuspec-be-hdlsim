"""HDLTestbench profile for zuspec-be-hdlsim backend."""


class _HDLTestbenchProfile:
    """Profile for HDL testbench components.
    
    This profile enforces rules for HDL/Python domain separation:
    - Extern-derived classes are implemented in SystemVerilog
    - XtorComponent-derived classes generate SV and are implemented in SV
    - Python components cannot connect at signal level to SV components
    """
    
    def get_checker(self):
        """Return the checker for this profile."""
        from .checker import HDLTestbenchChecker
        return HDLTestbenchChecker()


# Singleton instance
HDLTestbenchProfile = _HDLTestbenchProfile()
