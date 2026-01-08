"""End-to-end integration test with real Wishbone VIP."""
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def e2e_workspace():
    """Create workspace for end-to-end test."""
    tmpdir = tempfile.mkdtemp(prefix="e2e_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_e2e_wishbone_testbench_generation(e2e_workspace):
    """Complete end-to-end: Generate testbench from real Wishbone VIP."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    # Add src/vip to path so we can import the VIP
    vip_path = Path(__file__).parent.parent.parent.parent.parent / "src" / "vip"
    sys.path.insert(0, str(vip_path))
    
    # Create a simple testbench module
    tb_module = e2e_workspace / "wb_testbench.py"
    tb_module.write_text("""
import zuspec.dataclasses as zdc
from org.featherweight_vip.fwvip_wb.initiator import InitiatorXtor

# Simple DUT wrapper (Extern)
class SimpleDut(zdc.Extern):
    clock: zdc.bit = zdc.input()
    reset: zdc.bit = zdc.input()

@zdc.dataclass
class WishboneTB(zdc.Component):
    '''Simple Wishbone testbench with initiator.'''
    dut: SimpleDut = zdc.inst()
    initiator: InitiatorXtor = zdc.inst()
""")
    
    sys.path.insert(0, str(e2e_workspace))
    
    try:
        # Run GenTB task
        task = GenTB()
        
        from unittest.mock import Mock
        ctxt = Mock()
        ctxt.rundir = str(e2e_workspace / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'wb_testbench.WishboneTB'
        }
        ctxt.log = Mock()
        
        import asyncio
        result = asyncio.run(task.run(ctxt))
        
        # Should succeed
        assert result.status == 0, "GenTB task failed"
        
        # Check generated files
        gen_dir = Path(ctxt.rundir) / "generated"
        assert gen_dir.exists(), "Generated directory not created"
        
        # Should have SV modules and pytest file
        hdl_module = gen_dir / "WishboneTB.sv"
        top_module = gen_dir / "WishboneTB_tb.sv"
        pytest_file = gen_dir / "test_wishbonetb.py"
        
        assert hdl_module.exists(), "HDL module not generated"
        assert top_module.exists(), "Top module not generated"
        assert pytest_file.exists(), "Pytest file not generated"
        
        # Check HDL module content
        hdl_content = hdl_module.read_text()
        assert "module WishboneTB" in hdl_content
        assert "SimpleDut dut()" in hdl_content
        assert "InitiatorXtor initiator()" in hdl_content  # be-sv generates correct name
        
        # Check top module content
        top_content = top_module.read_text()
        assert "module WishboneTB_tb" in top_content
        assert "import pyhdl_if" in top_content
        assert "WishboneTB top()" in top_content
        assert "pyhdl_pytest" in top_content
        assert "pyhdl_if_registerObject" in top_content
        assert "top.initiator" in top_content
        assert "configure_objfactory" in top_content or "PyImport_ImportModule" in top_content  # New or old style
        
        # Check pytest file content
        pytest_content = pytest_file.read_text()
        assert "async def test_example" in pytest_content
        assert "tb = WishboneTB()" in pytest_content
        assert "import WishboneTB" in pytest_content
        
        # Should have JSON API
        json_file = gen_dir / "transactor_apis.json"
        assert json_file.exists(), "JSON API not generated"
        
        import json
        with open(json_file) as f:
            api_spec = json.load(f)
        
        assert "apis" in api_spec
        assert len(api_spec["apis"]) == 1  # One transactor
        
        api = api_spec["apis"][0]
        assert "InitiatorXtor" in api["fullname"]
        assert "methods" in api
        
        # Check that access method is defined
        methods = {m["name"]: m for m in api["methods"]}
        assert "access" in methods
        
        access_method = methods["access"]
        assert access_method["kind"] == "imp_task"  # async
        assert "params" in access_method
        assert len(access_method["params"]) == 4  # adr, dat_w, sel, we
        assert "return_type" in access_method
        
        # Return type is tuple, so should be pyobject
        assert access_method["return_type"] == "pyobject"
        
        # Log what was generated
        print("\n=== Generated Files ===")
        for f in gen_dir.iterdir():
            print(f"  {f.name} ({f.stat().st_size} bytes)")
        
        # Test complete
        
    finally:
        sys.path.remove(str(e2e_workspace))
        if str(vip_path) in sys.path:
            sys.path.remove(str(vip_path))


def test_e2e_python_runtime_factory(e2e_workspace):
    """Test Python runtime factory with real components."""
    from zuspec.be.hdlsim.py_runtime import PyTestbenchFactory
    
    vip_path = Path(__file__).parent.parent.parent.parent.parent / "src" / "vip"
    sys.path.insert(0, str(vip_path))
    
    tb_module = e2e_workspace / "wb_runtime_tb.py"
    tb_module.write_text("""
import zuspec.dataclasses as zdc
from org.featherweight_vip.fwvip_wb.initiator import InitiatorXtor

@zdc.dataclass
class RuntimeTB(zdc.Component):
    initiator: InitiatorXtor = zdc.inst()
""")
    
    sys.path.insert(0, str(e2e_workspace))
    
    try:
        # Import the testbench
        import wb_runtime_tb
        
        # Create runtime proxy
        factory = PyTestbenchFactory()
        tb = factory.create(wb_runtime_tb.RuntimeTB, inst_path="top")
        
        # Should have initiator attribute
        assert hasattr(tb, 'initiator')
        assert tb.initiator is not None
        
        # Should be a RuntimeWrapper
        assert hasattr(tb.initiator, 'xtor_if')
        assert hasattr(tb.initiator, '_inst_path')
        
        # Check path
        assert tb.initiator._inst_path == "top.initiator"
        
        # xtor_if should be a proxy
        assert hasattr(tb.initiator.xtor_if, '__getattr__')
        
        # Test complete
        
    finally:
        sys.path.remove(str(e2e_workspace))
        if str(vip_path) in sys.path:
            sys.path.remove(str(vip_path))
