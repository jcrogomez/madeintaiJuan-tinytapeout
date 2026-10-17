# Board program: two programs, one tissue

Not yet run on silicon. Exact expected values are in `test/board_program.json`; `t24_board_program_A` in `test/test.py` replays them at
RTL and gate level. Board clock: 100 kHz; every step goes through the pins.

## What it shows

With the same central program (ring {13, 42, 71} = 011), edge 6 off, the same data rings and the same two external inputs (x_a and x_b
= x_a with cell 24 flipped), changing **only** the second program (ring {1, 8, 27}: 000 → 011) changes the **difference** between the
responses to the two inputs, from clock 5 on. The difference cancels the constant footprint of the stored programs, so what changes is
how the tissue transforms data. Both program rings stay intact, and the data rings are read back with the decoder of the current program.

## Pins

`ui_in[7:0]` cell index; `uio_in[0]` stimulus; `uio_in[1]` mode write with `uio_in[3:2]` mode (2 = XOR) and `uio_in[6]` edge 6;
`uio_in[4]` scan enable; `uio_in[5]` scan in; `uo_out[0]` combinational probe of the indexed cell (reading does not advance the clock).

## Procedure (each of the 4 runs, in the order of the JSON)

1. Reset, XOR mode without edge 6, scan in `carga` (the full 87-cell block; cells 87–242 at 0).
2. **Phase 1:** at t = 0..11 read probes 23, 24, 52, 53, 81, 82, one clock between reads. Must equal `fase1_lecturas`.
3. **Phase 2:** reset, same load, mode sequence 101110 (1 = edge 6 on) for T = 12: at step t write the mode of step t+1 (that clock still
   evolves with the mode of step t). Reads must equal `fase2_lecturas`.
4. **Decode:** each functional is the XOR of its listed reads (`test/decoder.json`, context `011|<ring 2>`) plus its constant; must equal
   `funcionales[].valor`.
5. **Final read** of all 243 cells: equals `final_fase2`; rings {13,42,71} and {1,8,27} unchanged.

**Pass criterion:** the 4 runs match bit by bit, and Δ(ring 2 = 000) ≠ Δ(ring 2 = 011) on the phase-1 reads.
