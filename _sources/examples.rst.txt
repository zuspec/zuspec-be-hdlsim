Examples
========

This page provides complete, working examples demonstrating various HDLSim 
backend use cases.

Example 1: Simple Counter
--------------------------

A basic counter testbench demonstrating the fundamentals.

RTL (counter.sv)
^^^^^^^^^^^^^^^^

.. code-block:: systemverilog

    module counter #(
        parameter WIDTH = 8
    ) (
        input  logic             clock,
        input  logic             reset,
        input  logic             enable,
        output logic [WIDTH-1:0] count
    );
        logic [WIDTH-1:0] count_reg;
        
        always_ff @(posedge clock) begin
            if (reset)
                count_reg <= '0;
            else if (enable)
                count_reg <= count_reg + 1;
        end
        
        assign count = count_reg;
    endmodule

Testbench (counter_tb.py)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import zuspec.dataclasses as zdc
    from zuspec.dataclasses.protocols import Extern, XtorComponent
    from zuspec.dataclasses import Signal, annotation_fileset
    
    # Clock/reset protocol
    class ClkRstIf:
        async def reset_assert(self):
            """Assert reset."""
            ...
        
        async def reset_deassert(self):
            """Deassert reset."""
            ...
        
        async def wait_cycles(self, n: int):
            """Wait N clock cycles."""
            ...
    
    # Clock/reset transactor
    @zdc.dataclass
    class ClkRstXtor(XtorComponent[ClkRstIf]):
        clock: Signal = zdc.output()
        reset: Signal = zdc.output()
    
    # Counter wrapper
    @zdc.dataclass
    class CounterDut(zdc.Component, Extern):
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        enable: Signal = zdc.input()
        count: Signal = zdc.output()
        
        @annotation_fileset(sources=["rtl/counter.sv"])
        def __post_init__(self):
            pass
    
    # Control transactor protocol
    class CounterControlIf:
        async def set_enable(self, enable: bool):
            """Set enable signal."""
            ...
        
        async def get_count(self) -> int:
            """Read current count value."""
            ...
    
    # Control transactor
    @zdc.dataclass
    class CounterControl(XtorComponent[CounterControlIf]):
        enable: Signal = zdc.output()
        count: Signal = zdc.input()
    
    # Top-level testbench
    @zdc.dataclass
    class CounterTB(zdc.Component):
        clkrst: ClkRstXtor = zdc.inst()
        dut: CounterDut = zdc.inst()
        ctrl: CounterControl = zdc.inst()
        
        def __bind__(self):
            return (
                (self.clkrst.clock, self.dut.clock),
                (self.clkrst.reset, self.dut.reset),
                (self.ctrl.enable, self.dut.enable),
                (self.dut.count, self.ctrl.count),
            )

Test (test_counter.py)
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import pytest
    
    @pytest.fixture
    def tb():
        from counter_tb import CounterTB
        return CounterTB()
    
    async def test_counter_reset(tb):
        """Test counter reset behavior."""
        # Reset the counter
        await tb.clkrst.reset_assert()
        await tb.clkrst.wait_cycles(5)
        await tb.clkrst.reset_deassert()
        
        # Check count is 0
        count = await tb.ctrl.get_count()
        assert count == 0
    
    async def test_counter_enable(tb):
        """Test counter counting."""
        # Reset and enable
        await tb.clkrst.reset_assert()
        await tb.clkrst.wait_cycles(5)
        await tb.clkrst.reset_deassert()
        
        await tb.ctrl.set_enable(True)
        await tb.clkrst.wait_cycles(10)
        
        # Count should be 10
        count = await tb.ctrl.get_count()
        assert count == 10
    
    async def test_counter_disable(tb):
        """Test counter stops when disabled."""
        await tb.clkrst.reset_assert()
        await tb.clkrst.wait_cycles(5)
        await tb.clkrst.reset_deassert()
        
        # Count for a while
        await tb.ctrl.set_enable(True)
        await tb.clkrst.wait_cycles(5)
        
        # Disable and wait
        await tb.ctrl.set_enable(False)
        count_before = await tb.ctrl.get_count()
        await tb.clkrst.wait_cycles(10)
        count_after = await tb.ctrl.get_count()
        
        # Count should not change
        assert count_before == count_after

Example 2: Wishbone Bus
-----------------------

A more complex example with a standard bus interface.

Bus Protocol
^^^^^^^^^^^^

.. code-block:: python

    class WishboneInitiatorIf:
        """Wishbone bus initiator protocol."""
        
        async def write(self, addr: int, data: int, sel: int = 0xF):
            """Single write transaction."""
            ...
        
        async def read(self, addr: int) -> int:
            """Single read transaction."""
            ...
        
        async def write_burst(self, addr: int, data: list[int]):
            """Burst write."""
            ...
        
        async def read_burst(self, addr: int, count: int) -> list[int]:
            """Burst read."""
            ...

Wishbone Transactor
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class WishboneInitiator(XtorComponent[WishboneInitiatorIf]):
        """Wishbone initiator transactor."""
        
        # Clock and reset
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        
        # Wishbone signals
        wb_adr: Signal = zdc.output()
        wb_dat_o: Signal = zdc.output()
        wb_dat_i: Signal = zdc.input()
        wb_sel: Signal = zdc.output()
        wb_cyc: Signal = zdc.output()
        wb_stb: Signal = zdc.output()
        wb_we: Signal = zdc.output()
        wb_ack: Signal = zdc.input()
        wb_err: Signal = zdc.input()
        wb_rty: Signal = zdc.input()

Memory DUT
^^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class WishboneMemory(zdc.Component, Extern):
        """Wishbone memory module."""
        
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        
        wb_adr: Signal = zdc.input()
        wb_dat_i: Signal = zdc.input()
        wb_dat_o: Signal = zdc.output()
        wb_sel: Signal = zdc.input()
        wb_cyc: Signal = zdc.input()
        wb_stb: Signal = zdc.input()
        wb_we: Signal = zdc.input()
        wb_ack: Signal = zdc.output()
        wb_err: Signal = zdc.output()
        
        @annotation_fileset(
            sources=["rtl/wb_memory.sv"],
            incdirs=["rtl/include"]
        )
        def __post_init__(self):
            pass

Testbench
^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class WishboneTB(zdc.Component):
        clkrst: ClkRstXtor = zdc.inst()
        initiator: WishboneInitiator = zdc.inst()
        memory: WishboneMemory = zdc.inst()
        
        def __bind__(self):
            return (
                # Clock/reset
                (self.clkrst.clock, self.initiator.clock),
                (self.clkrst.clock, self.memory.clock),
                (self.clkrst.reset, self.initiator.reset),
                (self.clkrst.reset, self.memory.reset),
                
                # Wishbone bus
                (self.initiator.wb_adr, self.memory.wb_adr),
                (self.initiator.wb_dat_o, self.memory.wb_dat_i),
                (self.memory.wb_dat_o, self.initiator.wb_dat_i),
                (self.initiator.wb_sel, self.memory.wb_sel),
                (self.initiator.wb_cyc, self.memory.wb_cyc),
                (self.initiator.wb_stb, self.memory.wb_stb),
                (self.initiator.wb_we, self.memory.wb_we),
                (self.memory.wb_ack, self.initiator.wb_ack),
                (self.memory.wb_err, self.initiator.wb_err),
            )

Tests
^^^^^

.. code-block:: python

    async def test_wb_basic_write_read(tb):
        """Test basic write and read."""
        await tb.clkrst.reset_pulse(10)
        
        # Write data
        await tb.initiator.write(0x1000, 0xDEADBEEF)
        
        # Read back
        data = await tb.initiator.read(0x1000)
        assert data == 0xDEADBEEF
    
    async def test_wb_burst_write(tb):
        """Test burst write operation."""
        await tb.clkrst.reset_pulse(10)
        
        test_data = [0x100, 0x200, 0x300, 0x400]
        base_addr = 0x2000
        
        # Burst write
        await tb.initiator.write_burst(base_addr, test_data)
        
        # Verify each location
        for i, expected in enumerate(test_data):
            actual = await tb.initiator.read(base_addr + i*4)
            assert actual == expected

Example 3: Multi-Component System
----------------------------------

Demonstrates a more complex system with multiple components and monitors.

System Architecture
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class UartTx(zdc.Component, Extern):
        """UART transmitter."""
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        tx_data: Signal = zdc.input()
        tx_valid: Signal = zdc.input()
        tx_ready: Signal = zdc.output()
        tx_out: Signal = zdc.output()
        
        @annotation_fileset(sources=["rtl/uart_tx.sv"])
        def __post_init__(self): pass
    
    @zdc.dataclass
    class UartRx(zdc.Component, Extern):
        """UART receiver."""
        clock: Signal = zdc.input()
        reset: Signal = zdc.input()
        rx_in: Signal = zdc.input()
        rx_data: Signal = zdc.output()
        rx_valid: Signal = zdc.output()
        rx_ready: Signal = zdc.input()
        
        @annotation_fileset(sources=["rtl/uart_rx.sv"])
        def __post_init__(self): pass

Driver and Monitor
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Driver protocol
    class UartDriverIf:
        async def send_byte(self, data: int): ...
        async def send_packet(self, data: bytes): ...
    
    # Monitor protocol  
    class UartMonitorIf:
        async def recv_byte(self) -> int: ...
        async def recv_packet(self, length: int) -> bytes: ...
    
    @zdc.dataclass
    class UartDriver(XtorComponent[UartDriverIf]):
        clock: Signal = zdc.input()
        tx_data: Signal = zdc.output()
        tx_valid: Signal = zdc.output()
        tx_ready: Signal = zdc.input()
    
    @zdc.dataclass
    class UartMonitor(XtorComponent[UartMonitorIf]):
        clock: Signal = zdc.input()
        rx_data: Signal = zdc.input()
        rx_valid: Signal = zdc.input()
        rx_ready: Signal = zdc.output()

Python Scoreboard
^^^^^^^^^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class UartScoreboard(zdc.Component):
        """Pure Python scoreboard component."""
        
        def __post_init__(self):
            self.sent_packets = []
            self.recv_packets = []
        
        def record_sent(self, data: bytes):
            """Record sent packet."""
            self.sent_packets.append(data)
        
        def record_received(self, data: bytes):
            """Record received packet."""
            self.recv_packets.append(data)
        
        def check(self) -> bool:
            """Verify sent == received."""
            return self.sent_packets == self.recv_packets

Complete Testbench
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    @zdc.dataclass
    class UartLoopbackTB(zdc.Component):
        """UART loopback testbench."""
        
        clkrst: ClkRstXtor = zdc.inst()
        driver: UartDriver = zdc.inst()
        monitor: UartMonitor = zdc.inst()
        tx: UartTx = zdc.inst()
        rx: UartRx = zdc.inst()
        scoreboard: UartScoreboard = zdc.inst()
        
        def __bind__(self):
            return (
                # Clock/reset
                (self.clkrst.clock, self.driver.clock),
                (self.clkrst.clock, self.monitor.clock),
                (self.clkrst.clock, self.tx.clock),
                (self.clkrst.clock, self.rx.clock),
                (self.clkrst.reset, self.tx.reset),
                (self.clkrst.reset, self.rx.reset),
                
                # Driver -> TX
                (self.driver.tx_data, self.tx.tx_data),
                (self.driver.tx_valid, self.tx.tx_valid),
                (self.tx.tx_ready, self.driver.tx_ready),
                
                # TX -> RX (serial)
                (self.tx.tx_out, self.rx.rx_in),
                
                # RX -> Monitor
                (self.rx.rx_data, self.monitor.rx_data),
                (self.rx.rx_valid, self.monitor.rx_valid),
                (self.monitor.rx_ready, self.rx.rx_ready),
            )

Advanced Test
^^^^^^^^^^^^^

.. code-block:: python

    async def test_uart_loopback_with_scoreboard(tb):
        """Test UART loopback with scoreboard checking."""
        await tb.clkrst.reset_pulse(10)
        
        # Test data
        test_packets = [
            b"Hello",
            b"World",
            b"Zuspec HDLSim!",
        ]
        
        # Send and monitor in parallel
        async def sender():
            for packet in test_packets:
                await tb.driver.send_packet(packet)
                tb.scoreboard.record_sent(packet)
        
        async def receiver():
            for _ in test_packets:
                packet = await tb.monitor.recv_packet(len(packet))
                tb.scoreboard.record_received(packet)
        
        # Run concurrently
        import asyncio
        await asyncio.gather(sender(), receiver())
        
        # Check scoreboard
        assert tb.scoreboard.check(), "Mismatch detected!"

See Also
--------

* :doc:`quickstart` - Getting started guide
* :doc:`components` - Component types reference
* :doc:`dfm_integration` - DFM workflow setup
