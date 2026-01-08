// Auto-generated testbench module for CounterTB
module CounterTB_tb;
    import pyhdl_if::*;

    CounterTB top();

    initial begin
        // Initialize pyhdl-if
        pyhdl_if_start();

        // Register ctrl transactor
        CounterControlXtorApi_impl ctrl_impl = new(top.ctrl.xtor_if);
        pyhdl_if::pyhdl_if_registerObject(
            ctrl_impl,
            "top.ctrl",
            0
        );


        // Configure be-hdlsim ObjFactory
        begin
            PyObject config_mod, config_func, args, result;
            PyGILState_STATE state;

            state = PyGILState_Ensure();

            // Import zuspec.be.hdlsim module
            config_mod = pyhdl_pi_if_HandleErr(
                PyImport_ImportModule("zuspec.be.hdlsim")
            );

            if (config_mod != null) begin
                // Get configure_objfactory function
                config_func = PyObject_GetAttrString(
                    config_mod, "configure_objfactory"
                );

                if (config_func != null) begin
                    // Call with testbench class path
                    args = PyTuple_New(1);
                    void'(PyTuple_SetItem(args, 0,
                        PyUnicode_FromString(
                            "counter_tb_with_bindings.CounterTB"
                        )
                    ));

                    result = pyhdl_pi_if_HandleErr(
                        PyObject_Call(config_func, args, null)
                    );

                    Py_DecRef(args);
                    if (result != null) Py_DecRef(result);
                    Py_DecRef(config_func);
                end
                Py_DecRef(config_mod);
            end

            PyGILState_Release(state);
        end

        // Launch pytest
        pyhdl_pytest(".");  // Run tests in current directory
        $finish;
    end

endmodule
