"""Integration tests combining multiple components."""
import pytest
import json
import zuspec.dataclasses as zdc
from typing import Protocol


def test_complete_generation_flow():
    """Test complete flow: Component → JSON API → SV modules."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
    
    # Define components
    class ISimpleXtor(Protocol):
        async def write(self, addr: zdc.u32, data: zdc.u64) -> None:
            ...
        
        async def read(self, addr: zdc.u32) -> zdc.u64:
            ...
    
    @zdc.dataclass
    class SimpleXtor(zdc.XtorComponent[ISimpleXtor]):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
        
        async def write(self, addr: zdc.u32, data: zdc.u64) -> None:
            pass
        
        async def read(self, addr: zdc.u32) -> zdc.u64:
            return 0
    
    class SimpleDut(zdc.Extern):
        clock: zdc.bit = zdc.input()
        reset: zdc.bit = zdc.input()
    
    @zdc.dataclass
    class SimpleTB(zdc.Component):
        dut: SimpleDut = zdc.inst()
        initiator: SimpleXtor = zdc.inst()
    
    # Generate JSON API
    api_gen = TransactorJsonApiGenerator(SimpleXtor, module_name="simple_tb")
    api_def = api_gen.generate()
    
    # Verify JSON API
    assert api_def["fullname"] == "simple_tb.SimpleXtorApi"
    assert len(api_def["methods"]) == 2
    
    method_names = [m["name"] for m in api_def["methods"]]
    assert "write" in method_names
    assert "read" in method_names
    
    # Generate SV modules
    sv_gen = SVTestbenchGenerator(SimpleTB)
    sv_files = sv_gen.generate()
    
    # Verify SV files and pytest file
    # be-sv may sanitize module names for test-defined classes
    assert "SimpleTB_tb.sv" in sv_files
    # Find SimpleTB module file (may have sanitized name)
    simpletb_file = [f for f in sv_files.keys() if 'SimpleTB.sv' in f and not f.endswith('_tb.sv')]
    assert len(simpletb_file) > 0, f"SimpleTB module not found in {list(sv_files.keys())}"
    simpletb_sv_name = simpletb_file[0]
    
    assert "test_simpletb.py" in sv_files
    
    hdl_content = sv_files[simpletb_sv_name]
    tb_content = sv_files["SimpleTB_tb.sv"]
    pytest_content = sv_files["test_simpletb.py"]
    
    # Verify HDL module exists and is valid SV (be-sv generated)
    # For test-defined classes with no bindings, the module may be minimal
    assert "module" in hdl_content
    assert "endmodule" in hdl_content
    
    # Verify testbench module has registration and ObjFactory config
    assert "pyhdl_if::pyhdl_if_registerObject" in tb_content
    assert "top.initiator" in tb_content
    assert "configure_objfactory" in tb_content
    
    # Verify pytest file structure
    assert "from zuspec.be.hdlsim import HDLSim" not in pytest_content
    assert "async def test_example" in pytest_content
    assert "tb = SimpleTB()" in pytest_content


def test_json_can_be_serialized_to_file(temp_workspace):
    """Test that generated JSON can be written to file."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    
    class IXtor(Protocol):
        async def test(self) -> None:
            ...
    
    @zdc.dataclass
    class TestXtor(zdc.XtorComponent[IXtor]):
        async def test(self) -> None:
            pass
    
    # Generate and write JSON
    api_gen = TransactorJsonApiGenerator(TestXtor)
    api_def = api_gen.generate()
    
    json_file = temp_workspace / "api_def.json"
    with open(json_file, 'w') as f:
        json.dump(api_def, f, indent=2)
    
    # Verify file exists and is valid
    assert json_file.exists()
    
    # Read back and validate
    with open(json_file, 'r') as f:
        loaded = json.load(f)
    
    assert loaded == api_def


def test_sv_can_be_written_to_files(temp_workspace):
    """Test that generated SV can be written to files."""
    from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
    
    @zdc.dataclass
    class SimpleTB(zdc.Component):
        pass
    
    gen = SVTestbenchGenerator(SimpleTB)
    files = gen.generate()
    
    # Write files
    for filename, content in files.items():
        filepath = temp_workspace / filename
        with open(filepath, 'w') as f:
            f.write(content)
        
        assert filepath.exists()
        
        # Verify content matches
        with open(filepath, 'r') as f:
            read_content = f.read()
        assert read_content == content


def test_multiple_transactors_generate_multiple_apis():
    """Test that multiple transactors each get their own API."""
    from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
    from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
    
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
    
    # Generate SV
    sv_gen = SVTestbenchGenerator(MultiTB)
    
    # Generate JSON for each transactor
    api_defs = []
    for name, xtor_cls in sv_gen._xtor_components.items():
        api_gen = TransactorJsonApiGenerator(xtor_cls)
        api_def = api_gen.generate()
        api_defs.append(api_def)
    
    # Should have 2 APIs
    assert len(api_defs) == 2
    
    fullnames = [api["fullname"] for api in api_defs]
    assert "generated_api.Xtor1Api" in fullnames
    assert "generated_api.Xtor2Api" in fullnames


def test_profile_checker_validates_before_generation():
    """Test that profile checker runs before generation."""
    from zuspec.be.hdlsim.profile import HDLTestbenchProfile
    from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
    
    @zdc.dataclass(profile=HDLTestbenchProfile)
    class ValidTB(zdc.Component):
        pass
    
    # Should be able to generate without errors
    checker = HDLTestbenchProfile.get_checker()
    checker.check_component(ValidTB)
    
    assert not checker.has_errors()
    
    # Generation should succeed
    gen = SVTestbenchGenerator(ValidTB)
    files = gen.generate()
    
    # Should generate 3 files: HDL module, TB module, and pytest file
    assert len(files) == 3
