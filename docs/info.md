# HatUno A: Two Protected Program Rings

243 one-bit cells whose wiring is read off the aperiodic Hat tiling (Smith, Myers, Kaplan, Goodman-Strauss 2023): the 87-cell Hat87
machine (rule "listen across edges 5 and 7"), plus loops and closed modules of rules {3} and {3,6}. Nothing is designed by hand except
the cell, the pins and four "receiver" cells whose position is also read off the tiling.

## How it works

Every cell updates on the rising edge from its wired neighbours with a selectable rule: OR (mode 0), AND (mode 1) or XOR (mode 2).
A stimulus sets one cell by index for one cycle; a scan chain over all 243 cells loads and reads any state. Reset is synchronous.

In XOR mode, closed rings of three cells keep their contents forever (each cell is the XOR of the other two), so a ring holds one of four
even words: 000, 011, 101, 110. Two such rings are used as **protected programs**:

- ring {13, 42, 71} drives receivers 15, 44 and 73;
- ring {1, 8, 27} drives receiver 22.

A receiver with ring cells m and d and a data input u computes `d XOR (NOT m AND u)`: depending on the program it passes u, inverts it,
or forces 0 or 1. The rings are never changed by the computation, yet they change how the tissue transforms data. With both rings at 000
the chip behaves exactly as the plain XOR machine. A third mode bit (`uio_in[6]`) adds Hat edge 6 on six nucleus cells.

With fixed programs the 87-cell machine is affine over GF(2); its exact maximal periods depend on the programs, from 168 cycles up to
4991220570.

## How to test

Pins: `ui_in[7:0]` cell index (0 to 242). `uio_in[0]` stimulus valid, `uio_in[1]` mode write enable with `uio_in[3:2]` the mode and
`uio_in[6]` edge 6, `uio_in[4]` scan enable, `uio_in[5]` scan in. `uo_out[0]` state of the indexed cell (combinational), `uo_out[1]` scan
out, `uo_out[2]` any cell excited.

1. Reset; write mode 2 (XOR). Shift in the 7-cell state at indices 153, 158, 161, 162, 163, 164, 165 (first bit shifted in lands at
   cell 242). Read it back with the probe. Clock 127 times: the state returns exactly; after 1 clock it differs.
2. In OR mode, stimulate cell 153 once and clock 20 times: exactly cells 153 to 165 light up and nothing else.
3. Two-program demonstration (`docs/board_program.md`, data in `test/board_program.json`): with ring {13,42,71} = 011 and edge 6 off,
   load two inputs that differ only in cell 24, once with ring {1,8,27} = 000 and once with 011. Read probes 23, 24, 52, 53, 81, 82 for 12
   clocks. The difference between the two responses changes with the second program (from clock 5 on), while both rings stay intact.
4. The other data rings can be read back through the six probes with a program-specific decoder (`test/decoder.json`).

`test/test.py` runs all of this (25 tests) through the pins at RTL and gate level.
