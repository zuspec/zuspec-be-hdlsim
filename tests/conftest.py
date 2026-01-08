"""Pytest configuration for zuspec-be-hdlsim tests."""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_workspace():
    """Provide temporary workspace for tests."""
    tmpdir = tempfile.mkdtemp(prefix="hdlsim_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def simple_component():
    """Provide a simple test component class."""
    import zuspec.dataclasses as zdc
    
    @zdc.dataclass
    class SimpleComp(zdc.Component):
        """Simple test component."""
        pass
    
    return SimpleComp


@pytest.fixture
def xtor_component():
    """Provide a simple XtorComponent for testing."""
    import zuspec.dataclasses as zdc
    from typing import Protocol, Tuple
    
    class ISimpleXtor(Protocol):
        async def access(self, addr: zdc.u32) -> zdc.u32:
            ...
    
    @zdc.dataclass
    class SimpleXtor(zdc.XtorComponent[ISimpleXtor]):
        """Simple transactor for testing."""
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        
        def __bind__(self):
            return ((self.xtor_if.access, self.access),)
        
        async def access(self, addr: zdc.u32) -> zdc.u32:
            return addr + 1
    
    return SimpleXtor


@pytest.fixture
def extern_component():
    """Provide an Extern component for testing."""
    import zuspec.dataclasses as zdc
    
    class SimpleDut(zdc.Extern):
        """Simple DUT wrapper."""
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
    
    return SimpleDut
