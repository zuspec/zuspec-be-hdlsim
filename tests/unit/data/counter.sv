// Simple counter module for testing Extern functionality
module counter(
    input clock,
    input reset,
    output reg[31:0] count);

    always @(posedge clock or posedge reset) begin
        if (reset) begin
            count <= {32{1'b0}};
        end else begin
            count <= count + 1;
        end
    end
endmodule
