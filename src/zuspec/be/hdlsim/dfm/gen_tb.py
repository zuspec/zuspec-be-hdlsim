"""GenTB task - Generate testbench from Zuspec component."""
import os
import json
import importlib
from typing import Any


class TaskDataResult:
    """Result from task execution."""
    def __init__(self, status: int, data: dict = None):
        self.status = status
        self.data = data or {}


class GenTB:
    """Generate HDL testbench SystemVerilog from Zuspec component.
    
    This task:
    1. Loads the specified Zuspec component class
    2. Runs profile checker
    3. Generates JSON API definitions for transactors
    4. Invokes PyHDL-IF APIGenSV to generate SV API wrappers
    5. Generates SystemVerilog testbench modules
    6. Outputs fileset for compilation
    """
    
    async def run(self, ctxt) -> TaskDataResult:
        """Execute the GenTB task.
        
        Args:
            ctxt: Task run context with:
                - rundir: Working directory
                - input.params: Dict with 'class_name'
                - log: Logger
                
        Returns:
            TaskDataResult with status and generated files
        """
        # Get parameters
        params = ctxt.input.params
        class_name = params.get('class_name')
        
        if not class_name:
            ctxt.log.error("Missing required parameter: class_name")
            return TaskDataResult(status=1)
        
        # Import the component class
        try:
            component_cls = self._load_class(class_name)
        except Exception as e:
            ctxt.log.error(f"Failed to load class {class_name}: {e}")
            return TaskDataResult(status=1)
        
        # Run checker
        from zuspec.be.hdlsim.profile import HDLTestbenchProfile
        checker = HDLTestbenchProfile.get_checker()
        checker.check_component(component_cls)
        
        errors = checker.get_errors()
        if errors:
            for error in errors:
                ctxt.log.error(error)
            return TaskDataResult(status=1)
        
        # Create output directory
        output_dir = os.path.join(ctxt.rundir, "generated")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate SystemVerilog testbench
        from zuspec.be.hdlsim.sv_generator import SVTestbenchGenerator
        sv_gen = SVTestbenchGenerator(component_cls)
        sv_files = sv_gen.generate()
        
        # Write SV files
        file_paths = []
        for filename, content in sv_files.items():
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            file_paths.append(filepath)
            ctxt.log.info(f"Generated SV: {filename}")
        
        # Generate JSON API definitions for transactors
        from zuspec.be.hdlsim.json_api_gen import TransactorJsonApiGenerator
        
        api_defs = []
        for name, xtor_cls in sv_gen._xtor_components.items():
            api_gen = TransactorJsonApiGenerator(
                xtor_cls,
                module_name="generated_api"
            )
            api_def = api_gen.generate()
            api_defs.append(api_def)
        
        if api_defs:
            # Create combined JSON spec
            json_api_spec = {
                "$schema": "https://raw.githubusercontent.com/fvutils/pyhdl-if-pytest/main/doc/pyhdl-if.schema.json",
                "apis": api_defs
            }
            
            # Write JSON file
            json_file = os.path.join(output_dir, "transactor_apis.json")
            with open(json_file, 'w') as f:
                json.dump(json_api_spec, f, indent=2)
            
            ctxt.log.info(f"Generated JSON API spec: transactor_apis.json")
            
            # Invoke PyHDL-IF APIGenSV
            try:
                from hdl_if.cmd.cmd_api_gen_sv import CmdApiGenSV
                import argparse
                
                api_gen_sv = CmdApiGenSV()
                sv_pkg_file = os.path.join(
                    output_dir,
                    f"{component_cls.__name__}_api_pkg.sv"
                )
                
                args = argparse.Namespace(
                    spec=json_file,
                    spec_fmt='json',
                    package=f"{component_cls.__name__.lower()}_api_pkg",
                    output=sv_pkg_file,
                    uvm=False,
                    deprecated=False
                )
                
                api_gen_sv(args)
                file_paths.append(sv_pkg_file)
                ctxt.log.info(f"Generated SV API package: {os.path.basename(sv_pkg_file)}")
                
            except ImportError as e:
                ctxt.log.warning(f"PyHDL-IF not available, skipping API generation: {e}")
            except Exception as e:
                ctxt.log.error(f"Failed to generate SV API: {e}")
                # Don't fail the task, just warn
        
        # Return result
        return TaskDataResult(
            status=0,
            data={
                'files': file_paths,
                'incdirs': [output_dir],
                'sv_files': file_paths
            }
        )
    
    def _load_class(self, class_name: str) -> Any:
        """Load a Python class by fully-qualified name.
        
        Args:
            class_name: e.g., "my.module.MyClass"
            
        Returns:
            The class object
            
        Raises:
            ValueError: If class name is not fully qualified
            ImportError: If module cannot be imported
            AttributeError: If class doesn't exist in module
        """
        parts = class_name.rsplit('.', 1)
        if len(parts) == 1:
            raise ValueError(f"Class name must be fully qualified: {class_name}")
        
        module_name, cls_name = parts
        module = importlib.import_module(module_name)
        return getattr(module, cls_name)
