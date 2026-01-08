"""Test Python runtime factory."""
import pytest
import zuspec.dataclasses as zdc
from typing import Protocol
from unittest.mock import Mock, MagicMock, patch


def test_factory_can_be_imported():
    """Verify runtime factory can be imported."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    assert PyTestbenchFactory is not None


def test_factory_creates_simple_component():
    """Verify factory can create a simple component."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    @zdc.dataclass
    class SimpleComp(zdc.Component):
        pass
    
    factory = PyTestbenchFactory()
    instance = factory.create(SimpleComp, inst_path="top")
    
    assert instance is not None
    # Factory creates a proxy object, not the actual Component class
    assert hasattr(instance, '__class__')


def test_factory_identifies_xtor_components():
    """Verify factory identifies XtorComponent instances."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor(Protocol):
        async def access(self) -> None:
            ...
    
    @zdc.dataclass
    class MyXtor(zdc.XtorComponent[IXtor]):
        clock: zdc.bit = zdc.input()
        
        async def access(self) -> None:
            pass
    
    @zdc.dataclass
    class MyTB(zdc.Component):
        xtor: MyXtor = zdc.inst()
    
    factory = PyTestbenchFactory()
    tb = factory.create(MyTB, inst_path="top")
    
    # Should have xtor attribute
    assert hasattr(tb, 'xtor')
    assert tb.xtor is not None


def test_factory_creates_xtor_wrapper():
    """Verify factory creates wrapper for XtorComponent."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor(Protocol):
        async def test_method(self) -> None:
            ...
    
    @zdc.dataclass
    class TestXtor(zdc.XtorComponent[IXtor]):
        clock: zdc.bit = zdc.input()
        
        async def test_method(self) -> None:
            pass
    
    @zdc.dataclass
    class TestTB(zdc.Component):
        xtor: TestXtor = zdc.inst()
    
    factory = PyTestbenchFactory()
    tb = factory.create(TestTB, inst_path="top")
    
    # Wrapper should have xtor_if attribute
    assert hasattr(tb.xtor, 'xtor_if')
    assert tb.xtor.xtor_if is not None


def test_xtor_wrapper_has_correct_path():
    """Verify xtor wrapper is created with correct hierarchical path."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor(Protocol):
        async def op(self) -> None:
            ...
    
    @zdc.dataclass
    class MyXtor(zdc.XtorComponent[IXtor]):
        async def op(self) -> None:
            pass
    
    @zdc.dataclass
    class MyTB(zdc.Component):
        xtor: MyXtor = zdc.inst()
    
    factory = PyTestbenchFactory()
    tb = factory.create(MyTB, inst_path="top")
    
    # Wrapper should have internal path set to "top.xtor"
    assert hasattr(tb.xtor, '_inst_path')
    assert tb.xtor._inst_path == "top.xtor"


def test_xtor_if_proxy_forwards_to_api_object():
    """Verify xtor_if proxy forwards method calls to registered API object."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor(Protocol):
        async def access(self, addr: zdc.u32) -> zdc.u32:
            ...
    
    @zdc.dataclass
    class TestXtor(zdc.XtorComponent[IXtor]):
        async def access(self, addr: zdc.u32) -> zdc.u32:
            return addr
    
    @zdc.dataclass
    class TestTB(zdc.Component):
        xtor: TestXtor = zdc.inst()
    
    # Mock the HdlObjRgy to return a mock API object
    mock_api_obj = Mock()
    mock_api_obj.access = Mock(return_value=42)
    
    factory = PyTestbenchFactory()
    
    # Mock the registry
    with patch('zuspec.be.hdlsim.py_runtime.HdlObjRgy') as mock_rgy_cls:
        mock_rgy = Mock()
        mock_rgy.findObj = Mock(return_value=mock_api_obj)
        mock_rgy_cls.inst = Mock(return_value=mock_rgy)
        
        tb = factory.create(TestTB, inst_path="top")
        
        # Access the xtor_if
        result = tb.xtor.xtor_if.access
        
        # Should have looked up "top.xtor" in registry
        mock_rgy.findObj.assert_called_once_with("top.xtor")


def test_factory_handles_multiple_xtors():
    """Verify factory handles testbench with multiple transactors."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor1(Protocol):
        async def op1(self) -> None:
            ...
    
    class IXtor2(Protocol):
        async def op2(self) -> None:
            ...
    
    @zdc.dataclass
    class Xtor1(zdc.XtorComponent[IXtor1]):
        async def op1(self) -> None:
            pass
    
    @zdc.dataclass
    class Xtor2(zdc.XtorComponent[IXtor2]):
        async def op2(self) -> None:
            pass
    
    @zdc.dataclass
    class MultiTB(zdc.Component):
        xtor1: Xtor1 = zdc.inst()
        xtor2: Xtor2 = zdc.inst()
    
    factory = PyTestbenchFactory()
    tb = factory.create(MultiTB, inst_path="top")
    
    # Both should be created
    assert hasattr(tb, 'xtor1')
    assert hasattr(tb, 'xtor2')
    
    # Both should have correct paths
    assert tb.xtor1._inst_path == "top.xtor1"
    assert tb.xtor2._inst_path == "top.xtor2"


def test_factory_skips_extern_components():
    """Verify factory doesn't create Python objects for Extern."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class MyDut(zdc.Extern):
        clock: zdc.bit = zdc.input()
    
    @zdc.dataclass
    class TestTB(zdc.Component):
        dut: MyDut = zdc.inst()
    
    factory = PyTestbenchFactory()
    tb = factory.create(TestTB, inst_path="top")
    
    # Extern components shouldn't have Python proxies
    # (they exist only in SV)
    # So tb.dut might be None or not present
    if hasattr(tb, 'dut'):
        assert tb.dut is None


def test_xtor_wrapper_error_when_not_registered():
    """Verify helpful error when transactor not found in registry."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    class IXtor(Protocol):
        async def op(self) -> None:
            ...
    
    @zdc.dataclass
    class TestXtor(zdc.XtorComponent[IXtor]):
        async def op(self) -> None:
            pass
    
    @zdc.dataclass
    class TestTB(zdc.Component):
        xtor: TestXtor = zdc.inst()
    
    factory = PyTestbenchFactory()
    
    # Mock registry to return None (not found)
    with patch('zuspec.be.hdlsim.py_runtime.HdlObjRgy') as mock_rgy_cls:
        mock_rgy = Mock()
        mock_rgy.findObj = Mock(return_value=None)
        mock_rgy.getInstNames = Mock(return_value=["other.path"])
        mock_rgy_cls.inst = Mock(return_value=mock_rgy)
        
        tb = factory.create(TestTB, inst_path="top")
        
        # Accessing xtor_if should trigger lookup and raise error
        with pytest.raises(RuntimeError) as exc_info:
            _ = tb.xtor.xtor_if.some_method
        
        # Error should mention the path and show available paths
        error_msg = str(exc_info.value)
        assert "top.xtor" in error_msg
        assert "not found" in error_msg.lower() or "available" in error_msg.lower()


def test_factory_builds_hierarchical_paths():
    """Verify factory builds correct hierarchical paths."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    factory = PyTestbenchFactory()
    
    # Test path building
    path1 = factory._build_inst_path("top", "xtor")
    assert path1 == "top.xtor"
    
    path2 = factory._build_inst_path("", "xtor")
    assert path2 == "xtor"
    
    path3 = factory._build_inst_path("top.sub", "xtor")
    assert path3 == "top.sub.xtor"
