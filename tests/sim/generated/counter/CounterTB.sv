module CounterTB(
  output logic ctrl_clk_out,
  output logic ctrl_rst_out,
  output logic ctrl_enable_out,
  input logic [7:0] ctrl_count_in
);

  CounterControlXtor ctrl (
    .clk_out(/* unknown expr */),
    .rst_out(/* unknown expr */),
    .enable_out(/* unknown expr */),
    .count_in(/* unknown expr */)
  );

endmodule
