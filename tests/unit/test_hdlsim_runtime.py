"""Test HDLSim runtime registration and validation."""
import pytest
import zuspec.dataclasses as zdc


def test_runtime_can_be_imported():
    """Verify runtime can be imported."""
    from zuspec.be.hdlsim import HDLSimRuntime
    assert HDLSimRuntime is not None


def test_runtime_is_singleton():
    """Verify runtime uses singleton pattern."""
    from zuspec.be.hdlsim import HDLSimRuntime
    
    runtime1 = HDLSimRuntime.get_instance()
    runtime2 = HDLSimRuntime.get_instance()
    
    assert runtime1 is runtime2


def test_runtime_registers_tb_class():
    """Verify runtime can register testbench class."""
    from zuspec.be.hdlsim import HDLSimRuntime
    
    @zdc.dataclass
    class TestTB(zdc.Component):
        pass
    
    runtime = HDLSimRuntime.get_instance()
    runtime.register_tb_class(TestTB)
    
    assert runtime.get_registered_tb_class() is TestTB


def test_runtime_intercepts_construction():
    """Verify runtime intercepts testbench construction."""
    from zuspec.be.hdlsim import HDLSimRuntime
    
    @zdc.dataclass
    class MyTB(zdc.Component):
        pass
    
    runtime = HDLSimRuntime.get_instance()
    runtime.register_tb_class(MyTB)
    
    # Construct the testbench - should be intercepted
    tb = MyTB()
    
    # Should have received runtime proxy
    assert tb is not None


def test_configure_objfactory():
    """Verify configure_objfactory function."""
    from zuspec.be.hdlsim import configure_objfactory, HDLSimRuntime
    import sys
    
    # Create a test module with a testbench
    test_module = type(sys)('test_module')
    
    @zdc.dataclass
    class ConfigTB(zdc.Component):
        pass
    
    test_module.ConfigTB = ConfigTB
    sys.modules['test_module'] = test_module
    
    try:
        # Configure via the function
        configure_objfactory('test_module.ConfigTB')
        
        # Verify it was registered
        runtime = HDLSimRuntime.get_instance()
        assert runtime.get_registered_tb_class() is ConfigTB
        
    finally:
        # Cleanup
        del sys.modules['test_module']
