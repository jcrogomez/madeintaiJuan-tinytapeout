![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# made in TaiJuan — Tiny Tapeout

**HatUno A: two protected program rings on an aperiodic tissue.** A Tiny Tapeout design (sky130, 1×2 tiles) by Juan Carlos Romero.

243 one-bit cells are wired by reading the neighbour relations of the aperiodic Hat monotile tiling. In XOR mode, a closed ring of three
cells holding an even-parity word (000, 011, 101 or 110) keeps it unchanged at every clock. Two such rings act as **protected programs**:
they select whether four receiver cells pass, invert, clear or set their data input. The XOR evolution never modifies the programs (they
are written only through the scan chain or the stimulus), yet they change how the tissue transforms data, and that change can be observed
through the pins without reading the programs.

**Status:** not yet fabricated. Verified so far outside this repository's CI: RTL and gate-level tests (25/25), hardening with LibreLane,
and the Tiny Tapeout precheck. The official GitHub Actions flow runs here.

- What it does and how to test it: [docs/info.md](docs/info.md)
- Board procedure for the two-program demonstration: [docs/board_program.md](docs/board_program.md)
- Testbench (cocotb, RTL and gate level): [test/](test/)

The repository name is generic on purpose: the chip name may change between shuttles.

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that makes it easier and cheaper than ever to get digital and analog designs manufactured on a
real chip. Learn more at https://tinytapeout.com.
