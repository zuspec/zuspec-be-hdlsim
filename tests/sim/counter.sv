// Simple counter DUT for simulation test
module counter #(
    parameter WIDTH = 8
) (
    input  logic clk,
    input  logic rst,
    input  logic enable,
    output logic [WIDTH-1:0] count
);

    always_ff @(posedge clk or posedge rst) begin
        if (rst)
            count <= '0;
        else if (enable)
            count <= count + 1;
    end

endmodule
