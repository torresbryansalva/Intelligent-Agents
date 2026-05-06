"""
a_star_structural_v3.py
========================
Optimizador A* para pórtico plano [columna_1, travesaño, columna_2].
Lee el catálogo limpio desde AISC_Catalogo_Limpio.xlsx.

Sistema de unidades SI consistente:
  Fuerzas    → kN
  Longitudes → m
  Tensiones  → kN/m²   (1 MPa = 1 000 kN/m²)
  E acero    = 200 GPa  = 2.0×10⁸ kN/m²
  Fy A992    = 345 MPa  = 345 000 kN/m²

Verificaciones AISC 360-22 (LRFD):
  1. Deflexión   δ_max ≤ L/360              (anastruct)
  2. Compacidad  bf/2tf ≤ λp_ala            (Tabla B4.1b)
                 h/tw   ≤ λp_alma
  3. Flexión     φMn ≥ Mu                   (Cap. F, Mp = Fy·Zx)
  4. Corte       φVn ≥ Vu                   (Cap. G, G2.1)
  5. Pandeo      φPn ≥ Pu                   (Cap. E)

Uso:
    python a_star_structural_v3.py
    python a_star_structural_v3.py --carga -30 --luz 6.0 --altura 4.0 --verbose
    python a_star_structural_v3.py --Fy 250   # acero A36
"""

import argparse
import heapq
import itertools
import math
import warnings
from pathlib import Path

import pandas as pd
from anastruct import SystemElements

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTES  (todo en kN y m)
# ═══════════════════════════════════════════════════════════════════════════════

E_ACERO = 2.0e8   # kN/m²  (200 GPa)
Fy_A992 = 345e3   # kN/m²  (345 MPa — A992 Gr50)

# Factores LRFD AISC 360-22
PHI_M = 0.90   # flexión
PHI_V = 1.00   # corte (G2.1, alma sin refuerzo)
PHI_P = 0.90   # compresión axial

CATALOGO_PATH = "D:/Maestria Inteligencia Artificial/PRIMER CICLO/matematica para machine learning/articulo de investigacion/AISC_Catalogo_Limpio.xlsx"
SHEET_NAME    = "W"


# ═══════════════════════════════════════════════════════════════════════════════
#  CARGA DEL CATÁLOGO
# ═══════════════════════════════════════════════════════════════════════════════

def cargar_catalogo(path: str, sheet: str = "W") -> list[dict]:
    """
    Lee AISC_Catalogo_Limpio.xlsx (generado por limpiar_aisc.py).
    Usa columnas en unidades SI. Ordena por peso_kgm ascendente.
    """
    df = pd.read_excel(path, sheet_name=sheet, header=2, skiprows=[3])

    cols = {
        "nombre"  : "nombre",
        "peso_kgm": "peso",    # kg/m
        "area_m2" : "A",       # m²
        "d_m"     : "d",       # m
        "tw_m"    : "tw",      # m
        "Ix_m4"   : "Ix",      # m⁴
        "Zx_m3"   : "Zx",      # m³
        "rx_m"    : "rx",      # m
        "ry_m"    : "ry",      # m
        "bf_2tf"  : "bf_2tf",  # adim
        "h_tw"    : "h_tw",    # adim
    }

    sub = df[list(cols.keys())].rename(columns=cols).copy()
    for col in [c for c in sub.columns if c != "nombre"]:
        sub[col] = pd.to_numeric(sub[col], errors="coerce")

    sub = sub.dropna().sort_values("peso", ascending=True).reset_index(drop=True)
    return sub.to_dict("records")


# ═══════════════════════════════════════════════════════════════════════════════
#  VERIFICACIONES AISC 360-22
# ═══════════════════════════════════════════════════════════════════════════════

class Verificador:
    """Checks estructurales en unidades SI puras (kN, m, kN/m²)."""

    def __init__(self, Fy: float = Fy_A992, E: float = E_ACERO):
        self.Fy = Fy   # kN/m²
        self.E  = E    # kN/m²
        # Pre-calcular ratio √(E/Fy) — adimensional, igual con cualquier unidad coherente
        self._sqr = math.sqrt(E / Fy)

    # ── 1. Compacidad — Tabla B4.1b ────────────────────────────────────────
    def check_compacidad(self, p: dict) -> tuple[bool, str]:
        lp_ala  = 0.38 * self._sqr    # ≈ 9.15  para A992
        lp_alma = 3.76 * self._sqr    # ≈ 90.6  para A992
        ok_ala  = p["bf_2tf"] <= lp_ala
        ok_alma = p["h_tw"]   <= lp_alma
        msg = (f"bf/2tf={p['bf_2tf']:.2f}≤{lp_ala:.2f}({'✓' if ok_ala else '✗'})  "
               f"h/tw={p['h_tw']:.2f}≤{lp_alma:.2f}({'✓' if ok_alma else '✗'})")
        return ok_ala and ok_alma, msg

    # ── 2. Flexión — Cap. F (sección compacta) ─────────────────────────────
    def check_flexion(self, p: dict, Mu: float) -> tuple[bool, str]:
        """
        Mp   = Fy · Zx   [kN/m² × m³ = kN·m]
        φMn  = 0.90 · Mp
        """
        phi_Mn = PHI_M * self.Fy * p["Zx"]
        ok     = phi_Mn >= abs(Mu)
        msg    = f"φMn={phi_Mn:.1f}≥Mu={abs(Mu):.1f} kN·m ({'✓' if ok else '✗'})"
        return ok, msg

    # ── 3. Corte — Sec. G2.1 ───────────────────────────────────────────────
    def check_corte(self, p: dict, Vu: float) -> tuple[bool, str]:
        """
        Cv1  = 1.0  si h/tw ≤ 2.24·√(E/Fy)
        Aw   = d · tw  [m²]
        φVn  = 1.0 · 0.6·Fy·Aw·Cv1  [kN]
        """
        Cv1    = 1.0 if p["h_tw"] <= 2.24 * self._sqr else 0.9
        phi_Vn = PHI_V * 0.6 * self.Fy * (p["d"] * p["tw"]) * Cv1
        ok     = phi_Vn >= abs(Vu)
        msg    = f"φVn={phi_Vn:.1f}≥Vu={abs(Vu):.1f} kN ({'✓' if ok else '✗'})"
        return ok, msg

    # ── 4. Pandeo — Cap. E ─────────────────────────────────────────────────
    def check_pandeo(self, p: dict, Pu: float,
                     L_col: float, K: float = 0.65) -> tuple[bool, str]:
        """
        K = 0.65  (empotrado-empotrado, pórtico rígido)
        λ   = KL / r_min
        Fe  = π²·E / λ²   [kN/m²]
        Fcr calculado según AISC E3
        φPn = 0.90·Fcr·A   [kN]
        """
        r_min = min(p["rx"], p["ry"])
        lam   = K * L_col / r_min
        lim   = 4.71 * self._sqr                      # ≈ 113 para A992
        Fe    = (math.pi**2 * self.E) / lam**2
        Fcr   = ((0.658 ** (self.Fy / Fe)) * self.Fy
                 if lam <= lim else 0.877 * Fe)
        phi_Pn = PHI_P * Fcr * p["A"]
        ok     = phi_Pn >= abs(Pu)
        msg    = (f"KL/r={lam:.1f}  "
                  f"φPn={phi_Pn:.1f}≥Pu={abs(Pu):.1f} kN ({'✓' if ok else '✗'})")
        return ok, msg


# ═══════════════════════════════════════════════════════════════════════════════
#  ANÁLISIS CON ANASTRUCT
# ═══════════════════════════════════════════════════════════════════════════════

def analizar_estructura(asign: dict, carga: float, L: float, H: float,
                        idx_cat: dict) -> dict | None:
    """Modela, resuelve y extrae esfuerzos del pórtico."""
    p1 = idx_cat[asign["columna_1"]]
    pT = idx_cat[asign["travesano"]]
    p2 = idx_cat[asign["columna_2"]]

    try:
        ss = SystemElements()
        ss.add_element([[0, 0], [0, H]], EI=E_ACERO * p1["Ix"])
        ss.add_element([[0, H], [L, H]], EI=E_ACERO * pT["Ix"])
        ss.add_element([[L, H], [L, 0]], EI=E_ACERO * p2["Ix"])
        ss.add_support_fixed(node_id=1)
        ss.add_support_fixed(node_id=4)
        ss.q_load(element_id=2, q=carga)
        ss.solve()

        disps    = ss.get_node_displacements()
        disp_max = max(max(abs(d["ux"]), abs(d["uy"])) for d in disps)

        r1 = ss.get_element_results(element_id=1)
        rT = ss.get_element_results(element_id=2)
        r2 = ss.get_element_results(element_id=3)

        return {
            "disp_max": disp_max,
            "Mu_viga" : max(abs(rT["Mmin"]), abs(rT["Mmax"])),
            "Vu_viga" : max(abs(rT["Qmin"]), abs(rT["Qmax"])),
            "Pu_col1" : max(abs(r1["Nmin"]), abs(r1["Nmax"])),
            "Pu_col2" : max(abs(r2["Nmin"]), abs(r2["Nmax"])),
            "Mu_col"  : max(abs(r1["Mmin"]), abs(r1["Mmax"]),
                            abs(r2["Mmin"]), abs(r2["Mmax"])),
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  VERIFICACIÓN COMPLETA DE UN DISEÑO
# ═══════════════════════════════════════════════════════════════════════════════

def verificar_diseno(asign: dict, res: dict, L: float, H: float,
                     idx_cat: dict, v: Verificador,
                     verbose: bool = False) -> bool:

    p1 = idx_cat[asign["columna_1"]]
    pT = idx_cat[asign["travesano"]]
    p2 = idx_cat[asign["columna_2"]]

    checks: list[tuple[bool, str]] = []

    # 1. Deflexión
    lim = L / 360
    ok  = res["disp_max"] <= lim
    checks.append((ok, f"Deflexión  δ={res['disp_max']*100:.3f}≤{lim*100:.3f} cm"))

    # 2. Compacidad
    for tag, p in [("col1", p1), ("viga", pT), ("col2", p2)]:
        ok, msg = v.check_compacidad(p)
        checks.append((ok, f"Compact [{tag}] {msg}"))

    # 3. Flexión
    ok, msg = v.check_flexion(pT, res["Mu_viga"])
    checks.append((ok, f"Flexión [viga] {msg}"))
    for tag, p in [("col1", p1), ("col2", p2)]:
        ok, msg = v.check_flexion(p, res["Mu_col"])
        checks.append((ok, f"Flexión [{tag}] {msg}"))

    # 4. Corte
    ok, msg = v.check_corte(pT, res["Vu_viga"])
    checks.append((ok, f"Corte   [viga] {msg}"))

    # 5. Pandeo
    for tag, p, Pu in [("col1", p1, res["Pu_col1"]),
                        ("col2", p2, res["Pu_col2"])]:
        ok, msg = v.check_pandeo(p, Pu, H)
        checks.append((ok, f"Pandeo  [{tag}] {msg}"))

    todas_ok = all(c[0] for c in checks)

    if verbose and not todas_ok:
        print(f"    ✗ {asign['columna_1']}|{asign['travesano']}|{asign['columna_2']}")
        for ok, msg in checks:
            if not ok:
                print(f"        ✗ {msg}")

    return todas_ok


# ═══════════════════════════════════════════════════════════════════════════════
#  OPTIMIZADOR A*
# ═══════════════════════════════════════════════════════════════════════════════

class AStarEstructuralV3:
    """Minimiza peso total [kg] con verificaciones AISC 360-22 completas."""

    GRUPOS = ["columna_1", "travesano", "columna_2"]

    def __init__(self, carga: float, luz: float, altura: float,
                 catalogo: list[dict], Fy: float = Fy_A992):
        self.carga   = carga
        self.L       = luz
        self.H       = altura
        self.CAT     = catalogo
        self.verif   = Verificador(Fy=Fy)
        self.counter = itertools.count()
        self._idx    = {p["nombre"]: p for p in catalogo}
        self._long   = {"columna_1": altura, "travesano": luz, "columna_2": altura}

        # Pre-filtro estático: solo perfiles compactos entran al A*
        self._aptos = [p for p in self.CAT if self.verif.check_compacidad(p)[0]]
        print(f"  Pre-filtro compacidad: {len(self._aptos)}/{len(self.CAT)} perfiles aptos")
        self._w_min = self._aptos[0]["peso"]

    def _heuristica(self, nivel: int) -> float:
        return sum(self._w_min * self._long[self.GRUPOS[n]]
                   for n in range(nivel, len(self.GRUPOS)))

    def optimizar(self, verbose: bool = False) -> tuple[dict | None, float]:
        heap: list = []
        heapq.heappush(heap, (0.0, next(self.counter), 0, {}, 0.0))

        nodos = 0
        eval_completos = 0

        while heap:
            f, _, nivel, asign, g = heapq.heappop(heap)
            nodos += 1

            if nivel == len(self.GRUPOS):
                print(f"  Nodos expandidos  : {nodos:,}")
                print(f"  Diseños evaluados : {eval_completos:,}")
                return asign, g

            grupo   = self.GRUPOS[nivel]
            es_last = (nivel == len(self.GRUPOS) - 1)

            for p in self._aptos:
                temp = {**asign, grupo: p["nombre"]}

                if es_last:
                    eval_completos += 1
                    res = analizar_estructura(temp, self.carga, self.L,
                                              self.H, self._idx)
                    if res is None:
                        continue
                    if not verificar_diseno(temp, res, self.L, self.H,
                                            self._idx, self.verif, verbose):
                        continue

                nuevo_g = g + p["peso"] * self._long[grupo]
                heapq.heappush(heap,
                    (nuevo_g + self._heuristica(nivel + 1),
                     next(self.counter), nivel + 1, temp, nuevo_g))

        print(f"  Nodos expandidos  : {nodos:,}")
        print(f"  Diseños evaluados : {eval_completos:,}")
        return None, 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTE
# ═══════════════════════════════════════════════════════════════════════════════

def imprimir_reporte(asign: dict, peso: float, carga: float,
                     L: float, H: float, cat: list[dict], v: Verificador):
    sep = "═" * 65
    idx = {p["nombre"]: p for p in cat}
    longs = {"columna_1": H, "travesano": L, "columna_2": H}

    print(f"\n{sep}")
    print(f"  DISEÑO ÓPTIMO — A* Estructural v3  (AISC 360-22)")
    print(sep)
    print(f"  Geometría : L={L} m  │  H={H} m")
    print(f"  Carga     : q={carga} kN/m")
    print(f"  Material  : Fy={v.Fy/1e3:.0f} MPa  │  E={v.E/1e6:.0f} GPa")
    print(sep)
    print(f"  {'Grupo':<14}  {'Perfil':<12}  {'kg/m':>8}  {'L(m)':>6}  {'Subtotal':>10}")
    print(f"  {'─'*56}")
    for grupo, nombre in asign.items():
        p = idx[nombre]
        sub = p["peso"] * longs[grupo]
        print(f"  {grupo:<14}  {nombre:<12}  {p['peso']:>8.2f}  {longs[grupo]:>6.1f}  {sub:>10.2f}")
    print(f"  {'─'*56}")
    print(f"  {'PESO TOTAL':<36}  {peso:>10.2f} kg")
    print(sep)

    res = analizar_estructura(asign, carga, L, H, idx)
    if not res:
        return

    print(f"\n  VERIFICACIONES DETALLADAS:\n")
    p1 = idx[asign["columna_1"]]
    pT = idx[asign["travesano"]]
    p2 = idx[asign["columna_2"]]

    rows: list[tuple[bool, str, str]] = []

    lim = L / 360
    ok  = res["disp_max"] <= lim
    rows.append((ok, "Deflexión", f"δ={res['disp_max']*100:.3f} cm ≤ L/360={lim*100:.3f} cm"))

    for tag, p in [("col1", p1), ("viga", pT), ("col2", p2)]:
        ok, msg = v.check_compacidad(p)
        rows.append((ok, f"Compacidad [{tag}]", msg))

    ok, msg = v.check_flexion(pT, res["Mu_viga"])
    rows.append((ok, "Flexión [viga]", msg))
    for tag, p in [("col1", p1), ("col2", p2)]:
        ok, msg = v.check_flexion(p, res["Mu_col"])
        rows.append((ok, f"Flexión [{tag}]", msg))

    ok, msg = v.check_corte(pT, res["Vu_viga"])
    rows.append((ok, "Corte [viga]", msg))

    for tag, p, Pu in [("col1", p1, res["Pu_col1"]), ("col2", p2, res["Pu_col2"])]:
        ok, msg = v.check_pandeo(p, Pu, H)
        rows.append((ok, f"Pandeo [{tag}]", msg))

    for ok, cat_str, msg in rows:
        marca = "✓" if ok else "✗"
        print(f"  {marca} {cat_str:<20} {msg}")

    print(f"\n{sep}\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="A* Estructural v3 — AISC 360-22")
    parser.add_argument("--carga",    type=float, default=-30.0,
                        help="Carga distribuida kN/m (neg=↓). Default: -30")
    parser.add_argument("--luz",      type=float, default=5.0,
                        help="Longitud travesaño m. Default: 5.0")
    parser.add_argument("--altura",   type=float, default=4.0,
                        help="Altura columnas m. Default: 4.0")
    parser.add_argument("--Fy",       type=float, default=345.0,
                        help="Fy en MPa. Default: 345 (A992 Gr50)")
    parser.add_argument("--catalogo", type=str,   default=CATALOGO_PATH)
    parser.add_argument("--sheet",    type=str,   default=SHEET_NAME)
    parser.add_argument("--verbose",  action="store_true",
                        help="Muestra cada diseño que falla")
    args = parser.parse_args()

    Fy_kNm2 = args.Fy * 1e3   # MPa → kN/m²

    cat_path = Path(args.catalogo)
    if not cat_path.exists():
        raise FileNotFoundError(f"No encontré: {cat_path}")

    sep = "═" * 65
    print(f"\n{sep}")
    print(f"  A* ESTRUCTURAL v3  —  AISC 360-22 (LRFD, SI)")
    print(sep)

    CAT = cargar_catalogo(str(cat_path), args.sheet)
    print(f"  Catálogo : {cat_path}  [{args.sheet}] → {len(CAT)} perfiles W")
    print(f"  Geometría: L={args.luz} m  │  H={args.altura} m")
    print(f"  Carga    : q={args.carga} kN/m")
    print(f"  Material : Fy={args.Fy} MPa = {Fy_kNm2:.0f} kN/m²")
    print()

    opt    = AStarEstructuralV3(args.carga, args.luz, args.altura, CAT, Fy_kNm2)
    diseno, peso = opt.optimizar(verbose=args.verbose)

    if diseno:
        verif = Verificador(Fy=Fy_kNm2)
        imprimir_reporte(diseno, peso, args.carga, args.luz, args.altura, CAT, verif)
    else:
        print(f"\n{sep}")
        print("  ❌  Sin solución. Prueba:")
        print("      --carga -10   (reducir carga)")
        print("      --Fy 250      (acero A36)")
        print(f"{sep}\n")


if __name__ == "__main__":
    main()