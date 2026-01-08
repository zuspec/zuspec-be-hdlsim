"""Test JSON API generator."""
import pytest
import json
import zuspec.dataclasses as zdc
from typing import Protocol, Tuple


def test_json_api_generator_can_be_imported():
    """Verify generator can be imported."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    assert TransactorJsonApiGenerator is not None


def test_generator_extracts_xtor_interface(xtor_component):
    """Verify generator extracts xtor_if Protocol."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    assert gen.xtor_if is not None
    assert gen.xtor_name == "SimpleXtor"


def test_generator_produces_valid_json(xtor_component):
    """Verify generator produces valid JSON structure."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    api_def = gen.generate()
    
    # Should be a dict with required keys
    assert isinstance(api_def, dict)
    assert "fullname" in api_def
    assert "methods" in api_def
    assert isinstance(api_def["methods"], list)


def test_generator_maps_method_correctly(xtor_component):
    """Verify generator correctly maps xtor_if methods."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    api_def = gen.generate()
    
    # Should have the 'access' method
    methods = api_def["methods"]
    assert len(methods) > 0
    
    access_method = next((m for m in methods if m["name"] == "access"), None)
    assert access_method is not None
    assert access_method["kind"] == "imp_task"  # async → imp_task


def test_generator_maps_types_correctly(xtor_component):
    """Verify generator maps Zuspec types to JSON types."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    api_def = gen.generate()
    
    access_method = next((m for m in api_def["methods"] if m["name"] == "access"), None)
    assert access_method is not None
    
    # Check parameter type mapping (u32 → uint32)
    params = access_method["params"]
    assert len(params) == 1
    assert params[0]["name"] == "addr"
    assert params[0]["type"] == "uint32"


def test_generator_handles_return_types(xtor_component):
    """Verify generator handles return types."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    api_def = gen.generate()
    
    access_method = next((m for m in api_def["methods"] if m["name"] == "access"), None)
    assert "return_type" in access_method
    # u32 return → uint32
    assert access_method["return_type"] == "uint32"


def test_generator_produces_serializable_json(xtor_component):
    """Verify output can be serialized to JSON string."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(xtor_component)
    api_def = gen.generate()
    
    # Should be serializable
    json_str = json.dumps(api_def, indent=2)
    assert json_str is not None
    assert len(json_str) > 0
    
    # Should be deserializable
    parsed = json.loads(json_str)
    assert parsed == api_def


def test_generator_with_tuple_return_type():
    """Verify generator handles tuple return types as pyobject."""
    
    class IComplexXtor(Protocol):
        async def dual_return(self, addr: zdc.u32) -> Tuple[zdc.bit, zdc.u64]:
            ...
    
    @zdc.dataclass
    class ComplexXtor(zdc.XtorComponent[IComplexXtor]):
        clock: zdc.bit = zdc.input()
        
        async def dual_return(self, addr: zdc.u32) -> Tuple[zdc.bit, zdc.u64]:
            return (0, addr)
    
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    gen = TransactorJsonApiGenerator(ComplexXtor)
    api_def = gen.generate()
    
    method = next((m for m in api_def["methods"] if m["name"] == "dual_return"), None)
    assert method is not None
    # Tuple return should become pyobject
    assert method["return_type"] == "pyobject"


def test_generator_fullname_format():
    """Verify generator creates proper fullname."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    class ITestXtor(Protocol):
        async def test_method(self) -> None:
            ...
    
    @zdc.dataclass
    class TestXtor(zdc.XtorComponent[ITestXtor]):
        async def test_method(self) -> None:
            pass
    
    gen = TransactorJsonApiGenerator(TestXtor, module_name="my_module")
    api_def = gen.generate()
    
    assert api_def["fullname"] == "my_module.TestXtorApi"
