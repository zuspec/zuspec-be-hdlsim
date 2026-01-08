"""SystemVerilog testbench generator."""
from typing import Dict, Set, Any, List, Tuple, Optional
from io import StringIO
import inspect
import ast
import tempfile
from pathlib import Path


class SVTestbenchGenerator:
    """Generates SystemVerilog testbench from Zuspec component."""
    
    def __init__(self, top_component_cls):
        self.top_cls = top_component_cls
        self.top_name = top_component_cls.__name__
        self._extern_components: Dict[str, Any] = {}
        self._xtor_components: Dict[str, Any] = {}
        self._imports: Set[str] = {'pyhdl_if'}
        self._source_filesets: List[Any] = []
        self._fields: Dict[str, Any] = {}
        self._processes: List[Tuple[str, Any]] = []
        self._sync_blocks: List[Tuple[str, Any]] = []
        self._xtor_sv_files: Dict[str, str] = {}  # Store generated transactor SV
        
        # Analyze component tree
        self._analyze_component(self.top_cls)
    
    def generate(self) -> Dict[str, str]:
        """Generate all SV files.
        
        Returns:
            Dict mapping filename to SV content
        """
        files = {}
        
        # Use be-sv to generate ALL HDL modules (testbench + transactors)
        self._generate_hdl_modules_with_besv()
        files.update(self._xtor_sv_files)
        
        # Generate testbench wrapper module (top level that instances HDL + Python integration)
        files[f"{self.top_name}_tb.sv"] = self._generate_testbench_module()
        
        # Generate pytest file
        files[f"test_{self.top_name.lower()}.py"] = self._generate_pytest_file()
        
        return files
    
    def get_source_filesets(self) -> List[Any]:
        """Get all source filesets from extern components.
        
        Returns:
            List of AnnotationFileSet objects from all extern components
        """
        return self._source_filesets
    
    def _generate_hdl_modules_with_besv(self):
        """Generate ALL HDL modules (testbench + components) using zuspec-be-sv.
        
        This leverages be-sv's comprehensive module generation including:
        - Component modules with ports
        - Component instances
        - Signal bindings
        - Transactor modules
        """
        try:
            # Import be-sv generator
            from zuspec.be.sv import SVGenerator
            import zuspec.dataclasses as zdc
            
            # Create IR context for the entire testbench
            factory = zdc.DataModelFactory()
            ctxt = factory.build(self.top_cls)
            
            # Create temporary directory for be-sv output
            with tempfile.TemporaryDirectory() as tmpdir:
                # Generate SV using be-sv
                gen = SVGenerator(output_dir=tmpdir, debug_annotations=False)
                sv_files = gen.generate(ctxt)
                
                # Read all generated files and add to our output
                for sv_file in sv_files:
                    if sv_file.exists():
                        content = sv_file.read_text()
                        # Store with the original filename
                        self._xtor_sv_files[sv_file.name] = content
                        print(f"be-sv generated: {sv_file.name} ({len(content)} bytes)")
            
        except ImportError as e:
            # be-sv not available - fall back to manual generation
            print(f"Warning: zuspec-be-sv not available, using manual generation: {e}")
            self._xtor_sv_files[f"{self.top_name}.sv"] = self._generate_hdl_module()
            
        except Exception as e:
            # If be-sv generation fails, fall back to manual generation
            print(f"Warning: be-sv generation failed, using manual generation: {e}")
            import traceback
            traceback.print_exc()
            self._xtor_sv_files[f"{self.top_name}.sv"] = self._generate_hdl_module()
    
    def _generate_transactor_modules(self):
        """Generate transactor SV modules using zuspec-be-sv."""
        try:
            # Import be-sv generator
            from zuspec.be.sv import SVGenerator
            import zuspec.dataclasses as zdc
            
            # Generate IR for each transactor component
            for xtor_name, xtor_cls in self._xtor_components.items():
                try:
                    # Create IR context for this transactor using DataModelFactory
                    factory = zdc.DataModelFactory()
                    ctxt = factory.build(xtor_cls)
                    
                    # Create temporary directory for be-sv output
                    with tempfile.TemporaryDirectory() as tmpdir:
                        # Generate SV using be-sv
                        gen = SVGenerator(output_dir=tmpdir, debug_annotations=False)
                        sv_files = gen.generate(ctxt)
                        
                        # Read generated files and add to our output
                        for sv_file in sv_files:
                            if sv_file.exists():
                                content = sv_file.read_text()
                                # Store with the original filename
                                self._xtor_sv_files[sv_file.name] = content
                
                except Exception as e:
                    # If be-sv generation fails, log warning but continue
                    # This allows the testbench to still be generated
                    print(f"Warning: Could not generate transactor SV for {xtor_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    
        except ImportError as e:
            # be-sv not available - skip transactor generation
            print(f"Warning: zuspec-be-sv not available, transactor SV not generated: {e}")
    
    def _analyze_component(self, cls):
        """Analyze component to categorize instances."""
        # Check for dataclass fields
        if not hasattr(cls, '__dataclass_fields__'):
            return
        
        fields = cls.__dataclass_fields__
        
        for field_name, field in fields.items():
            if field_name.startswith('_'):
                continue
            
            # Check metadata for 'kind'
            metadata = field.metadata
            kind = metadata.get('kind')
            
            if kind == 'instance':
                field_type = field.type
                if field_type is None:
                    continue
                
                # Categorize by type
                if self._is_extern(field_type):
                    self._extern_components[field_name] = field_type
                    # Collect source filesets from extern component
                    self._collect_extern_sources(field_type)
                elif self._is_xtor_component(field_type):
                    self._xtor_components[field_name] = field_type
            else:
                # Regular field
                self._fields[field_name] = field
        
        # Analyze methods for processes and sync blocks
        for name in dir(cls):
            if name.startswith('_'):
                attr = getattr(cls, name)
                if self._is_process(attr):
                    self._processes.append((name, attr))
                elif self._is_sync(attr):
                    self._sync_blocks.append((name, attr))
    
    def _is_extern(self, cls) -> bool:
        """Check if class is Extern-derived."""
        try:
            if hasattr(cls, '__mro__'):
                return any(base.__name__ == 'Extern' for base in cls.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
    
    def _collect_extern_sources(self, comp):
        """Collect source filesets from an extern component."""
        try:
            instance = comp()
            impl_info = instance.__implementation__()
            if "sources" in impl_info:
                self._source_filesets.extend(impl_info["sources"])
        except Exception:
            # Silently ignore if __implementation__ fails
            pass
    
    def _is_xtor_component(self, cls) -> bool:
        """Check if class is XtorComponent-derived."""
        try:
            if hasattr(cls, '__mro__'):
                return any(base.__name__ == 'XtorComponent' for base in cls.__mro__)
            return False
        except (AttributeError, TypeError):
            return False
    
    def _is_process(self, attr) -> bool:
        """Check if attribute is a process (ExecProc)."""
        return hasattr(attr, '__class__') and attr.__class__.__name__ == 'ExecProc'
    
    def _is_sync(self, attr) -> bool:
        """Check if attribute is a sync block (ExecSync)."""
        return hasattr(attr, '__class__') and attr.__class__.__name__ == 'ExecSync'
    
    def _get_sv_type(self, field) -> str:
        """Get SystemVerilog type for a field."""
        field_type = field.type
        
        # Extract from typing.Annotated if present
        if hasattr(field_type, '__metadata__'):
            # Annotated type like Annotated[int, U(width=32)]
            metadata = field_type.__metadata__
            if metadata and hasattr(metadata[0], 'width'):
                width = metadata[0].width
                if width == 1:
                    return "logic"
                else:
                    return f"logic[{width-1}:0]"
        
        # Default types
        type_name = getattr(field_type, '__name__', str(field_type))
        if 'bit' in type_name.lower():
            return "logic"
        elif 'u32' in type_name.lower() or 'uint32' in type_name.lower():
            return "logic[31:0]"
        elif 'u8' in type_name.lower() or 'uint8' in type_name.lower():
            return "logic[7:0]"
        
        return "logic[31:0]"  # Default
    
    def _generate_hdl_module(self) -> str:
        """Generate <Top> HDL module with design components."""
        out = StringIO()
        
        out.write(f"// Auto-generated HDL module for {self.top_name}\n")
        out.write(f"module {self.top_name};\n\n")
        
        # Generate variable declarations for top-level fields
        if self._fields:
            out.write("    // Top-level signals\n")
            for name, field in self._fields.items():
                sv_type = self._get_sv_type(field)
                out.write(f"    {sv_type} {name};\n")
            out.write("\n")
        
        # Generate extern instances with connections
        for name, comp in self._extern_components.items():
            out.write(self._generate_extern_instance(name, comp))
        
        # Generate transactor instances
        for name, comp in self._xtor_components.items():
            out.write(self._generate_xtor_instance(name, comp))
        
        # Generate initial blocks for processes
        for proc_name, proc in self._processes:
            out.write(self._generate_process_block(proc_name, proc))
        
        # Generate always blocks for sync blocks
        for sync_name, sync in self._sync_blocks:
            out.write(self._generate_sync_block(sync_name, sync))
        
        out.write("\nendmodule\n")
        
        return out.getvalue()
    
    def _generate_testbench_module(self) -> str:
        """Generate <Top>_tb testbench module with Python integration."""
        out = StringIO()
        
        out.write(f"// Auto-generated testbench module for {self.top_name}\n")
        out.write(f"module {self.top_name}_tb;\n")
        
        # Import packages only if there are transactors
        if self._xtor_components:
            for imp in sorted(self._imports):
                out.write(f"    import {imp}::*;\n")
            out.write("\n")
        
        # Instance the HDL module
        out.write(f"    {self.top_name} top();\n\n")
        
        # Initial block for registration and pytest launch (only if transactors exist)
        if self._xtor_components:
            out.write("    initial begin\n")
            
            # Start pyhdl-if
            out.write("        // Initialize pyhdl-if\n")
            out.write("        pyhdl_if_start();\n")
            out.write("\n")
            
            # Register transactors
            for name, comp in self._xtor_components.items():
                out.write(self._generate_xtor_registration(name, comp))
            
            # Configure ObjFactory by calling Python function
            out.write("\n        // Configure be-hdlsim ObjFactory\n")
            out.write("        begin\n")
            out.write("            PyObject config_mod, config_func, args, result;\n")
            out.write("            PyGILState_STATE state;\n")
            out.write("\n")
            out.write("            state = PyGILState_Ensure();\n")
            out.write("\n")
            out.write("            // Import zuspec.be.hdlsim module\n")
            out.write("            config_mod = pyhdl_pi_if_HandleErr(\n")
            out.write("                PyImport_ImportModule(\"zuspec.be.hdlsim\")\n")
            out.write("            );\n")
            out.write("\n")
            out.write("            if (config_mod != null) begin\n")
            out.write("                // Get configure_objfactory function\n")
            out.write("                config_func = PyObject_GetAttrString(\n")
            out.write("                    config_mod, \"configure_objfactory\"\n")
            out.write("                );\n")
            out.write("\n")
            out.write("                if (config_func != null) begin\n")
            out.write("                    // Call with testbench class path\n")
            out.write("                    args = PyTuple_New(1);\n")
            out.write(f"                    void'(PyTuple_SetItem(args, 0,\n")
            out.write(f"                        PyUnicode_FromString(\n")
            out.write(f"                            \"{self.top_cls.__module__}.{self.top_name}\"\n")
            out.write(f"                        )\n")
            out.write(f"                    ));\n")
            out.write("\n")
            out.write("                    result = pyhdl_pi_if_HandleErr(\n")
            out.write("                        PyObject_Call(config_func, args, null)\n")
            out.write("                    );\n")
            out.write("\n")
            out.write("                    Py_DecRef(args);\n")
            out.write("                    if (result != null) Py_DecRef(result);\n")
            out.write("                    Py_DecRef(config_func);\n")
            out.write("                end\n")
            out.write("                Py_DecRef(config_mod);\n")
            out.write("            end\n")
            out.write("\n")
            out.write("            PyGILState_Release(state);\n")
            out.write("        end\n")
            
            # Launch pytest
            out.write("\n        // Launch pytest\n")
            out.write("        pyhdl_pytest(\".\");  // Run tests in current directory\n")
            out.write("        $finish;\n")
            out.write("    end\n")
        
        out.write("\nendmodule\n")
        
        return out.getvalue()
    
    def _generate_extern_instance(self, name: str, comp) -> str:
        """Generate extern component instance.
        
        Gets the typename from __implementation__ method which may include
        parameterization and filelist information.
        """
        # Create an instance to call __implementation__
        try:
            instance = comp()
            impl_info = instance.__implementation__()
            module_name = impl_info.get("typename", comp.__name__)
        except Exception:
            # Fall back to class name if __implementation__ fails
            module_name = comp.__name__
        
        # Get connections from __bind__ if available
        connections = self._get_bindings(name)
        
        if connections:
            out = StringIO()
            out.write(f"    {module_name} {name}(\n")
            conn_strs = []
            for port, signal in connections:
                conn_strs.append(f"        .{port}({signal})")
            out.write(",\n".join(conn_strs))
            out.write("\n    );\n")
            return out.getvalue()
        else:
            return f"    {module_name} {name}();\n"
    
    def _get_bindings(self, inst_name: str) -> List[Tuple[str, str]]:
        """Extract bindings for an instance from __bind__ method."""
        if not hasattr(self.top_cls, '__bind__'):
            return []
        
        # Try AST-based approach first (works for source files)
        try:
            connections = self._get_bindings_from_source(inst_name)
            if connections:
                return connections
        except Exception:
            pass
        
        # Fall back to runtime approach (works for dynamically defined classes)
        try:
            return self._get_bindings_from_runtime(inst_name)
        except Exception:
            return []
    
    def _get_bindings_from_runtime(self, inst_name: str) -> List[Tuple[str, str]]:
        """Extract bindings by creating an instance and calling __bind__.
        
        This approach uses a custom tracer to capture attribute accesses.
        """
        connections = []
        
        # Create a mock instance that tracks attribute access
        class SignalTracer:
            def __init__(self, name):
                self._name = name
            
            def __getattr__(self, attr):
                return SignalTracer(f"{self._name}.{attr}")
            
            def __repr__(self):
                return self._name
        
        # Create a mock top instance
        mock_top = type('MockTop', (), {})()
        
        # Manually set attributes to avoid infinite recursion
        for field_name in self.top_cls.__dataclass_fields__:
            object.__setattr__(mock_top, field_name, SignalTracer(field_name))
        
        # Call __bind__ on the mock instance
        try:
            bindings = self.top_cls.__bind__(mock_top)
            
            for binding in bindings:
                if len(binding) == 2:
                    left, right = binding
                    left_str = str(left)
                    right_str = str(right)
                    
                    # Extract instance name and port from right side
                    if right_str.startswith(f"{inst_name}."):
                        port = right_str.split('.', 1)[1]
                        signal = left_str
                        connections.append((port, signal))
        except Exception:
            pass
        
        return connections
    
    def _get_bindings_from_source(self, inst_name: str) -> List[Tuple[str, str]]:
        """Extract bindings from source code using AST parsing."""
        method = getattr(self.top_cls, '__bind__')
        
        # Try to get source from the method
        try:
            source = inspect.getsource(method)
            tree = ast.parse(source)
            
            # Find the function definition
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == '__bind__':
                    return self._extract_connections_from_ast(node, inst_name)
        except (OSError, TypeError):
            pass
        
        # Try to get the source file of the class
        try:
            import sys
            class_module = sys.modules[self.top_cls.__module__]
            class_file = inspect.getsourcefile(class_module)
            if class_file:
                with open(class_file, 'r') as f:
                    file_source = f.read()
                
                # Parse the file and find the __bind__ method
                tree = ast.parse(file_source)
                bind_method = None
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == self.top_cls.__name__:
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name == '__bind__':
                                bind_method = item
                                break
                
                if bind_method:
                    return self._extract_connections_from_ast(bind_method, inst_name)
        except Exception:
            pass
        
        return []
    
    def _extract_connections_from_ast(self, func_node, inst_name: str) -> List[Tuple[str, str]]:
        """Extract connections from an AST function node."""
        connections = []
        
        # Look for return statements with tuples
        for stmt in func_node.body:
            if isinstance(stmt, ast.Return) and stmt.value:
                # Check if it's a tuple of tuples
                if isinstance(stmt.value, ast.Tuple):
                    for binding in stmt.value.elts:
                        if isinstance(binding, ast.Tuple) and len(binding.elts) == 2:
                            left = binding.elts[0]
                            right = binding.elts[1]
                            
                            # Extract signal names
                            left_name = self._extract_attr_name(left)
                            right_name = self._extract_attr_name(right)
                            
                            # Check if right side matches our instance
                            if right_name.startswith(f"{inst_name}."):
                                port = right_name.split('.', 1)[1]
                                signal = left_name
                                connections.append((port, signal))
        
        return connections
    
    def _extract_attr_name(self, node) -> str:
        """Extract attribute name from AST node like self.clock or self.counter1.clock."""
        if isinstance(node, ast.Attribute):
            value_name = self._extract_attr_name(node.value)
            if value_name == 'self':
                return node.attr
            return f"{value_name}.{node.attr}"
        elif isinstance(node, ast.Name):
            return node.id
        return ""
    
    def _generate_xtor_instance(self, name: str, comp) -> str:
        """Generate transactor instance.
        
        be-sv generates transactor modules with the component class name
        (no _xtor suffix). The module will have ports for clock, reset,
        and any input/output fields defined in the component.
        
        Note: The actual instance is generated by be-sv in the parent
        component module. This method is kept for backward compatibility
        but isn't used when be-sv successfully generates the hierarchy.
        """
        module_name = comp.__name__
        return f"    {module_name} {name}();\n"
    
    def _generate_xtor_registration(self, name: str, comp) -> str:
        """Generate transactor registration code for PyHDL-IF.
        
        This creates the API implementation wrapper and registers it.
        The API package (generated by pyhdl-if from JSON) provides the
        {Component}Api_impl class that bridges Python to the xtor_if.
        """
        out = StringIO()
        
        comp_name = comp.__name__
        
        out.write(f"        // Register {name} transactor\n")
        out.write(f"        {comp_name}Api_impl {name}_impl = new(top.{name}.xtor_if);\n")
        out.write(f"        pyhdl_if::pyhdl_if_registerObject(\n")
        out.write(f"            {name}_impl,\n")
        out.write(f"            \"top.{name}\",\n")
        out.write(f"            0\n")
        out.write(f"        );\n\n")
        
        return out.getvalue()
    
    def _generate_process_block(self, proc_name: str, proc) -> str:
        """Generate initial block for a process."""
        out = StringIO()
        
        out.write(f"    // Process: {proc_name}\n")
        out.write("    initial begin\n")
        
        # Get the method source and convert to SV
        method = proc.method
        if hasattr(method, '__func__'):
            method = method.__func__
        
        try:
            source = inspect.getsource(method)
            sv_code = self._convert_python_to_sv(source, is_async=True)
            out.write(sv_code)
        except Exception as e:
            out.write(f"        // Error generating process: {e}\n")
            out.write("        // TODO: Implement process code\n")
        
        out.write("    end\n\n")
        
        return out.getvalue()
    
    def _generate_sync_block(self, sync_name: str, sync) -> str:
        """Generate always block for a sync block."""
        out = StringIO()
        
        out.write(f"    // Sync block: {sync_name}\n")
        
        # Build sensitivity list
        sensitivity = []
        if sync.clock:
            sensitivity.append("posedge clock")
        if sync.reset:
            sensitivity.append("posedge reset")
        
        if not sensitivity:
            sensitivity.append("*")
        
        out.write(f"    always @({' or '.join(sensitivity)}) begin\n")
        
        # Get the method source and convert to SV
        method = sync.method
        if hasattr(method, '__func__'):
            method = method.__func__
        
        try:
            source = inspect.getsource(method)
            sv_code = self._convert_python_to_sv(source, is_async=False)
            out.write(sv_code)
        except Exception as e:
            out.write(f"        // Error generating sync block: {e}\n")
            out.write("        // TODO: Implement sync code\n")
        
        out.write("    end\n\n")
        
        return out.getvalue()
    
    def _convert_python_to_sv(self, source: str, is_async: bool = False) -> str:
        """Convert Python source code to SystemVerilog.
        
        This is a simplified converter that handles basic constructs.
        """
        out = StringIO()
        
        try:
            # Remove leading indentation to make it parseable
            lines = source.split('\n')
            if lines:
                # Find minimum indentation (excluding empty lines)
                min_indent = float('inf')
                for line in lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)
                
                # Remove the minimum indentation from all lines
                if min_indent != float('inf'):
                    normalized_lines = []
                    for line in lines:
                        if line.strip():
                            normalized_lines.append(line[min_indent:])
                        else:
                            normalized_lines.append('')
                    source = '\n'.join(normalized_lines)
            
            # Parse the Python source
            tree = ast.parse(source)
            
            # Find the function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    func_def = node
                    break
            
            if func_def:
                # Process the function body
                for stmt in func_def.body:
                    sv_stmt = self._convert_statement(stmt, indent=2)
                    if sv_stmt:
                        out.write(sv_stmt)
        except Exception as e:
            out.write(f"        // Conversion error: {e}\n")
        
        return out.getvalue()
    
    def _convert_statement(self, stmt, indent: int = 0) -> str:
        """Convert a single Python statement to SystemVerilog."""
        indent_str = "    " * indent
        
        if isinstance(stmt, ast.Assign):
            # Handle assignments like self.clock = 0
            targets = stmt.targets
            value = stmt.value
            
            if len(targets) == 1:
                target = targets[0]
                target_str = self._convert_expr(target)
                value_str = self._convert_expr(value)
                return f"{indent_str}{target_str} = {value_str};\n"
        
        elif isinstance(stmt, ast.Expr):
            # Handle expressions like print() or await
            if isinstance(stmt.value, ast.Call):
                return self._convert_call(stmt.value, indent)
            elif isinstance(stmt.value, ast.Await):
                # Handle await statements
                await_expr = stmt.value.value
                if isinstance(await_expr, ast.Call):
                    func = await_expr.func
                    if isinstance(func, ast.Attribute) and func.attr == 'wait':
                        # Convert self.wait(zdc.Time.ns(10)) to #10ns
                        if await_expr.args:
                            time_arg = await_expr.args[0]
                            time_str = self._extract_time_value(time_arg)
                            return f"{indent_str}#{time_str};\n"
        
        elif isinstance(stmt, ast.For):
            # Handle for loops
            target = self._convert_expr(stmt.target)
            iter_expr = stmt.iter
            
            out = StringIO()
            if isinstance(iter_expr, ast.Call) and isinstance(iter_expr.func, ast.Name):
                if iter_expr.func.id == 'range':
                    # Convert range to for loop
                    if len(iter_expr.args) == 1:
                        end = self._convert_expr(iter_expr.args[0])
                        out.write(f"{indent_str}for (int {target} = 0; {target} < {end}; {target}++) begin\n")
                    elif len(iter_expr.args) == 2:
                        start = self._convert_expr(iter_expr.args[0])
                        end = self._convert_expr(iter_expr.args[1])
                        out.write(f"{indent_str}for (int {target} = {start}; {target} < {end}; {target}++) begin\n")
                    
                    # Convert body
                    for body_stmt in stmt.body:
                        out.write(self._convert_statement(body_stmt, indent + 1))
                    
                    out.write(f"{indent_str}end\n")
                    return out.getvalue()
        
        elif isinstance(stmt, ast.If):
            # Handle if statements
            test = self._convert_expr(stmt.test)
            out = StringIO()
            out.write(f"{indent_str}if ({test}) begin\n")
            
            for body_stmt in stmt.body:
                out.write(self._convert_statement(body_stmt, indent + 1))
            
            if stmt.orelse:
                out.write(f"{indent_str}end else begin\n")
                for else_stmt in stmt.orelse:
                    out.write(self._convert_statement(else_stmt, indent + 1))
            
            out.write(f"{indent_str}end\n")
            return out.getvalue()
        
        return ""
    
    def _convert_call(self, call_node, indent: int = 0) -> str:
        """Convert a function call to SystemVerilog."""
        indent_str = "    " * indent
        
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
            
            if func_name == 'print':
                # Convert print to $display
                if call_node.args:
                    # Check for format string (BinOp with Mod for % formatting)
                    arg = call_node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                        # String formatting like "count: %d" % self.count
                        format_str = self._convert_expr(arg.left).strip('"')
                        
                        # Handle the value(s) being formatted
                        if isinstance(arg.right, ast.Tuple):
                            # Multiple values
                            values = [self._convert_expr(v) for v in arg.right.elts]
                            value_str = ', '.join(values)
                        else:
                            # Single value
                            value_str = self._convert_expr(arg.right)
                        
                        return f'{indent_str}$display("{format_str}", {value_str});\n'
                    else:
                        # Simple print without formatting
                        args = [self._convert_expr(a) for a in call_node.args]
                        arg_str = ', '.join(args)
                        return f'{indent_str}$display({arg_str});\n'
                else:
                    return f'{indent_str}$display();\n'
        
        return ""
    
    def _convert_expr(self, expr) -> str:
        """Convert a Python expression to SystemVerilog."""
        if isinstance(expr, ast.Attribute):
            # Handle attribute access like self.clock
            value = self._convert_expr(expr.value)
            if value == 'self':
                return expr.attr
            return f"{value}.{expr.attr}"
        
        elif isinstance(expr, ast.Name):
            if expr.id == 'self':
                return 'self'
            return expr.id
        
        elif isinstance(expr, ast.Constant):
            if isinstance(expr.value, str):
                return f'"{expr.value}"'
            return str(expr.value)
        
        elif isinstance(expr, ast.UnaryOp):
            if isinstance(expr.op, ast.Not):
                operand = self._convert_expr(expr.operand)
                return f"!{operand}"
        
        elif isinstance(expr, ast.BinOp):
            left = self._convert_expr(expr.left)
            right = self._convert_expr(expr.right)
            if isinstance(expr.op, ast.BitAnd):
                return f"({left} & {right})"
            elif isinstance(expr.op, ast.BitOr):
                return f"({left} | {right})"
            elif isinstance(expr.op, ast.Mod):
                # Used for string formatting
                return left
        
        elif isinstance(expr, ast.Compare):
            # Handle comparisons
            left = self._convert_expr(expr.left)
            if len(expr.ops) == 1 and len(expr.comparators) == 1:
                op = expr.ops[0]
                right = self._convert_expr(expr.comparators[0])
                
                if isinstance(op, ast.Eq):
                    return f"{left} == {right}"
                elif isinstance(op, ast.NotEq):
                    return f"{left} != {right}"
                elif isinstance(op, ast.Lt):
                    return f"{left} < {right}"
                elif isinstance(op, ast.Gt):
                    return f"{left} > {right}"
        
        elif isinstance(expr, ast.IfExp):
            # Ternary operator: a if cond else b -> cond ? a : b
            test = self._convert_expr(expr.test)
            body = self._convert_expr(expr.body)
            orelse = self._convert_expr(expr.orelse)
            return f"({test} ? {body} : {orelse})"
        
        return "expr"
    
    def _extract_time_value(self, time_arg) -> str:
        """Extract time value from zdc.Time.ns(10) expression."""
        if isinstance(time_arg, ast.Call):
            if isinstance(time_arg.func, ast.Attribute):
                if time_arg.func.attr == 'ns' and time_arg.args:
                    value = self._convert_expr(time_arg.args[0])
                    return f"{value}ns"
        return "10ns"
    
    def _generate_pytest_file(self) -> str:
        """Generate pytest file with testbench declared outside test function.
        
        The pytest file structure:
        1. Import testbench module (must be importable)
        2. Direct testbench construction (no fixture)
        3. Async test entrypoint
        """
        out = StringIO()
        
        # File header
        out.write('"""Auto-generated pytest file for HDL testbench.\n\n')
        out.write('This file is generated by zuspec-be-hdlsim and should be\n')
        out.write('loaded by pyhdl_pytest during simulation.\n\n')
        out.write('The testbench class is registered by SystemVerilog before\n')
        out.write('pytest runs. Constructing the testbench directly (tb = MyTB())\n')
        out.write('creates a runtime proxy with access to SV transactors.\n')
        out.write('"""\n')
        
        # Import the testbench class
        out.write(f'# Import testbench component class\n')
        out.write(f'# NOTE: This assumes the module is in Python path\n')
        out.write(f'from {self.top_cls.__module__} import {self.top_name}\n\n')
        
        # Example test (placeholder)
        out.write('async def test_example():\n')
        out.write('    """Example test - replace with actual tests.\n')
        out.write('    \n')
        out.write('    The testbench class is already registered by SystemVerilog.\n')
        out.write('    Simply construct it directly to get a runtime proxy.\n')
        out.write('    """\n')
        out.write(f'    tb = {self.top_name}()\n')
        out.write('    \n')
        out.write('    # TODO: Add test implementation\n')
        out.write('    # Example:\n')
        
        # Add example calls for each transactor
        if self._xtor_components:
            for name, comp in self._xtor_components.items():
                out.write(f'    # await tb.{name}.xtor_if.some_method(...)\n')
        
        out.write('    pass\n')
        
        return out.getvalue()
