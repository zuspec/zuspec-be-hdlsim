"""Testbench definition with proper signal bindings."""
import zuspec.dataclasses as zdc
from typing import Protocol


class CounterDUT(zdc.Extern):
    """Wrapper for counter.sv DUT."""
    clk: zdc.bit = zdc.input()
    rst: zdc.bit = zdc.input()
    enable: zdc.bit = zdc.input()
    count: zdc.u8 = zdc.output()
    
    def __implementation__(self):
        """Specify DUT implementation."""
        return {
            "typename": "counter",
            "sources": []
        }


class ICounterControl(Protocol):
    """Protocol for counter control transactor."""
    
    async def reset(self) -> None:
        """Assert reset."""
        ...
    
    async def set_enable(self, en: bool) -> None:
        """Set enable signal."""
        ...


@zdc.dataclass
class CounterControlXtor(zdc.XtorComponent[ICounterControl]):
    """Counter control transactor with actual ports."""
    # Ports that connect to DUT
    clk_out: zdc.bit = zdc.output()
    rst_out: zdc.bit = zdc.output()
    enable_out: zdc.bit = zdc.output()
    count_in: zdc.u8 = zdc.input()
    
    async def reset(self) -> None:
        """Assert reset."""
        pass  # Implementation in SV
    
    async def set_enable(self, en: bool) -> None:
        """Set enable signal."""
        pass  # Implementation in SV


@zdc.dataclass
class CounterTB(zdc.Component):
    """Counter testbench with signal bindings."""
    dut: CounterDUT = zdc.inst()
    ctrl: CounterControlXtor = zdc.inst()
    
    def __bind__(self):
        """Bind signals between DUT and control."""
        return (
            (self.ctrl.clk_out, self.dut.clk),
            (self.ctrl.rst_out, self.dut.rst),
            (self.ctrl.enable_out, self.dut.enable),
            (self.dut.count, self.ctrl.count_in),
        )
