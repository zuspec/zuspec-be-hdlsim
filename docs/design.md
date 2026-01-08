# Zuspec Backend HDLSim

This backend package supports co-simulating Zuspec descriptions with
existing HDL (eg Verilog) designs. This process starts with a single top-level
Zuspec component class that instances all required elements:
- Extern classes that specify how existing Verilog sources are integrated
- XtorComponent classes that specify generation of Verilog transactors
  and their integration with Python
- Zuspec component classes that stay in Python
- Zuspec component classes that are retargetable, and could be implemented in SV

This description is processed two ways to create two views of the design:
- By a SystemVerilog generator that implements the portion simulated by the
  hardware simulator. This generator is called during the build flow
- By a Python runtime generator (similar to what's in 'rt' of zuspec-dataclasses)
  that produces an executable Python implementation for behavior that stays
  in Python (at minimum, the top level). This generator runs when the simulator
  runs and launches Zuspec. The implementation must attach to the elements 
  exposed by the simulation

## Initial Assumptions
- All Extern-derived component classes are implemented in SV
- All XtorComponent-derived classes generate SV code and are implemented in SV
- Everything else is implemented in Python
- Critical: A Python-implemented component cannot connect at the signal level
  to a SV-implemented component.

We will revisit these assumptions in the future as we make things more flexible.

## Checker
zuspec-dataclasses provides a Profile-driven checker framework. hdlsim must 
define an HDLTestbench profile and companion checker. This checker must enforce
rules, such as signal-level connection between domains.

## Operation: SV Generator
The SystemVerilog generator accepts the top-level testbench Zuspec component
class and generates SV for the elements that must be in SystemVerilog.

It creates two modules:
- <TBComp>_hdl: Implements the 'HDL' portions of the Zuspec description. Instances
  extern components and Xtors; Connects their input/output signals as required.
- <TBComp>: top-level module responsible for connecting HDL components to
  Python, and launching the Pytest at simulation runtime. This module instances
  the '_hdl' module.

Generation of XtorComponents is two-step:
- The SV generator (zuspec-be-sv) is used to produce the SystemVerilog portions 
  of the transactor
- A generator in hdlsim produces the PyHDL-IF wrapper classes. Let's define a
  proper public generator interface for PyHDL-IF as part of this project so we
  can call something reliable.

### SV / Python Connection
The <TBComp> module must import the package of each transactor type used in the
testbench environment:

```verilog
module <TBComp>;
    import pyhdl_if::*;
    import xtor_1::*;

endmodule
```
On startup (initial block), the <TBComp> module must register each transactor 
instance with the pyhdl_if package.

```verilog
module <TBComp>;
    import pyhdl_if::*;
    import xtor_1::*;

    <TBComp>_hdl top();

    initial begin
      typedef virtual xtor_1_xtor_if <#(parameters)> xtor_1_i1_vif;
      typedef xtor_1_exp_impl #(xtor_1_i1_vif) xtor1_i1_wrap;

      xtor1_i1_wrap = new(top.xtor1_i1);

      // TODO: register with pyhdl_if

      // TODO: Call Python to properly configure the ObjFactory to
      // use the be-hdlsim one.

      // Run pytest
      pyhdl_pytest();
      $finish;
    end

endmodule

```

## Operation: Python Generator
The Python generator is an ObjFactory-like class that produces an executable Python
object having the same API as the input Zuspec class. This generator will be invoked
from within a simulation, and can access (via PyHDL-IF) wrapper classes registered
by the <TbComp> module prior to launching the pytest.

## DV Flow Manager Integration

The HDL generator must be packaged as a `DFM <https://dv-flow.github.io>`_ task. A parameter 
on the task specifies the root Zuspec Testbench component typename. This task outputs filesets 
that specify the ordered SV sources to be compiled.


# How it's intended to be used

Assume we have a testbench like this:

```python

@zdc.dataclass
class MyTB(zdc.Component)
    dut : DutWrapper = zdc.inst()
    xtor : RVXtor = zdc.inst()
    clkrst : ClkRstGenXtor = zdc.inst()

    def __bind__(self):
        return (
            (self.xtor.xtor_if, self.dut.rv_if),
            (self.clkrst.clock, self.dut.clock),
            (self.clkrst.reset, self.dut.reset),
        )
```

We have a design (DutWrapper) that we're testing. We're driving the data interface
with 'xtor', and clock and reset with the 'clkrst' transactor.

We'll have a test that looks something like this:

```python
from zuspec.be.hdlsim import HDLSim

async def test_reset(zuspec_sim : HDLSim):
    tb = zuspec_sim.create(MyTB)

    await tb.clkrst.count(100)
    await tb.clkrst.assert_reset(False)

    ...

```

The build/run flow will be specified on a `DV Flow Manager <https://dv-flow.github.io>`_ spec file:

```yaml
package:
  name: my_tb

  tasks:
  - name: GenTB
    uses: zuspec.be.hdlsim.GenTB
    with:
      class: MyTB
  - name: SimImage
    uses: hdlsim.vlt.SimImage
    needs: [GenTB]
  - name: SimRun
    uses: hdlsim.vlt.SimRun
    needs: [SimImage]
    with:
      plusargs: [pyhdl.pytest=test_reset]
```

When the user runs `dfm run SimRun`:
- SystemVerilog will be generated for GenTB and the dependent elements
- Verilator will compile the SystemVerilog for the testbench and PyHDL library
- The verilator-compiled image is run, which invokes the pytest via pyhdl

The bulk of your changes must be in the zuspec-be-hdlsim project. 


## References
- pyhdl-if plug-in to understand how the Python/SystemVerilog interface works
- 'initiator.py' and 'target.py' in the fwvip-wb-zuspec project to see what 
  Zuspec transactors look like
- `dv-flow-mgr <https://dv-flow.github.io>`_ to understand what flow.dv/flow.yaml files look like
- dv-flow-libhdlsim to undestand what `DFM <https://dv-flow.github.io>`_ tasks look like, and how they're registered