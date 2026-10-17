"""Pin-only tests for the B + C3 tissue (tt_um_jcrogomez_bc3). Clock is pulsed manually; the probe is combinational.
Reset is synchronous. Vectors come from test/vectors.json (states built per factor of the XOR minimal polynomial)."""
import json
from pathlib import Path
import cocotb
from cocotb.triggers import Timer

V = json.loads((Path(__file__).parent / "vectors.json").read_text())
N = V["n"]; INS = V["entradas"]; EST = V["estados"]
STIM, MODE_WE, SCAN_EN, SCAN_IN = 1 << 0, 1 << 1, 1 << 4, 1 << 5
XOR = 2
XOR_A6 = 6            # mode bit 2 (uio[6]) enables hat edge 6 on six nucleus cells
A6 = {int(k): v for k, v in V.get("arista6", {}).items()}

async def settle(ns=100):
    await Timer(ns, unit="ns")

async def pulse(dut):
    dut.clk.value = 0; await settle()
    dut.clk.value = 1; await settle()
    dut.clk.value = 0; await settle()

async def reset(dut):
    dut.ena.value = 1; dut.ui_in.value = 0; dut.uio_in.value = 0; dut.clk.value = 0; dut.rst_n.value = 0
    await pulse(dut); await pulse(dut)
    dut.rst_n.value = 1; await settle()

async def set_mode(dut, mode):
    """mode[1:0] on uio[3:2], mode[2] on uio[6]"""
    dut.uio_in.value = MODE_WE | ((mode & 3) << 2) | (((mode >> 2) & 1) << 6); await pulse(dut); dut.uio_in.value = 0

async def scan_load(dut, cells):
    """Shift in a state: first bit in ends at q[N-1], so send v[N-1] ... v[0]."""
    s = set(cells)
    for i in range(N - 1, -1, -1):
        dut.uio_in.value = SCAN_EN | (SCAN_IN if i in s else 0); await pulse(dut)
    dut.uio_in.value = 0

async def scan_read(dut):
    """Shift out all bits (destructive): outputs q[N-1], q[N-2], ..., q[0]."""
    out = []
    for _ in range(N):
        dut.uio_in.value = SCAN_EN; await settle(); out.append(int(dut.uo_out.value) >> 1 & 1); await pulse(dut)
    dut.uio_in.value = 0
    return set(i for i, b in zip(range(N - 1, -1, -1), out) if b)

async def read_all(dut):
    dut.uio_in.value = 0; on = set()
    for i in range(N):
        dut.ui_in.value = i; await settle()
        if int(dut.uo_out.value) & 1: on.add(i)
    return on

async def run(dut, k):
    dut.uio_in.value = 0
    for _ in range(k): await pulse(dut)

async def stim(dut, i):
    dut.ui_in.value = i; dut.uio_in.value = STIM; await pulse(dut); dut.uio_in.value = 0

def model_xor(on, k, a6=False):
    x = set(on)
    for _ in range(k):
        x = {i for i in range(N) if (sum(1 for s in INS[i] if s in x) + (1 if (a6 and i in A6 and A6[i] in x) else 0)) % 2 == 1}
    return x

HD_RING_ = (13, 42, 71); HD_REC_ = {15: (13, 42, 20), 44: (42, 71, 49), 73: (71, 13, 78), 22: (8, 27, 24)}   # receptoras: (m, d, u); 15, 44, 73: anillo {13,42,71}; 22: anillo {1,8,27}
def hd_model(on, k, a6=False):
    """Modelo del chip (k pasos XOR): como model_xor, pero las receptoras 15, 44, 73 y 22 calculan d ^ (~m & u)."""
    x = set(on)
    for _ in range(k):
        y = model_xor(x, 1, a6=a6)
        for r, (m, d, u) in HD_REC_.items():
            y.discard(r)
            if (d in x) ^ ((m not in x) and (u in x)): y.add(r)
        x = y
    return x

def any_bit(dut): return int(dut.uo_out.value) >> 2 & 1

@cocotb.test()
async def t0_reset_all_zero(dut):
    await reset(dut)
    assert await read_all(dut) == set(), "cells not zero after reset"
    assert any_bit(dut) == 0

@cocotb.test()
async def t1_scan_roundtrip(dut):
    await reset(dut); await set_mode(dut, XOR)
    cells = EST["13r_periodo_127"]["celdas"]
    await scan_load(dut, cells)
    assert await read_all(dut) == set(cells), "probe after scan load"
    assert any_bit(dut) == 1
    assert await scan_read(dut) == set(cells), "scan out"

async def check_period(dut, name):
    e = EST[name]; cells = e["celdas"]; T = e["valor"]
    await reset(dut); await set_mode(dut, XOR); await scan_load(dut, cells)
    s0 = await read_all(dut); assert s0 == set(cells)
    await run(dut, 1); s1 = await read_all(dut); assert s1 != s0, "%s: state unchanged after 1 cycle" % name
    assert s1 == model_xor(s0, 1), "%s: step 1 differs from the XOR model" % name
    await run(dut, T - 1); sT = await read_all(dut)
    assert sT == s0, "%s: period %d not observed" % (name, T)

@cocotb.test()
async def t2_period_127_module13(dut): await check_period(dut, "13r_periodo_127")

@cocotb.test()
async def t3_period_8_module13(dut): await check_period(dut, "13r_periodo_8")

@cocotb.test()
async def t4_period_15_module77(dut): await check_period(dut, "77r_periodo_15")

@cocotb.test()
async def t5_period_4_module77(dut): await check_period(dut, "77r_periodo_4")

@cocotb.test()
async def t6_period_1016_module13_sum(dut): await check_period(dut, "13r_periodo_1016")

@cocotb.test()
async def t7_transient_dies_in_8(dut):
    e = EST["77r_transitorio_8"]
    await reset(dut); await set_mode(dut, XOR); await scan_load(dut, e["celdas"])
    await run(dut, 7); assert await read_all(dut) != set(), "transient state died before 8 cycles"
    await run(dut, 1); assert await read_all(dut) == set(), "transient state alive after 8 cycles"
    assert any_bit(dut) == 0

@cocotb.test()
async def t8_or_flood_stays_in_module13(dut):
    await reset(dut)                      # mode resets to OR
    await stim(dut, V["offsets"]["13r"])
    await run(dut, 20)
    on = await read_all(dut); mod13 = set(range(V["offsets"]["13r"], V["offsets"]["13r"] + 13))
    assert on == mod13, "OR flood: expected exactly the 13 cells of the cut-out, got %d cells" % len(on)

@cocotb.test()
async def t9_xor_model_50_cycles(dut):
    cells = set(EST["77r_periodo_15"]["celdas"]) ^ set(EST["13r_periodo_127"]["celdas"]) ^ set(range(0, 87, 7))
    await reset(dut); await set_mode(dut, XOR); await scan_load(dut, cells)
    await run(dut, 50)
    assert await read_all(dut) == hd_model(cells, 50), "50-cycle XOR evolution differs from the receiver model"


@cocotb.test()
async def t10_witness_segments(dut):
    """Tramos de 2000 ciclos de dos estados testigo (anillo {13,42,71} en 000 y en 011) contra el modelo."""
    W = json.loads((Path(__file__).parent / "witnesses.json").read_text())
    for key in ("000", "011"):
        x0 = set(W[key]["x0_bloque87"])
        await reset(dut); await set_mode(dut, XOR); await scan_load(dut, x0)
        assert await read_all(dut) == x0, "scan load of witness " + key
        await run(dut, 2000)
        assert await read_all(dut) == hd_model(x0, 2000), "witness %s differs from the receiver model after 2000 cycles" % key

@cocotb.test()
async def t11_edge6_model_50_cycles(dut):
    """With edge 6 enabled the six cells get a third input; compare 50 cycles against the model with that semantics (deduplicated neighbours)."""
    cells = set(V["estado_32760"]["celdas"]) ^ set(range(1, 87, 5))
    await reset(dut); await set_mode(dut, XOR_A6); await scan_load(dut, cells)
    await run(dut, 50)
    assert await read_all(dut) == hd_model(cells, 50, a6=True), "edge-6 evolution differs from the receiver model"
    assert hd_model(cells, 50, a6=True) != hd_model(cells, 50, a6=False), "edge 6 changed nothing in 50 cycles: test not discriminating"

@cocotb.test()
async def t12_edge6_off_keeps_57(dut):
    """Mode 2 (edge 6 off) must still be the plain {5,7} machine: compare against the model without edge 6."""
    cells = set(V["estado_32760"]["celdas"])
    await reset(dut); await set_mode(dut, XOR); await scan_load(dut, cells)
    await run(dut, 40)
    assert await read_all(dut) == hd_model(cells, 40, a6=False), "edge 6 leaked into mode 2 (receiver model)"

# --- Paridades del banco leídas desde el núcleo ---
import random
RINGS = [[0, 2, 39], [1, 8, 27], [5, 11, 83], [10, 58, 60], [13, 42, 71], [25, 34, 40], [29, 31, 68], [30, 37, 56], [54, 63, 69], [59, 66, 85]]
FEEDS = [(2, 27, 40), (11, 60, 85), (31, 56, 69)]          # celdas de anillo que alimentan los tres ciclos de un sentido
READ = [(24, 23), (82, 81), (53, 52)]                       # D_{a,b}(t) = q_a(t+4) ^ q_a(t+1) ^ q_b(t+3) ^ q_b(t)
WORDS = [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]

def model_step(x, a6=False, s=None):
    x = hd_step(x, a6=a6)
    return x | {s} if s is not None else x

def sigmas(x): return tuple(sum(c in x for c in f) % 2 for f in FEEDS)

RING2_BANK_OK = WORDS   # el anillo {1,8,27} conserva las tres paridades en sus cuatro palabras
RING2_P11_OK = [(0, 0, 0), (1, 0, 1)]   # q[8] = 0: protocolo de 11 bits intacto; con q[8] = 1 fallan las ecuaciones 3 y 5–10

def context(rng, target, ring2_words=RING2_BANK_OK):
    """Palabras pares en los 10 anillos con las tres sigma pedidas; resto de las N celdas al azar. Anillo 1 en 000; anillo 2 en ring2_words."""
    while True:
        x = {i for i in range(N) if rng.random() < 0.5}
        for r in RINGS:
            w = WORDS[0] if r == [13, 42, 71] else (rng.choice(ring2_words) if r == list(HD_RING2) else rng.choice(WORDS))
            x -= set(r); x |= {c for c, b in zip(r, w) if b}
        if sigmas(x) == target: return x

def ring_words(x): return [tuple(int(c in x) for c in r) for r in RINGS]

async def probe(dut, cells):
    dut.uio_in.value = 0; out = {}
    for i in cells:
        dut.ui_in.value = i; await settle(); out[i] = int(dut.uo_out.value) & 1
    return out

async def observe(dut, x, alternate):
    """Un paso (t=1) y cuatro más leyendo las seis celdas en t=1..5; devuelve (D, ingenua, estado del modelo)."""
    cells = [c for ab in READ for c in ab]; q = []; prev = False      # el modo vigente al entrar es XOR sin a6
    for step in range(5):
        if alternate:
            new = step % 2 == 1
            await set_mode(dut, XOR_A6 if new else XOR)               # este flanco evoluciona con el modo ANTERIOR (latencia de un flanco)
            x = model_step(x, a6=prev); prev = new
        else:
            await run(dut, 1); x = model_step(x)
        q.append(await probe(dut, cells))
    D = tuple(q[4][a] ^ q[1][a] ^ q[3][b] ^ q[0][b] for a, b in READ)
    return D, q[4][24] ^ q[1][24], x

@cocotb.test()
async def t13_bank_parities_from_nucleus(dut):
    rng = random.Random(1016); seen = set(); naive_ok = 0; n = 0
    for target in [tuple((k >> j) & 1 for j in range(3)) for k in range(8)] * 2:
        n += 1; alternate = n % 2 == 0
        x = context(rng, target)
        await reset(dut); await set_mode(dut, XOR); await scan_load(dut, x)
        assert await read_all(dut) == x, "scan load"
        D, naive, xm = await observe(dut, x, alternate)
        assert D == target, "context %d: D=%s, expected sigma=%s" % (n, D, target)
        final = await read_all(dut)
        assert final == xm, "context %d: final state differs from the XOR/a6 model" % n
        assert ring_words(final) == ring_words(x), "context %d: bank changed" % n
        seen.add(target); naive_ok += int(naive == target[0])
    assert len(seen) == 8, "not all sigma combinations exercised"
    assert naive_ok < n, "naive single-cell readout matched sigma_1 everywhere: control not discriminating"

@cocotb.test()
async def t14_local_write_toggles_one_parity(dut):
    rng = random.Random(1017)
    for ring_idx in (0, 2, 6):   # uno por ciclo (anillos {0,2,39}, {5,11,83}, {29,31,68}) y {13,42,71}, que no alimenta ninguno
        r = RINGS[ring_idx]
        x = context(rng, (0, 0, 0))
        old = tuple(int(c in x) for c in r)
        feed = [c for c in r if any(c in f for f in FEEDS)]
        new = next(w for w in WORDS[1:] if w != old and (not feed or w[r.index(feed[0])] != old[r.index(feed[0])]))
        await reset(dut); await set_mode(dut, XOR); await scan_load(dut, x)
        prog = []
        if any(old): prog += [r[old.index(0)], None]
        prog += [r[new.index(0)], None]
        for s in prog:
            if s is None: await run(dut, 1)
            else: await stim(dut, s)
            x = model_step(x, s=s)
        assert await read_all(dut) == x, "ring %s: state after local write differs from model" % r
        assert tuple(int(c in x) for c in r) == new, "ring %s: word not written" % r
        expected = sigmas(x)
        D, _, xm = await observe(dut, x, False)
        assert D == expected, "ring %s: D=%s expected %s" % (r, D, expected)
        changed = [i for i in range(3) if expected[i] != 0]
        assert changed == ([] if not feed else [next(i for i, f in enumerate(FEEDS) if feed[0] in f)]), "ring %s: wrong parity changed %s" % (r, changed)

# --- Protocolo de 11 bits: conmutación XOR/a6, 6 sondas, T = 12 ---
P11 = json.loads((Path(__file__).parent / "bank_protocol.json").read_text())
P11_MODE = {"0": XOR, "1": XOR_A6}

async def p11_run(dut, x, seq):
    """Carga x con el modo del paso 0 ya fijado; en el paso t escribe el modo del paso t+1 (ese flanco evoluciona con el del paso t)."""
    T = P11["T"]; probes = P11["sondas"]; reads = []
    await reset(dut); await set_mode(dut, P11_MODE[seq[0]]); await scan_load(dut, x)
    assert await read_all(dut) == x, "scan load"
    xm = set(x)
    for t in range(T):
        reads.append(await probe(dut, probes))
        if t < T - 1:
            await set_mode(dut, P11_MODE[seq[(t + 1) % len(seq)]])
            xm = hd_step(xm, a6=(seq[t % len(seq)] == "1"))
    return reads, xm

def p11_check(reads, x):
    return [sum(reads[t][p] for t, p in e["lecturas"]) % 2 == sum(int(c in x) for c in e["celdas_banco"]) % 2 for e in P11["ecuaciones"]]

@cocotb.test()
async def t15_bank_11_bits_switching(dut):
    rng = random.Random(1018); fails_negative = 0
    for n in range(16):
        x = context(rng, tuple(rng.randint(0, 1) for _ in range(3)), ring2_words=RING2_P11_OK)
        reads, xm = await p11_run(dut, x, P11["secuencia"])
        ok = p11_check(reads, x)
        assert all(ok), "context %d: equations failed %s" % (n, [i for i, v in enumerate(ok) if not v])
        final = await read_all(dut)
        assert final == xm, "context %d: final state differs from the XOR/a6 model" % n
        assert ring_words(final) == ring_words(x), "context %d: bank changed" % n
        if n < 8:   # control negativo: la misma lectura con XOR fijo no debe satisfacer todas las ecuaciones
            reads0, _ = await p11_run(dut, x, "0")
            fails_negative += int(not all(p11_check(reads0, x)))
    assert fails_negative > 0, "negative control (fixed XOR) satisfied every equation: test not discriminating"

# --- Selector geométrico: receptoras del anillo {13, 42, 71} ---
HD_RING = (13, 42, 71)
HD_REC1 = {15: (13, 42, 20), 44: (42, 71, 49), 73: (71, 13, 78)}    # receptora: (m, d, u) — anillo {13,42,71}
HD_RING2 = (1, 8, 27); HD_REC2 = {22: (8, 27, 24)}                   # anillo {1,8,27}
HD_REC = {**HD_REC1, **HD_REC2}

def hd_step(x, a6=False):
    """Un paso XOR del modelo con las receptoras modificadas (15, 44, 73 y 22): y = d ^ (~m & u). a6 no toca las receptoras."""
    y = model_xor(x, 1, a6=a6)
    for r, (m, d, u) in HD_REC.items():
        y.discard(r)
        if (d in x) ^ ((m not in x) and (u in x)): y.add(r)
    return y

@cocotb.test()
async def t16_ring1_selector(dut):
    rng = random.Random(1019); seen = set(); base_wrong = 0; n = 0
    for w in WORDS:                                   # palabras pares del anillo (13, 42, 71)
        for us in [tuple((k >> j) & 1 for j in range(3)) for k in range(8)]:
            x = {i for i in range(N) if rng.random() < 0.5}
            x -= set(HD_RING); x |= {c for c, b in zip(HD_RING, w) if b}
            for (r, (m, d, u)), b in zip(HD_REC1.items(), us):
                x.discard(u)
                if b: x.add(u)
            await reset(dut); await set_mode(dut, XOR); await scan_load(dut, x)
            assert await read_all(dut) == x, "scan load"
            await run(dut, 1)
            got = await probe(dut, list(HD_REC1))
            for r, (m, d, u) in HD_REC1.items():
                exp = int((d in x) ^ ((m not in x) and (u in x)))
                assert got[r] == exp, "word %s u=%s receiver %d: got %d expected %d" % (w, us, r, got[r], exp)
                func = {(0, 0): "id", (0, 1): "not", (1, 0): "cero", (1, 1): "uno"}[(int(m in x), int(d in x))]
                seen.add((r, func, int(u in x)))
                base_wrong += int(got[r] != int((d in x) ^ (u in x)))
            xm = hd_step(x)
            await run(dut, 39)
            for _ in range(39): xm = hd_step(xm)
            final = await read_all(dut)
            assert {c: c in final for c in HD_RING} == {c: c in x for c in HD_RING}, "ring changed"
            assert final == xm, "state after 40 steps differs from the receiver model"
            n += 1
    assert len(seen) == 3 * 4 * 2, "not every receiver saw every function with u=0 and u=1: %d" % len(seen)
    assert base_wrong > 0, "negative control: the plain-XOR model never mispredicts, test not discriminating"

@cocotb.test()
async def t17_rings_zero_is_plain_xor(dut):
    """Modo compatible: con los dos anillos de programa en 000, el chip sigue exactamente el XOR sin receptoras (con y sin a6)."""
    rng = random.Random(1020)
    for a6 in (False, True):
        for _ in range(6):
            x = {i for i in range(N) if rng.random() < 0.5} - set(HD_RING) - set(HD_RING2)     # P2: los dos anillos en 000
            await reset(dut); await set_mode(dut, XOR_A6 if a6 else XOR); await scan_load(dut, x)
            await run(dut, 50)
            assert await read_all(dut) == model_xor(x, 50, a6=a6), "both rings at 000 but evolution differs from the plain XOR model"

# --- Segundo anillo de programa {1, 8, 27}, receptora 22 ---
def hatuno_step(x, a6=False):
    """Modelo con un solo anillo de programa ({13,42,71}): referencia para t18–t20."""
    y = model_xor(x, 1, a6=a6)
    for r, (m, d, u) in HD_REC1.items():
        y.discard(r)
        if (d in x) ^ ((m not in x) and (u in x)): y.add(r)
    return y

@cocotb.test()
async def t18_ring2_zero_is_hatuno(dut):
    """Con el anillo 2 en 000 y el anillo 1 en cualquier palabra par, el chip sigue exactamente al modelo de un anillo (a6 apagado y encendido)."""
    rng = random.Random(1021)
    for a6 in (False, True):
        for w1 in WORDS:
            x = {i for i in range(N) if rng.random() < 0.5} - set(HD_RING2) - set(HD_RING)
            x |= {c for c, b in zip(HD_RING, w1) if b}
            await reset(dut); await set_mode(dut, XOR_A6 if a6 else XOR); await scan_load(dut, x)
            await run(dut, 40)
            xm = set(x)
            for _ in range(40): xm = hatuno_step(xm, a6=a6)
            assert await read_all(dut) == xm, "ring 2 at 000, ring 1 %s, a6=%s: differs from the one-ring model" % (w1, a6)

@cocotb.test()
async def t19_sixteen_joint_programs(dut):
    """P1: 16 programas conjuntos (palabra1 x palabra2), u de la receptora 22 en 0 y 1, a6 alternando: función de 21 en un paso,
    40 pasos contra el modelo y las dos memorias intactas. Control negativo: el modelo de un anillo (sin la receptora 22) falla alguna vez."""
    rng = random.Random(1022); seen = set(); hatuno_wrong = 0; n = 0
    for w1 in WORDS:
        for w2 in WORDS:
            for u in (0, 1):
                a6 = n % 2 == 1; n += 1
                x = {i for i in range(N) if rng.random() < 0.5} - set(HD_RING) - set(HD_RING2)
                x |= {c for c, b in zip(HD_RING, w1) if b} | {c for c, b in zip(HD_RING2, w2) if b}
                x.discard(24)
                if u: x.add(24)
                await reset(dut); await set_mode(dut, XOR_A6 if a6 else XOR); await scan_load(dut, x)
                assert await read_all(dut) == x, "scan load"
                await run(dut, 1)
                got = (await probe(dut, [22]))[22]
                exp = int((27 in x) ^ ((8 not in x) and (24 in x)))
                assert got == exp, "w1 %s w2 %s u %d: receiver 22 got %d expected %d" % (w1, w2, u, got, exp)
                seen.add(({(0, 0): "id", (0, 1): "not", (1, 0): "cero", (1, 1): "uno"}[(int(8 in x), int(27 in x))], u))
                xm = hd_step(x, a6=a6); xh = hatuno_step(x, a6=a6)
                await run(dut, 39)
                for _ in range(39): xm = hd_step(xm, a6=a6); xh = hatuno_step(xh, a6=a6)
                final = await read_all(dut)
                assert all((c in final) == (c in x) for c in HD_RING + HD_RING2), "w1 %s w2 %s: a program ring changed" % (w1, w2)
                assert final == xm, "w1 %s w2 %s u %d a6 %s: state after 40 steps differs from the model" % (w1, w2, u, a6)
                hatuno_wrong += int(final != xh)
    assert len(seen) == 8, "receiver 22 did not see every function with u=0 and u=1: %s" % sorted(seen)
    assert hatuno_wrong > 0, "negative control: the one-ring model never mispredicts, ring 2 not exercised"

@cocotb.test()
async def t20_ring2_keeps_bank(dut):
    """Con el anillo {1,8,27}, D = sigma en las cuatro palabras del anillo 2 (a6 fijo y alternando). Control: el modelo de un anillo
    (sin la receptora 22) mispredice el estado final en algún contexto, así que el anillo 2 sí actúa."""
    rng = random.Random(1023); n = 0; hatuno_wrong = 0
    for w2 in WORDS:
        for k in range(4):
            target = tuple(((k + n) >> j) & 1 for j in range(3)); alternate = k % 2 == 1; n += 1
            x = context(rng, target, ring2_words=[w2])
            await reset(dut); await set_mode(dut, XOR); await scan_load(dut, x)
            D, _, xm = await observe(dut, x, alternate)
            final = await read_all(dut)
            assert final == xm, "ring 2 %s: state differs from the model" % (w2,)
            assert D == target, "ring 2 %s: D=%s expected %s" % (w2, D, target)
            assert ring_words(final) == ring_words(x), "ring 2 %s: bank changed" % (w2,)
            xh = set(x)
            for a6s in ([False, False, True, False, True] if alternate else [False] * 5): xh = hatuno_step(xh, a6=a6s)   # a6 por flanco en observe()
            hatuno_wrong += int(final != xh)
    assert hatuno_wrong > 0, "negative control: one-ring model never mispredicts, ring 2 not exercised"

@cocotb.test()
async def t21_ring2_mode_costs_p11(dut):
    """Con q[8] = 1 (palabras 011 y 110 del anillo 2) el protocolo de 11 bits pierde ecuaciones (alguna de 3, 5–10 falla en algún
    contexto) mientras las de sigma (0, 1, 2) y la 4 siguen valiendo; el estado final coincide con el modelo y el banco no cambia."""
    rng = random.Random(1024); failed = set()
    for n in range(12):
        x = context(rng, tuple(rng.randint(0, 1) for _ in range(3)), ring2_words=[(0, 1, 1), (1, 1, 0)])
        reads, xm = await p11_run(dut, x, P11["secuencia"])
        ok = p11_check(reads, x)
        assert ok[0] and ok[1] and ok[2] and ok[4], "context %d: a robust equation failed %s" % (n, ok)
        failed |= {i for i, v in enumerate(ok) if not v}
        final = await read_all(dut)
        assert final == xm, "context %d: final state differs from the model" % n
        assert ring_words(final) == ring_words(x), "context %d: bank changed" % n
    assert failed and failed <= {3, 5, 6, 7, 8, 9, 10}, "q8=1 did not cost the expected equations: %s" % sorted(failed)

# --- Demostración diferencial ---
async def probe_run(dut, x, a6, T):
    """Carga x, lee las 6 sondas en t = 0..T-1 (un flanco entre lecturas); devuelve lecturas y estado final."""
    await reset(dut); await set_mode(dut, XOR_A6 if a6 else XOR); await scan_load(dut, x)
    reads = []
    for k in range(T):
        rd = await probe(dut, P11["sondas"]); reads.append(tuple(rd[p] for p in P11["sondas"]))
        if k < T - 1: await run(dut, 1)
    return reads, await read_all(dut)

@cocotb.test()
async def t22_differential_ring2(dut):
    """Mismo anillo 1, a6 y entradas x_a, x_b = x_a ^ e24 (banco de datos en 0); cambia solo la palabra del anillo A. Δ = resp(x_a) ^ resp(x_b)
    en 12 pasos: igual dentro de q8 = 0 y dentro de q8 = 1, distinto entre ambos; anillos intactos; Δ coincide con el modelo."""
    rng = random.Random(1026); T = 12
    data = [c for r in RINGS if r not in ([13, 42, 71], [1, 8, 27]) for c in r]
    for w1, a6 in [((0, 0, 0), False), ((0, 1, 1), True), ((1, 1, 0), False)]:
        xa = {i for i in range(N) if rng.random() < 0.5} - set(range(87, N)) - set(data) - set(HD_RING) - set(HD_RING2)
        xb = xa ^ {24}
        delta = {}
        for wa in WORDS:
            prog = {c for c, b in zip(HD_RING, w1) if b} | {c for c, b in zip(HD_RING2, wa) if b}
            ra, fa = await probe_run(dut, xa | prog, a6, T); rb, fb = await probe_run(dut, xb | prog, a6, T)
            for f in (fa, fb): assert all((c in f) == (c in prog) for c in HD_RING + HD_RING2), "a program ring changed"
            delta[wa] = [tuple(p ^ q for p, q in zip(u, v)) for u, v in zip(ra, rb)]
            ma, mb = xa | prog, xb | prog; dm = []
            for _ in range(T):
                dm.append(tuple(int(p in ma) ^ int(p in mb) for p in P11["sondas"])); ma = hd_step(ma, a6=a6); mb = hd_step(mb, a6=a6)
            assert delta[wa] == dm, "w1 %s a6 %s wa %s: delta differs from the model" % (w1, a6, wa)
        assert delta[(0, 0, 0)] == delta[(1, 0, 1)] and delta[(0, 1, 1)] == delta[(1, 1, 0)], "w1 %s: same q8, different delta" % (w1,)
        assert delta[(0, 0, 0)] != delta[(0, 1, 1)], "w1 %s a6 %s: q8 did not change the processing in %d steps" % (w1, a6, T)

# --- Decodificador adaptado por contexto ---
DEC_A = json.loads((Path(__file__).parent / "decoder.json").read_text())

@cocotb.test()
async def t23_adapted_decoder(dut):
    """Los 16 contextos de programa (anillo 1 x anillo A), 2 estados al azar cada uno (banco de datos y exterior al azar): el decodificador
    del contexto recupera sus 7 funcionales del banco con las lecturas reales del protocolo (101110, T = 12, 6 sondas)."""
    rng = random.Random(1028); n = 0
    for key, dec in DEC_A["contextos"].items():
        w1, wa = [tuple(map(int, s)) for s in key.split("|")]
        assert len(dec) == 7, "context %s: %d functionals" % (key, len(dec))
        for _ in range(2):
            x = {i for i in range(87) if rng.random() < 0.5}
            for r in RINGS:
                w = w1 if r == [13, 42, 71] else (wa if r == [1, 8, 27] else rng.choice(WORDS))
                x -= set(r); x |= {c for c, b in zip(r, w) if b}
            reads, xm = await p11_run(dut, x, DEC_A["secuencia"])
            for e in dec:
                got = (sum(reads[t][p] for t, p in e["lecturas"]) + e["constante"]) % 2
                exp = sum(c in x for c in e["celdas_banco"]) % 2
                assert got == exp, "context %s: functional %s decoded %d expected %d" % (key, e["celdas_banco"], got, exp)
            assert await read_all(dut) == xm, "context %s: final state differs from the model" % key
            n += 1
    assert n == 32

# --- Programa de placa (docs/board_program.md; datos en test/board_program.json) ---
PLACA_A = json.loads((Path(__file__).parent / "board_program.json").read_text())

@cocotb.test()
async def t24_board_program_A(dut):
    """Reproduce el programa de placa exacto: 4 corridas (x_a, x_b) x (anillo A 000, 011), anillo 1 = 011, a6 = 0, banco fijo. Fase 1: 12 lecturas
    en XOR; fase 2: protocolo 101110 y los 7 funcionales del decodificador del contexto; final: anillos intactos. Todo contra los valores del JSON."""
    for c in PLACA_A["corridas"]:
        x0 = set(c["carga"])
        reads, fin1 = await probe_run(dut, x0, False, 12)
        assert [list(r) for r in reads] == c["fase1_lecturas"], "fase 1 %s %s" % (c["anillo_A"], c["entrada"])
        reads2, xm = await p11_run(dut, x0, DEC_A["secuencia"])
        assert [[reads2[t][p] for p in PLACA_A["sondas"]] for t in range(len(reads2))] == c["fase2_lecturas"], "fase 2 %s %s" % (c["anillo_A"], c["entrada"])
        for e in c["funcionales"]:
            dec = next(d for d in DEC_A["contextos"]["%s|%s" % ("".join(map(str, PLACA_A["anillo1"])), "".join(map(str, c["anillo_A"])))] if d["celdas_banco"] == e["celdas_banco"])
            assert (sum(reads2[t][p] for t, p in dec["lecturas"]) + dec["constante"]) % 2 == e["valor"], "funcional %s" % e["celdas_banco"]
        fin = await read_all(dut)
        assert sorted(fin) == c["final_fase2"], "estado final %s %s" % (c["anillo_A"], c["entrada"])
        assert all((q in fin) == (q in x0) for q in HD_RING + HD_RING2), "a program ring changed"
    d = PLACA_A["delta_fase1"]
    assert d["000"] != d["011"], "the board program does not separate q8 = 0 from q8 = 1"
