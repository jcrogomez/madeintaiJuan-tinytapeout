// Tiny Tapeout wrapper for HatUno A (243 binary cells wired from the Hat tiling, two protected program rings).
// Cell rule selectable OR / AND / XOR; stimulus by index; one scan chain; combinational probe. No uio outputs.
`default_nettype none
module tt_um_jcrogomez_bc3 (
    input wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena,
    input wire clk,
    input wire rst_n
);
    wire [242:0] state_bits;
    wire scan_out;
    // ui_in[7:0] = cell index: stimulated cell when uio_in[0] (stimulus valid) is high; probed cell always.
    // uio_in[0] stimulus valid, uio_in[1] mode write enable, uio_in[3:2] mode (0 OR, 1 AND, 2 XOR), uio_in[6] mode bit 2 (enable hat edge 6 on six nucleus cells),
    // uio_in[4] scan enable, uio_in[5] scan in.
    bc3_core core (
        .clk(clk), .rst_n(rst_n),
        .stim_valid(uio_in[0] & ena), .stim_idx(ui_in),
        .mode_in({uio_in[6], uio_in[3:2]}), .mode_we(uio_in[1] & ena),
        .scan_en(uio_in[4] & ena), .scan_in(uio_in[5]),
        .scan_out(scan_out), .state_bits(state_bits)
    );
    wire probe = (ui_in < 8'd243) ? state_bits[ui_in] : 1'b0;
    wire any_excited = |state_bits;
    assign uo_out = {5'b00000, any_excited, scan_out, probe};
    assign uio_out = 8'h00;
    assign uio_oe = 8'h00;
    wire _unused = &{uio_in[7], 1'b0};
endmodule
`default_nettype wire
