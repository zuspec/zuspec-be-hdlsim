interface InitiatorXtor_xtor_if;

  // Local signals
  logic _ack;
  logic [31:0] _adr = 0;
  logic [31:0] _dat_r;
  logic [31:0] _dat_w = 0;
  logic _err;
  logic _req = 0;
  logic [3:0] _sel = 0;
  logic _we = 0;
  logic clock;
  logic reset;

  task access(
    input logic [31:0] adr,
    input logic [31:0] dat_w,
    input logic [31:0] sel,
    input logic [31:0] we,
    output logic __ret_0,
    output logic [31:0] __ret_1);
    $display("%0t: [access] Task started", $time);
    _adr = adr;
    _dat_w = dat_w;
    _sel = sel;
    _we = we;
    @(posedge clock);
    $display("%0t:   While loop checking: reset=%b", $time, reset);
    while (reset) begin
      $display("%0t:     Inside while loop, waiting...", $time);
      @(posedge clock);
    end
    $display("%0t:   While loop exited", $time);
    _req = 1;
    @(posedge clock);
    $display("%0t:   While loop checking: !_ack=%b", $time, !_ack);
    while (!_ack) begin
      $display("%0t:     Inside while loop, waiting...", $time);
      @(posedge clock);
    end
    $display("%0t:   While loop exited", $time);
    _req = 0;
    __ret_0 = _err;
    __ret_1 = _dat_r;
    $display("%0t: [access] Task completed", $time);
  endtask

endinterface

module InitiatorXtor #(
  parameter int DATA_WIDTH = 32,
  parameter int ADDR_WIDTH = 32
)(
  input  clock,
  input  reset
);

  logic [31:0] _adr;
  logic [31:0] _dat_w;
  logic [31:0] _dat_r;
  logic [3:0] _sel;
  logic _we;
  logic _err;
  logic _req;
  logic _ack;
  logic _req_state;

  always @(posedge clock or posedge reset) begin
    if (reset) begin
      _req_state <= 0;
      init_cyc <= 0;
    end else begin
      case (_req_state)
        0: begin
          _ack <= 0;
          if (_req) begin
            init_cyc <= 1;
            init_adr <= _adr;
            init_dat_w <= _dat_w;
            init_we <= _we;
            init_sel <= _sel;
            _req_state <= 1;
          end
        end
        1: begin
          if (init_ack) begin
            _ack <= 1;
            _req_state <= 0;
            _dat_r <= init_dat_r;
            _err <= init_err;
            init_cyc <= 0;
          end
        end
      endcase
    end
  end

  // Instantiate interface for xtor_if
  InitiatorXtor_xtor_if xtor_if();

  // Connect module signals to interface
  assign xtor_if._ack = _ack;
  assign _adr = xtor_if._adr;
  assign xtor_if._dat_r = _dat_r;
  assign _dat_w = xtor_if._dat_w;
  assign xtor_if._err = _err;
  assign _req = xtor_if._req;
  assign _sel = xtor_if._sel;
  assign _we = xtor_if._we;
  assign xtor_if.clock = clock;
  assign xtor_if.reset = reset;

endmodule
