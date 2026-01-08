"""Test DFM GenTB task."""
import pytest
import os
import tempfile
import shutil
import zuspec.dataclasses as zdc
from typing import Protocol
from pathlib import Path


@pytest.fixture
def task_rundir():
    """Provide temporary rundir for task execution."""
    tmpdir = tempfile.mkdtemp(prefix="gentb_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_gentb_can_be_imported():
    """Verify GenTB task can be imported."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    assert GenTB is not None


def test_gentb_has_required_methods():
    """Verify GenTB has run method."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    task = GenTB()
    assert hasattr(task, 'run')
    assert callable(task.run)


def test_gentb_loads_component_class(task_rundir):
    """Verify GenTB can load a component class by name."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    task = GenTB()
    
    # Should be able to load built-in classes
    cls = task._load_class('zuspec.dataclasses.Component')
    assert cls is zdc.Component


def test_gentb_generates_sv_files(task_rundir):
    """Verify GenTB generates SystemVerilog files."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    # Create a simple testbench module in temp location
    test_module = task_rundir / "test_tb.py"
    test_module.write_text("""
import zuspec.dataclasses as zdc

@zdc.dataclass
class SimpleTB(zdc.Component):
    pass
""")
    
    # Add to sys.path
    import sys
    sys.path.insert(0, str(task_rundir))
    
    try:
        task = GenTB()
        
        # Create mock context
        from unittest.mock import Mock
        ctxt = Mock()
        ctxt.rundir = str(task_rundir / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'test_tb.SimpleTB'
        }
        ctxt.log = Mock()
        
        # Run task
        import asyncio
        result = asyncio.run(task.run(ctxt))
        
        # Should succeed
        assert result.status == 0
        
        # Should have generated files
        gen_dir = Path(ctxt.rundir) / "generated"
        assert gen_dir.exists()
        
        assert (gen_dir / "SimpleTB_tb.sv").exists()
        assert (gen_dir / "SimpleTB.sv").exists()
        
    finally:
        sys.path.remove(str(task_rundir))


def test_gentb_generates_json_api(task_rundir):
    """Verify GenTB generates JSON API definitions."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    from typing import Protocol
    
    # Create testbench with transactor (use unique module name)
    test_module = task_rundir / "test_tb_json.py"
    test_module.write_text("""
import zuspec.dataclasses as zdc
from typing import Protocol

class IXtor(Protocol):
    async def access(self, addr: zdc.u32) -> zdc.u32:
        ...

@zdc.dataclass
class MyXtor(zdc.XtorComponent[IXtor]):
    clock: zdc.bit = zdc.input()
    
    async def access(self, addr: zdc.u32) -> zdc.u32:
        return addr

@zdc.dataclass
class TestTB(zdc.Component):
    xtor: MyXtor = zdc.inst()
""")
    
    import sys
    sys.path.insert(0, str(task_rundir))
    
    try:
        task = GenTB()
        
        from unittest.mock import Mock
        ctxt = Mock()
        ctxt.rundir = str(task_rundir / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'test_tb_json.TestTB'
        }
        ctxt.log = Mock()
        
        import asyncio
        result = asyncio.run(task.run(ctxt))
        
        assert result.status == 0
        
        # Should have JSON API file
        gen_dir = Path(ctxt.rundir) / "generated"
        json_file = gen_dir / "transactor_apis.json"
        assert json_file.exists()
        
        # Verify JSON content
        import json
        with open(json_file) as f:
            api_spec = json.load(f)
        
        assert "apis" in api_spec
        assert len(api_spec["apis"]) > 0
        
    finally:
        sys.path.remove(str(task_rundir))


def test_gentb_invokes_api_gen_sv(task_rundir):
    """Verify GenTB invokes PyHDL-IF APIGenSV."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    # Create testbench with transactor (use unique module name)
    test_module = task_rundir / "test_tb_apigen.py"
    test_module.write_text("""
import zuspec.dataclasses as zdc
from typing import Protocol

class IXtor(Protocol):
    async def test(self) -> None:
        ...

@zdc.dataclass
class TestXtor(zdc.XtorComponent[IXtor]):
    async def test(self) -> None:
        pass

@zdc.dataclass
class TestTB(zdc.Component):
    xtor: TestXtor = zdc.inst()
""")
    
    import sys
    sys.path.insert(0, str(task_rundir))
    
    try:
        task = GenTB()
        
        from unittest.mock import Mock, patch
        ctxt = Mock()
        ctxt.rundir = str(task_rundir / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'test_tb_apigen.TestTB'
        }
        ctxt.log = Mock()
        
        # Mock APIGenSV at the import location
        with patch('hdl_if.cmd.cmd_api_gen_sv.CmdApiGenSV') as mock_gen_sv:
            mock_instance = Mock()
            mock_gen_sv.return_value = mock_instance
            
            import asyncio
            result = asyncio.run(task.run(ctxt))
            
            assert result.status == 0
            
            # Should have called APIGenSV (if pyhdl-if is available)
            # We're mocking it so it should have been called
            mock_gen_sv.assert_called_once()
            mock_instance.assert_called_once()
        
    finally:
        sys.path.remove(str(task_rundir))


def test_gentb_returns_file_list(task_rundir):
    """Verify GenTB returns list of generated files."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    test_module = task_rundir / "test_tb.py"
    test_module.write_text("""
import zuspec.dataclasses as zdc

@zdc.dataclass
class SimpleTB(zdc.Component):
    pass
""")
    
    import sys
    sys.path.insert(0, str(task_rundir))
    
    try:
        task = GenTB()
        
        from unittest.mock import Mock
        ctxt = Mock()
        ctxt.rundir = str(task_rundir / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'test_tb.SimpleTB'
        }
        ctxt.log = Mock()
        
        import asyncio
        result = asyncio.run(task.run(ctxt))
        
        assert result.status == 0
        assert hasattr(result, 'data')
        assert 'files' in result.data
        
        files = result.data['files']
        assert len(files) > 0
        
        # All files should exist
        for filepath in files:
            assert os.path.exists(filepath)
        
    finally:
        sys.path.remove(str(task_rundir))


def test_gentb_reports_checker_errors(task_rundir):
    """Verify GenTB reports profile checker errors."""
    from zuspec.be.hdlsim.dfm.gen_tb import GenTB
    
    # Create a testbench that might have issues
    test_module = task_rundir / "test_tb.py"
    test_module.write_text("""
import zuspec.dataclasses as zdc

@zdc.dataclass
class SimpleTB(zdc.Component):
    pass
""")
    
    import sys
    sys.path.insert(0, str(task_rundir))
    
    try:
        task = GenTB()
        
        from unittest.mock import Mock, patch
        ctxt = Mock()
        ctxt.rundir = str(task_rundir / "rundir")
        ctxt.input = Mock()
        ctxt.input.params = {
            'class_name': 'test_tb.SimpleTB'
        }
        ctxt.log = Mock()
        
        # Mock checker to return errors - patch at the source module
        with patch('zuspec.be.hdlsim.profile.HDLTestbenchProfile.get_checker') as mock_get_checker:
            mock_checker = Mock()
            mock_checker.check_component = Mock()
            mock_checker.get_errors = Mock(return_value=["Test error"])
            mock_get_checker.return_value = mock_checker
            
            import asyncio
            result = asyncio.run(task.run(ctxt))
            
            # Should fail due to checker errors
            assert result.status == 1
            
            # Should have logged error
            ctxt.log.error.assert_called()
        
    finally:
        sys.path.remove(str(task_rundir))
