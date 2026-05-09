"""
simulacion_3d.py
================

Simulacion de una estructura de acero 3D de 3 niveles usando perfiles AISC.

La estructura tiene 4 columnas por nivel, 4 vigas perimetrales por nivel
y 4 diagonales de arriostramiento por entrepiso (una en cada cara lateral).
La base del nivel 0 esta empotrada al suelo. La carga objetivo de 1 tonelada
se distribuye uniformemente entre los 3 niveles.

Cada elemento esta etiquetado con un identificador unico que codifica su
tipo, su nivel/entrepiso y su posicion (esquina o cara). Esto permite ver
de un vistazo a que grupo y posicion pertenece cada barra.

Convencion de ejes y posiciones (planta vista desde arriba):

        D ----------- C        Y                                 
        |             |        ^                              N
        |             |        |                              |
        |             |        +--> X                    W <------> E
        A ----------- B                                       | 
                                                              S

    Esquinas: A=(0,0)  B=(Lx,0)  C=(Lx,Ly)  D=(0,Ly)
    Caras   : S=sur(y=0)  N=norte(y=Ly)  W=oeste(x=0)  E=este(x=Lx)

Etiquetas:
    Nodos     : N_L{nivel}_{esquina}            ej. N_L0_A (suelo, esquina A)
    Columnas  : COL_E{entrepiso}_{esquina}      ej. COL_E1_A (entrepiso 1, esq A)
    Vigas X   : VX_L{nivel}_{lado}              ej. VX_L2_S (nivel 2, lado sur)
    Vigas Y   : VY_L{nivel}_{lado}              ej. VY_L3_E (nivel 3, lado este)
    Diagonales: DIAG_E{entrepiso}_{cara}        ej. DIAG_E1_S (entrepiso 1, cara sur)

"""
# ESQUINAS = ["A", "B", "C", "D"]

import math
import pandas as pd
from dataclasses import dataclass


# =============================================================================
# DEMANDAS Y VERIFICACIONES BASICAS AISC
# =============================================================================

def cargas_por_nivel(cfg: dict) -> dict:
    """
    Distribuye la carga total entre los niveles y calcula la axial acumulada
    por columna en cada entrepiso

    Asume que peso total kg se reparte uniformente entre num_niveles 
    y dentro de cada nivel se reparte por igual entre las 4 esquinas.
    la columna del entrepiso 1(la mas cargada) acumulade todos los niveles
    superiores, la del entrepiso 3 (la mas arriba) solo carga el ultimo nivel

    Args:
        cfg: configuracion con peso total_kg y num_niveles
    
    Return:
    {P_total_kN, P_por_nivel_kN, P_por_nodo_kN y
        P_axial_columna_kN (lista indexada por entrepiso-1)}
    """
    g = 9.80665                                     # gravedad
    P_total = cfg["peso_total_kg"] * g / 1000.0     # kN
    n = cfg["num_niveles"]
    c_n = cfg["contactos_nivel"]
    P_nivel = P_total / n
    P_nodo = P_nivel / c_n
    P_axial = [( n - ( e - 1)) * P_nivel / 4.0 for e in range(1, n+1)]
    return {
        "P_total_kN" :          P_total,
        "P_por_nivel_kN":       P_nivel,
        "P_por_nodo_kN":        P_nodo,
        "P_axial_columna_kN":   P_axial,
    }


def propiedades(df: pd.DataFrame, nombre: str) -> dict:
    """
    Devuelve las propiedades clave de un perfil del catalogo en SI (m, kg).

    Args:
        df: DataFrame del catalogo (indice = nombre del perfil).
        nombre: designacion AISC (ej. 'W6X15').

    Returns:
        dict con: peso_kgm, area_m2, Ix_m4, Iy_m4, Sx_m3, Zx_m3, rx_m,
        ry_m, J_m4, bf_m, tf_m, d_m, tw_m.

    Raises:
        KeyError si el perfil no existe en el catalogo.
    """
    if nombre not in df.index:
        raise KeyError(f"Perfil '{nombre}' no existe en el catalogo")
    f = df.loc[nombre]
    return {
        "peso_kgm": float(f["peso_kgm"]),
        "area_m2":  float(f["area_m2"]),
        "Ix_m4":    float(f["Ix_m4"]),
        "Iy_m4":    float(f["Iy_m4"]),
        "Sx_m3":    float(f["Sx_m3"]),
        "Zx_m3":    float(f["Zx_m3"]),
        "rx_m":     float(f["rx_m"]),
        "ry_m":     float(f["ry_m"]),
        "J_m4":     float(f["J_m4"]),
        "bf_m":     float(f["bf_m"]),
        "tf_m":     float(f["tf_m"]),
        "d_m":      float(f["d_m"]),
        "tw_m":     float(f["tw_m"]),
    }




def verificar_viga(prop: dict, M_kNm: float, V_kN: float, Fy_MPa: float) -> dict:
    """
    Verifica una viga a flexion (Cap. F) y corte (Cap. G) segun AISC 360-22.

    Asume seccion compacta y arriostramiento lateral suficiente (sin LTB).
    Para luces pequenas (L <= 4 m) con perfiles W ligeros suele ser razonable;
    para luces mayores conviene aplicar las formulas F2-1 a F2-3 con Lb.

    Args:
        prop: propiedades del perfil.
        M_kNm: momento ultimo requerido.
        V_kN: corte ultimo requerido.
        Fy_MPa: tension de fluencia.

    Returns:
        dict con phi_Mn_kNm, phi_Vn_kN, ratio_M, ratio_V, ok.
    """
    Fy = Fy_MPa * 1000.0
    phi_Mn = 0.9 * Fy * prop["Zx_m3"]
    phi_Vn = 1.0 * 0.6 * Fy * prop["d_m"] * prop["tw_m"]
    rM = M_kNm / phi_Mn if phi_Mn > 0 else float("inf")
    rV = V_kN  / phi_Vn if phi_Vn > 0 else float("inf")
    return {
        "phi_Mn_kNm": phi_Mn,
        "phi_Vn_kN":  phi_Vn,
        "ratio_M":    rM,
        "ratio_V":    rV,
        "ok":         (rM <= 1.0) and (rV <= 1.0),
    }

def verificar_columna(prop: dict, P_kN: float, L_m: float,
                      Fy_MPa: float, E_MPa: float, K: float = 1.0) -> dict:
    """
    Verifica capacidad axial de una columna segun AISC 360-22 Cap. E (DAM, K=1.0).

    Aplica las formulas E3-2/E3-3 segun KL/r vs el limite 4.71*sqrt(E/Fy).
    No considera flexion ni interaccion P-M (verificacion simplificada).

    Args:
        prop: propiedades del perfil (de propiedades()).
        P_kN: carga axial requerida.
        L_m: longitud de la columna.
        Fy_MPa, E_MPa: material.
        K: factor de longitud efectiva (1.0 bajo DAM).

    Returns:
        dict con KL_r, F_e_MPa, F_cr_MPa, phi_Pn_kN, ratio (Pu/phiPn), ok.
    """
    Fy = Fy_MPa * 1000.0   # kN/m^2
    E  = E_MPa  * 1000.0
    KL_r = K * L_m / prop["ry_m"]
    F_e = math.pi**2 * E / KL_r**2
    limite = 4.71 * math.sqrt(E / Fy)
    if KL_r <= limite:
        F_cr = (0.658 ** (Fy / F_e)) * Fy
    else:
        F_cr = 0.877 * F_e
    phi_Pn = 0.9 * F_cr * prop["area_m2"]
    ratio = P_kN / phi_Pn if phi_Pn > 0 else float("inf")
    return {
        "KL_r":      KL_r,
        "F_e_MPa":   F_e / 1000.0,
        "F_cr_MPa":  F_cr / 1000.0,
        "phi_Pn_kN": phi_Pn,
        "ratio":     ratio,
        "ok":        ratio <= 1.0,
    }


def verificar_diagonal(prop: dict, F_kN: float, L_m: float,
                       Fy_MPa: float, E_MPa: float) -> dict:
    """
    Verifica una diagonal a traccion (Cap. D) y compresion (Cap. E) segun AISC.

    Como la fuerza axial puede invertir signo bajo viento alterno, se evalua
    contra la menor de las dos capacidades (la de compresion suele gobernar
    por pandeo).

    Args:
        prop: propiedades del perfil.
        F_kN: fuerza axial requerida (signo ignorado, se evalua valor absoluto).
        L_m: longitud de la diagonal.
        Fy_MPa, E_MPa: material.

    Returns:
        dict con phi_Tn_kN, phi_Pn_kN, KL_r, ratio (max), ok.
    """
    Fy = Fy_MPa * 1000.0
    E  = E_MPa  * 1000.0
    phi_Tn = 0.9 * Fy * prop["area_m2"]
    KL_r = 1.0 * L_m / prop["ry_m"]
    F_e = math.pi**2 * E / KL_r**2
    limite = 4.71 * math.sqrt(E / Fy)
    F_cr = (0.658 ** (Fy / F_e)) * Fy if KL_r <= limite else 0.877 * F_e
    phi_Pn = 0.9 * F_cr * prop["area_m2"]
    F = abs(F_kN)
    rT = F / phi_Tn if phi_Tn > 0 else float("inf")
    rC = F / phi_Pn if phi_Pn > 0 else float("inf")
    return {
        "phi_Tn_kN": phi_Tn,
        "phi_Pn_kN": phi_Pn,
        "KL_r":      KL_r,
        "ratio":     max(rT, rC),
        "ok":        max(rT, rC) <= 1.0,
    }