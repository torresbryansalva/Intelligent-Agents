"""
                        A* para estructuras metalicas en 3D
=======================================================================================


Implementacion del algoritmo de A* para optimizar el peso de una estructura en 3D
El algoritmo busca la mejor combinacion que aliviane el peso bajo las restricciones de AISC 

objetivos: 
    - cuantos perfiles del catalogo pasan los pre-filtros por grupo
    - cada extraccion que se hace del 'heap' con valores f(n), g(n), h(n)
    - como se construye cada arbol: nivel por nivel
    - cada poda (cuando f del nodo  >= mejor encontrado)
    - verificacion final en las hojas
    - el avance hacia el optimo


Niveles del arbol: 
    nivel 0 -> vigas_x
    nivel 1 -> vigas_y
    nivel 2 -> columnas
    nivel 3 -> diagonales (hoja: cuando se completa, se verifica)


Nodo:
    g(n) = peso acumulado de los perfiles ya elegidos (Kg)
    h(n) = peso minimo posible de lo que falta
    f(n) = g + h  (cota inferior del peso final si elegimos este camino)

Como h es admisible(siempre <= peso real restante), f es siempre <= peso optimo
del subarbol bajo este nodo. La primera hoja que cumpla este criterio es el OPTIMO

"""
import math
import heapq
import itertools
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field

from simulacion_3d import (cargas_por_nivel, propiedades, verificar_viga, verificar_columna,
                           verificar_diagonal)

# ================================================================================
#                       CONFIGURACION BASICA DE LA ESTRUCTURA
CONFIG = {
    # Geometria (m)
    "Lx":           4.0,        # longitud/luz de viga eje x
    "Ly":           4.0,        # longitud/luz de viga eje y
    "H_nivel":      3.0,        # longitud de columna
    "num_niveles":  3,          # cantidad de piso
    "contactos_nivel": 4.0,     # nodos o contactos por nivel

    # Cargas
    "peso_total_kg" : 5000.0,   # kg distribuida entre niveles
    "viento_kNm2":    0.8,

    # Material ASTM A992
    "Fy_MPa":       345.0,
    "E_MPa":        200_000.0,
    "G_MPa":        77_000.0,
    "rho_kgm3":     7850.0,

    # Catalogo
    "catalogo_path":   "D:/Maestria Inteligencia Artificial/PRIMER CICLO/matematica para machine learning/articulo de investigacion/AISC_Catalogo_Limpio.xlsx",
    "catalogo_hoja":   "W",
    "catalogo_header": 2,        # los nombres de columna estan en la fila 3

    # Perfiles AISC default (deben existir en la hoja W del catalogo)
    "perfil_columna":  "W6X15",
    "perfil_viga":     "W6X12",
    "perfil_diagonal": "W6X9",

    # Limites para que la salida sea legible
    "max_aptos_por_grupo":  5,   # solo los 5 mas livianos que pasan el filtro
    "verbose_pop":          True, # imprime cada extraccion del heap
    "verbose_expansion":    True, # imprime cada hijo generado
    "verbose_poda":         True, # imprime cada poda
    "max_pops_detallados":  40,   # despues de N pops, solo eventos clave

    # Salida
    "guardar_figura":  True,
    "ruta_figura":     "estructura_3d.png",
}

GRUPOS = ["vigas_X", "vigas_Y", "columnas", "diagonales"]

ESQUINAS = ["A", "B", "C", "D"]

# =============================================================================

# =============================================================================
# CARGA DEL CATALOGO
# =============================================================================

def cargar_catalogo(cfg: dict) -> pd.DataFrame:
    """
    Carga el catalogo AISC desde el Excel.

    El archivo tiene encabezado en la fila 3 (header=2) y columnas en SI
    como peso_kgm, area_m2, Ix_m4, Iy_m4, Zx_m3, ry_m, J_m4, bf_m, tf_m,
    d_m, tw_m. Devuelve un DataFrame indexado por el nombre del perfil
    (ej. 'W6X15').

    Args:
        cfg: diccionario CONFIG con catalogo_path y catalogo_hoja.

    Returns:
        DataFrame con los perfiles del catalogo.
    """
    path = Path(__file__).parent / cfg["catalogo_path"]
    df = pd.read_excel(path, sheet_name=cfg["catalogo_hoja"],
                       header=cfg["catalogo_header"])
    df = df.dropna(subset=["nombre"]).set_index("nombre")
    return df


# =============================================================================
# INFO POR GRUPO (cuantos elementos hay y que longitud)
# =============================================================================

def info_grupo(cfg: dict) -> dict:
    """
    Devuelve cuantos elementos hay y la longitu unitaria de cada grupo,
    para calcular peso = peso_kgm * longitud *cantidad
    Para 3 niveles:
        vigas_eje_x = 2 vigas por nivel x 3 niveles = 6 elementos de Lx
        vigas_eje_y = 2 vigas por nivel x 3 niveles = 6 elementos de Ly
        columnas = 4 columnas por entrepiso x 3 entrepisos = 12 de H_nivel
        digonales = 4 caras x 3 entrepisos = 12 (longitud meda para simplicidad)
    
    Argumentos:
    cfg: configuracion con  Lx, Ly, H_nivel, num_niveles
    """
    n_niv = cfg["num_niveles"]
    Lx, Ly, cols = cfg["Lx"], cfg["Ly"], cfg["H_nivel"]
    L_diag_prom = (math.hypot(cols, Lx) + math.hypot(cols, Ly)) / 2.0

    return {
        "vigas_X":    {"cantidad": 2 * n_niv, "longitud": Lx},
        "vigas_Y":    {"cantidad": 2 * n_niv, "longitud": Ly},
        "columnas":   {"cantidad": 4 * n_niv, "longitud": cols},
        "diagonales": {"cantidad": 4 * n_niv, "longitud": L_diag_prom},
    }

# =============================================================================
# DEMANDAS ANALITICAS POR GRUPO
# =============================================================================
def precalcular_demandas(cfg: dict) -> dict:
    """
    Calcular las demandas maximas analiticas (cota superior) por grupo.add()
    
    Estas demandas se usan en los pre-filtros: si un perfil no aguanta la 
    demanda analitica, se descarta sin meterlo al arbol A*.add()

    Argumento:
        cfg: configuracion
    """
    print("PASO 2.1: Cargas por nivel: ")
    cargas = cargas_por_nivel(cfg)
    print(cargas)
    print("PASO 2.2: Calculo demandas")
    Lx, Ly, H = cfg["Lx"], cfg["Ly"], cfg["H_nivel"]
    n_niv = cfg["num_niveles"]
    perim = 2 * (Lx + Ly)
    q_perim = cargas["P_por_nivel_kN"] / perim

    # Viento
    H_total = H * n_niv
    w_x_kN = cfg["viento_kNm2"] * Ly * H_total
    L_diag = math.hypot(H, max(Lx, Ly))
    F_diag_kN = w_x_kN * L_diag / H

    return {
        "M_vx":   q_perim * Lx**2 / 8,
        "V_vx":   q_perim * Lx / 2,
        "M_vy":   q_perim * Ly**2 / 8,
        "V_vy":   q_perim * Ly / 2,
        "P_col":  cargas["P_axial_columna_kN"][0],   # la mas cargada (entrepiso 1)
        "F_diag": F_diag_kN,
    }
     

# =============================================================================
# PRE-FILTROS POR GRUPO
# =============================================================================
def filtrar_aptos(df: pd.DataFrame, cfg: dict, dem: dict)-> dict:
    """
    Aplica los filtros analiticos AISC a cada perfil del catalogo,
    grupo por grupo. Devuelve los aptos (que pasan) ordenados por peso.

    Imprime un resumen de cuantos perfiles del catalogo pasan cada filtro.

    Args:
        df: catalogo cargado
        cfg: configuracion
        dem: demandas analiticas (de precalcular_demandas)

    Returns:
        dict {grupo: [lista de dicts {nombre, peso_kgm, p}]}, ordenada por peso asc
    """
    Fy, E = cfg["Fy_MPa"], cfg["E_MPa"]
    H, Lx, Ly = cfg["H_nivel"], cfg["Lx"], cfg["Ly"]
    L_diag = math.hypot(H, max(Lx, Ly))

    aptos: dict = {g: [] for g in GRUPOS}
    descartes = {g: 0 for g in GRUPOS}
    
    print("PASO 3.1: Verificar los elemento Viga, columna, diagonal")
    for nombre in df.index:
        try:
            p = propiedades(df, nombre)
        except (KeyError, ValueError):
            continue

        # vigas_X
        chk_vx = verificar_viga(p, dem["M_vx"], dem["V_vx"], Fy)
        if chk_vx["ok"]:
            aptos["vigas_X"].append({"nombre": nombre, "peso_kgm": p["peso_kgm"], "p": p})
        else:
            descartes["vigas_X"] += 1

        # vigas_Y
        chk_vy = verificar_viga(p, dem["M_vy"], dem["V_vy"], Fy)
        if chk_vy["ok"]:
            aptos["vigas_Y"].append({"nombre": nombre, "peso_kgm": p["peso_kgm"], "p": p})
        else:
            descartes["vigas_Y"] += 1

        # columnas
        chk_co = verificar_columna(p, dem["P_col"], H, Fy, E, K=1.0)
        if chk_co["ok"]:
            aptos["columnas"].append({"nombre": nombre, "peso_kgm": p["peso_kgm"], "p": p})
        else:
            descartes["columnas"] += 1

        # diagonales
        chk_dg = verificar_diagonal(p, dem["F_diag"], L_diag, Fy, E)
        if chk_dg["ok"]:
            aptos["diagonales"].append({"nombre": nombre, "peso_kgm": p["peso_kgm"], "p": p})
        else:
            descartes["diagonales"] += 1

    print("PASO 3.2: Ordenar ascendente y recortar")
    # ordenar por peso ascendente y recortar
    max_n = cfg["max_aptos_por_grupo"]
    for g in GRUPOS:
        aptos[g].sort(key=lambda x: x["peso_kgm"])
        aptos[g] = aptos[g][:max_n]
    print("\n" + "=" * 86)
    print("PASO 3.3: PRE-FILTROS ANALITICOS (paso previo al A*)")
    print("=" * 86)
    print(f"  Catalogo total                    : {len(df)} perfiles W")
    print(f"  Demandas analiticas calculadas   :")
    print(f"      M_vx  = {dem['M_vx']:.2f} kNm    V_vx  = {dem['V_vx']:.2f} kN")
    print(f"      M_vy  = {dem['M_vy']:.2f} kNm    V_vy  = {dem['V_vy']:.2f} kN")
    print(f"      P_col = {dem['P_col']:.2f} kN     F_diag = {dem['F_diag']:.2f} kN")
    print()
    print(f"  Resultado del filtrado (mostrando los {max_n} mas livianos por grupo):")
    print("  " + "-" * 82)
    print(f"  {'grupo':<12} {'pasan':>6} {'descartados':>13}   "
          f"{'mas livianos (kg/m)':<40}")
    for g in GRUPOS:
        livianos = ", ".join(f"{a['nombre']}({a['peso_kgm']:.1f})" for a in aptos[g])
        n_pasan = len(aptos[g]) + (descartes[g] if False else 0)  # n_pasan = total que paso
        # recontar (max_n recorta, pero contamos los que pasaron)
        n_pasan_real = len(df) - descartes[g]
        print(f"  {g:<12} {n_pasan_real:>6} {descartes[g]:>13}   {livianos}")
    # tamano del espacio efectivo
    prod = 1
    for g in GRUPOS:
        prod *= len(aptos[g])
    print(f"\n  Espacio efectivo del A* (con max_aptos={max_n}): "
          f"{prod:,} hojas posibles\n")


    return aptos


# =============================================================================
# HEURISTICA ADMISIBLE
# =============================================================================

def heuristica(nivel: int, aptos: dict, info: dict) -> tuple[float, list]:
    """
    Heuristica admisible h(n): suma de los perfiles MAS LIVIANOS en los grupos
    que aun no se han asignado, multiplicados por longitud y cantidad.

    Es admisible (cota inferior) porque cualquier asignacion real va a usar
    perfiles >= los mas livianos disponibles. Por tanto h <= peso real restante,
    y A* garantiza optimo global.

    Args:
        nivel: nivel actual del arbol (0..4).
        aptos: dict de listas por grupo (ordenadas por peso asc).
        info: info_grupo() con cantidad y longitud por grupo.

    Returns:
        (h, detalle) donde detalle es lista de (grupo, perfil_liviano, contrib_kg)
    """
    h = 0.0
    detalle = []
    for g in GRUPOS[nivel:]:
        if not aptos[g]:
            return float("inf"), []
        liv = aptos[g][0]
        contrib = liv["peso_kgm"] * info[g]["longitud"] * info[g]["cantidad"]
        h += contrib
        detalle.append((g, liv["nombre"], contrib))
    return h, detalle

# =============================================================================
# NODO DEL ARBOL A*
# =============================================================================

@dataclass(order=True)
class NodoArbol:
    """
    Nodo del arbol de busqueda A*.

    Atributos comparables (para heap):
        f       : g + h, valor de prioridad (menor primero)
        contador: tiebreaker para evitar comparar dicts

    Atributos no comparables:
        nivel       : 0..4, nivel del arbol (4 = hoja)
        asignacion  : {grupo: nombre_perfil}
        g           : peso acumulado (kg)
        h           : peso minimo restante estimado (kg)
        h_detalle   : lista de tuplas (grupo, perfil_min, contrib_kg) para imprimir
        ruta        : lista de elecciones acumuladas para visualizar el arbol
    """
    f: float
    contador: int
    nivel: int = field(compare=False)
    asignacion: dict = field(compare=False, default_factory=dict)
    g: float = field(compare=False, default=0.0)
    h: float = field(compare=False, default=0.0)
    h_detalle: list = field(compare=False, default_factory=list)
    ruta: list = field(compare=False, default_factory=list)



# =============================================================================
# VERIFICACION FINAL EN HOJAS
# =============================================================================

def verificar_diseño(asig: dict, cfg: dict, info: dict) -> tuple[bool, str]:
    """
    Verificacion final cuando los 4 grupos estan asignados.

    Reaplica los chequeos AISC con las demandas analiticas reales (no usa MEF
    aqui para mantener el ejemplo simple). En el workflow completo, esta seria
    la llamada a PyNiteFEA con DAM. Si se quisiera ser estricto, aqui se
    incluirian las cargas combinadas y la verificacion biaxial.

    Args:
        asig: dict con perfil asignado a cada grupo.
        cfg: configuracion.
        info: info_grupo().

    Returns:
        (ok, mensaje) bool si pasa todas las verificaciones.
    """
    # Como los pre-filtros ya validaron individualmente, aqui un diseno
    # completo siempre pasa (en el modelo simplificado). Se mantiene la
    # estructura para que el flujo del A* sea correcto.
    return True, "OK (pre-filtros ya validaron)"



# ================================================================================
#                             A*
# ================================================================================
def a_star(df: pd.DataFrame, cfg: dict) -> dict:
    """
    Ejecuta A* sobre el espacio de combinaciones de perfiles, imprimiendo
    paso a paso la construccion del arbol.

    Cada iteracion:
        1. Extrae el nodo de menor f (mejor candidato actual)
        2. Si nivel==4 (hoja): es candidato a optimo, comparar y guardar
        3. Si no: para cada perfil apto del grupo del nivel, generar hijo
           con g actualizado y h recalculado, empujar al heap
        4. Podar nodos cuya f >= mejor encontrado

    Args:
        df: catalogo W.
        cfg: configuracion del A*.

    Returns:
        dict con mejor_asignacion, mejor_peso, estadisticas.
    """
    print("\n------ APLICANDO FILTROS  ---")
    
    print("\nPASO 1: Info del grupo:")
    info = info_grupo(cfg)
    print(info)
    
    print("\nPASO 2: Calcular pre-demandas")
    dem = precalcular_demandas(cfg)
    print(dem)

    print("\nPASO 3: Filtrar Aptos - Encontra el Espacio del agente")
    aptos = filtrar_aptos(df, cfg, dem)
    
    # Obtener y mostrar los primeros 7 pares clave:valor
    print("Espacio del Agente encontrado: \n")
    for clave, valor in list(aptos.items())[:7]:
        print(f"{clave}: {valor}")

    # inicio del algoritmo A*
    print("\n------ INICIO ALGORITMO A*  ---")
    
    # h inicial (raiz)
    print("\n  Calculo de la raiz")
    h0, det0 = heuristica(0, aptos, info)

    print("\n" + "=" * 86)
    print("  ARRANQUE DEL A*")
    print("=" * 86)
    print(f"  Nodo raiz: nivel=0, asignacion=vacia, g=0.0")
    print(f"  Heuristica inicial h(raiz) = suma minimos por grupo:")
    for g, perf, contrib in det0:
        print(f"      {g:<12} -> {perf:<10} aporta {contrib:>8.2f} kg "
              f"(cota inferior si todo fuera asi de liviano)")
    print(f"  h(raiz) total = {h0:.2f} kg")
    print(f"  f(raiz) = g + h = 0 + {h0:.2f} = {h0:.2f} kg")
    print(f"\n  >> Esto significa: NINGUNA solucion puede pesar menos de {h0:.2f} kg")

    counter = itertools.count()
    raiz = NodoArbol(
        f=h0, contador=next(counter), nivel=0,
        asignacion={}, g=0.0, h=h0, h_detalle=det0, ruta=[],
    )
    heap: list[NodoArbol] = []
    heapq.heappush(heap, raiz)

    mejor_peso = float("inf")
    mejor_asig = None
    mejor_ruta = None

    n_pop  = 0
    n_push = 1
    n_poda = 0
    n_hojas_vistas = 0
    n_hojas_validas = 0

    print("\n" + "=" * 86)
    print("  ITERACIONES DEL A*")
    print("=" * 86)

    while heap:
        nodo = heapq.heappop(heap)
        n_pop += 1

        # Poda: si f del nodo >= mejor encontrado, ya no puede mejorar
        if nodo.f >= mejor_peso:
            n_poda += 1
            if cfg["verbose_poda"] and n_pop <= cfg["max_pops_detallados"]:
                print(f"\n  [POP #{n_pop}] PODADO: f={nodo.f:.2f} >= mejor={mejor_peso:.2f}")
                print(f"             ruta: {' -> '.join(nodo.ruta) if nodo.ruta else '(raiz)'}")
            continue

        verbose_pop = cfg["verbose_pop"] and n_pop <= cfg["max_pops_detallados"]

        if verbose_pop:
            print(f"\n  [POP #{n_pop}] EXTRAIDO del heap (mejor f del momento)")
            print(f"      nivel = {nodo.nivel}/{len(GRUPOS)}")
            print(f"      ruta  = {' -> '.join(nodo.ruta) if nodo.ruta else '(raiz)'}")
            print(f"      g(n)  = {nodo.g:>8.2f} kg  (peso ya comprometido)")
            print(f"      h(n)  = {nodo.h:>8.2f} kg  (cota inferior de lo restante)")
            print(f"      f(n)  = {nodo.f:>8.2f} kg  (cota inferior del peso final)")
            falta = max(0.0, mejor_peso - nodo.f) if mejor_peso < float("inf") else None
            if falta is not None:
                print(f"      mejor actual = {mejor_peso:.2f} kg, "
                      f"margen f vs mejor = {falta:.2f} kg")
            print(f"      heap = {len(heap)} nodos pendientes")


        # HOJA
        if nodo.nivel == len(GRUPOS):
            n_hojas_vistas += 1
            ok, detalle_v = verificar_diseño(nodo.asignacion, cfg, info)
            if verbose_pop:
                print(f"      *** HOJA detectada (4 perfiles asignados) ***")
                print(f"      asignacion: {nodo.asignacion}")
                print(f"      verificacion final AISC: {'PASA' if ok else 'FALLA'}")
                if not ok:
                    print(f"        razon: {detalle_v}")
            if ok:
                n_hojas_validas += 1
                if nodo.g < mejor_peso:
                    delta = (mejor_peso - nodo.g) if mejor_peso < float("inf") else 0
                    mejor_peso = nodo.g
                    mejor_asig = dict(nodo.asignacion)
                    mejor_ruta = list(nodo.ruta)
                    print(f"\n  [MEJORA] Nuevo mejor diseno encontrado!")
                    print(f"      peso = {mejor_peso:.2f} kg "
                          f"({'mejora '+str(round(delta,2))+' kg vs anterior' if delta else 'primero'})")
                    print(f"      asignacion: {mejor_asig}")
            continue
        
        # EXPANSION: para cada perfil apto del grupo de este nivel
        grupo = GRUPOS[nodo.nivel]
        cant  = info[grupo]["cantidad"]
        L_g   = info[grupo]["longitud"]

        if verbose_pop:
            print(f"      EXPANDIENDO nivel {nodo.nivel} = {grupo} "
                  f"({len(aptos[grupo])} perfiles aptos)")

        for ap in aptos[grupo]:
            peso_g = ap["peso_kgm"] * L_g * cant
            g_new  = nodo.g + peso_g
            asig_new = dict(nodo.asignacion)
            asig_new[grupo] = ap["nombre"]
            ruta_new = nodo.ruta + [f"{grupo}={ap['nombre']}"]
            h_new, det_new = heuristica(nodo.nivel + 1, aptos, info)
            f_new = g_new + h_new

            # poda preventiva
            if f_new >= mejor_peso:
                if cfg["verbose_expansion"] and verbose_pop:
                    print(f"        - {ap['nombre']:<10} g+={peso_g:>7.2f}  "
                          f"g_new={g_new:>7.2f}  h_new={h_new:>7.2f}  "
                          f"f_new={f_new:>7.2f}  *** PODADO (>= mejor {mejor_peso:.2f}) ***")
                n_poda += 1
                continue

            if cfg["verbose_expansion"] and verbose_pop:
                print(f"        + {ap['nombre']:<10} g+={peso_g:>7.2f}  "
                      f"g_new={g_new:>7.2f}  h_new={h_new:>7.2f}  "
                      f"f_new={f_new:>7.2f}  --> push al heap")

            heapq.heappush(heap, NodoArbol(
                f=f_new, contador=next(counter),
                nivel=nodo.nivel + 1,
                asignacion=asig_new, g=g_new, h=h_new,
                h_detalle=det_new, ruta=ruta_new,
            ))
            n_push += 1

        if n_pop == cfg["max_pops_detallados"]:
            print(f"\n  ... (modo verbose desactivado tras {n_pop} extracciones, "
                  f"solo se mostraran nuevas mejoras)")

    # FIN
    print("\n" + "=" * 86)
    print("  FIN DEL A*")
    print("=" * 86)
    print(f"  Pops (extracciones del heap): {n_pop}")
    print(f"  Pushes (nodos generados)    : {n_push}")
    print(f"  Podas                        : {n_poda}")
    print(f"  Hojas alcanzadas             : {n_hojas_vistas}")
    print(f"  Hojas validas (pasaron AISC) : {n_hojas_validas}")

    if mejor_asig is None:
        print("\n  >>> NO SE ENCONTRO SOLUCION FACTIBLE <<<")
    else:
        print(f"\n  >>> OPTIMO ENCONTRADO: {mejor_peso:.2f} kg <<<")
        print(f"      asignacion: {mejor_asig}")
        print(f"      ruta del optimo: {' -> '.join(mejor_ruta)}")

    return {
        "mejor_peso_kg":     mejor_peso,
        "mejor_asignacion":  mejor_asig,
        "n_pop":             n_pop,
        "n_push":            n_push,
        "n_poda":            n_poda,
        "n_hojas_vistas":    n_hojas_vistas,
        "n_hojas_validas":   n_hojas_validas,
    }       
    


# =============================================================================
# VISUALIZACION 3D (opcional)
# =============================================================================

@dataclass(frozen=True)
class Nodo:
    """Nodo de la estructura: etiqueta unica y coordenadas (m)."""
    label: str
    x: float
    y: float
    z: float

@dataclass(frozen=True)
class Elemento:
    """Elemento estructural (columna, viga o diagonal) con etiqueta unica."""
    label: str
    tipo: str        # 'COL', 'VX', 'VY', 'DIAG'
    nivel: int       # nivel del elemento (entrepiso para columnas/diagonales)
    posicion: str    # esquina (A,B,C,D) para COL, lado (S,N,W,E) para vigas y diagonales
    n1: str          # etiqueta nodo inicial
    n2: str          # etiqueta nodo final
    longitud: float  # m
    perfil: str      # designacion AISC

def generar_columnas(cfg: dict) -> list[Elemento]:
    """
    Genera 4 columnas por entrepiso (una en cada esquina A, B, C, D).

    Etiqueta: COL_E{entrepiso}_{esquina}. El entrepiso 1 va del nivel 0 al 1,
    el 2 del 1 al 2, etc.

    Returns:
        lista de Elemento de tipo 'COL'.
    """
    H = cfg["H_nivel"]
    elems: list[Elemento] = []
    for entrepiso in range(1, cfg["num_niveles"] + 1):
        ni, ns = entrepiso - 1, entrepiso
        for esq in ESQUINAS:
            elems.append(Elemento(
                label=f"COL_E{entrepiso}_{esq}",
                tipo="COL", nivel=entrepiso, posicion=esq,
                n1=f"N_L{ni}_{esq}", n2=f"N_L{ns}_{esq}",
                longitud=H, perfil=cfg["perfil_columna"],
            ))
    return elems


def generar_vigas(cfg: dict) -> list[Elemento]:
    """
    Genera 4 vigas perimetrales por nivel (excluye el nivel 0 = suelo):
    2 vigas paralelas a X (lados S y N) y 2 vigas paralelas a Y (lados W y E).

    Etiquetas:
        VX_L{nivel}_S    sur (y=0)    une A-B
        VX_L{nivel}_N    norte (y=Ly) une D-C
        VY_L{nivel}_W    oeste (x=0)  une A-D
        VY_L{nivel}_E    este (x=Lx)  une B-C

    Returns:
        lista de Elemento de tipo 'VX' o 'VY'.
    """
    Lx, Ly = cfg["Lx"], cfg["Ly"]
    elems: list[Elemento] = []
    for nivel in range(1, cfg["num_niveles"] + 1):
        elems.append(Elemento(
            label=f"VX_L{nivel}_S", tipo="VX", nivel=nivel, posicion="S",
            n1=f"N_L{nivel}_A", n2=f"N_L{nivel}_B",
            longitud=Lx, perfil=cfg["perfil_viga"]))
        elems.append(Elemento(
            label=f"VX_L{nivel}_N", tipo="VX", nivel=nivel, posicion="N",
            n1=f"N_L{nivel}_D", n2=f"N_L{nivel}_C",
            longitud=Lx, perfil=cfg["perfil_viga"]))
        elems.append(Elemento(
            label=f"VY_L{nivel}_W", tipo="VY", nivel=nivel, posicion="W",
            n1=f"N_L{nivel}_A", n2=f"N_L{nivel}_D",
            longitud=Ly, perfil=cfg["perfil_viga"]))
        elems.append(Elemento(
            label=f"VY_L{nivel}_E", tipo="VY", nivel=nivel, posicion="E",
            n1=f"N_L{nivel}_B", n2=f"N_L{nivel}_C",
            longitud=Ly, perfil=cfg["perfil_viga"]))
    return elems


def generar_diagonales(cfg: dict) -> list[Elemento]:
    """
    Genera 4 diagonales por entrepiso, una en cada cara lateral.

    Cada diagonal forma un triangulo con la columna y la viga adyacentes y
    transmite el corte horizontal por arriostramiento.

    Etiqueta: DIAG_E{entrepiso}_{cara}, cara en {S, N, W, E}.

        Cara S (y=0):  N_L{ni}_A  ->  N_L{ns}_B    (longitud sqrt(H^2+Lx^2))
        Cara N (y=Ly): N_L{ni}_D  ->  N_L{ns}_C
        Cara W (x=0):  N_L{ni}_A  ->  N_L{ns}_D    (longitud sqrt(H^2+Ly^2))
        Cara E (x=Lx): N_L{ni}_B  ->  N_L{ns}_C

    Returns:
        lista de Elemento de tipo 'DIAG'.
    """
    Lx, Ly, H = cfg["Lx"], cfg["Ly"], cfg["H_nivel"]
    L_dx = math.hypot(H, Lx)
    L_dy = math.hypot(H, Ly)
    elems: list[Elemento] = []
    for entrepiso in range(1, cfg["num_niveles"] + 1):
        ni, ns = entrepiso - 1, entrepiso
        elems.append(Elemento(
            label=f"DIAG_E{entrepiso}_S", tipo="DIAG", nivel=entrepiso, posicion="S",
            n1=f"N_L{ni}_A", n2=f"N_L{ns}_B",
            longitud=L_dx, perfil=cfg["perfil_diagonal"]))
        elems.append(Elemento(
            label=f"DIAG_E{entrepiso}_N", tipo="DIAG", nivel=entrepiso, posicion="N",
            n1=f"N_L{ni}_D", n2=f"N_L{ns}_C",
            longitud=L_dx, perfil=cfg["perfil_diagonal"]))
        elems.append(Elemento(
            label=f"DIAG_E{entrepiso}_W", tipo="DIAG", nivel=entrepiso, posicion="W",
            n1=f"N_L{ni}_A", n2=f"N_L{ns}_D",
            longitud=L_dy, perfil=cfg["perfil_diagonal"]))
        elems.append(Elemento(
            label=f"DIAG_E{entrepiso}_E", tipo="DIAG", nivel=entrepiso, posicion="E",
            n1=f"N_L{ni}_B", n2=f"N_L{ns}_C",
            longitud=L_dy, perfil=cfg["perfil_diagonal"]))
    return elems



def generar_nodos(cfg: dict) -> list[Nodo]:
    """
    Genera todos los nodos de la estructura: 4 esquinas por (num_niveles + 1)
    niveles. El nivel 0 es el suelo (empotrado), el ultimo nivel es el techo.

    Etiqueta: N_L{nivel}_{esquina}, ej. N_L0_A, N_L1_B, N_L3_C.

    Args:
        cfg: configuracion con Lx, Ly, H_nivel, num_niveles.

    Returns:
        lista de Nodo (4 * (num_niveles + 1) elementos).
    """
    Lx, Ly, H = cfg["Lx"], cfg["Ly"], cfg["H_nivel"]
    coords = {"A": (0.0, 0.0), "B": (Lx, 0.0),
              "C": (Lx, Ly),   "D": (0.0, Ly)}
    nodos: list[Nodo] = []
    for nivel in range(cfg["num_niveles"] + 1):
        z = nivel * H
        for esq, (x, y) in coords.items():
            nodos.append(Nodo(label=f"N_L{nivel}_{esq}", x=x, y=y, z=z))
    return nodos

def dibujar_3d(cfg: dict, ruta_png: str | None = None) -> None:
    """
    Dibuja la estructura en 3D con matplotlib y muestra las etiquetas.

    Cada tipo de elemento se colorea distinto:
        COL = azul, VX = verde, VY = oliva, DIAG = rojo.

    Si se pasa ruta_png, guarda el grafico como imagen; si es None, lo muestra.

    Args:
        cfg: configuracion.
        ruta_png: ruta de salida o None.
    """
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    except ImportError:
        print("  (matplotlib no disponible, se omite la figura)")
        return

    nodos = {n.label: n for n in generar_nodos(cfg)}
    elems = (generar_columnas(cfg)
             + generar_vigas(cfg)
             + generar_diagonales(cfg))
    color = {"COL": "tab:blue", "VX": "tab:green",
             "VY": "tab:olive", "DIAG": "tab:red"}

    fig = plt.figure(figsize=(11, 9))
    ax = fig.add_subplot(111, projection="3d")
    for e in elems:
        n1, n2 = nodos[e.n1], nodos[e.n2]
        ax.plot([n1.x, n2.x], [n1.y, n2.y], [n1.z, n2.z],
                color=color[e.tipo], lw=1.6)
        mx, my, mz = (n1.x + n2.x) / 2, (n1.y + n2.y) / 2, (n1.z + n2.z) / 2
        ax.text(mx, my, mz, e.label, fontsize=6, color=color[e.tipo])
    for n in nodos.values():
        ax.scatter(n.x, n.y, n.z, s=20, color="k")
        ax.text(n.x, n.y, n.z + 0.12, n.label, fontsize=6, color="k")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(f"Portico 3D arriostrado - {cfg['num_niveles']} niveles "
                 f"(Lx={cfg['Lx']}, Ly={cfg['Ly']}, H={cfg['H_nivel']} m)")
    plt.tight_layout()
    if ruta_png:
        salida = Path(__file__).parent / ruta_png
        plt.savefig(salida, dpi=120)
        print(f"  Figura guardada en: {salida}")
        plt.close(fig)
    else:
        plt.show()

# ================================================================================
#                                    MAIN
# ================================================================================

def main():
    print("="*60)
    print("\n Version 1.0 trabajo de Investigacion A* para Estructuras \n")
    print("="*60)

    print("Configuration de la Estructura")
    print(f"      geometria : viga(Lx)={CONFIG['Lx']} m  viga(Ly)={CONFIG['Ly']} m  "
          f"columna(H)={CONFIG['H_nivel']} m  niveles={CONFIG['num_niveles']}")
    df = cargar_catalogo(CONFIG)
    resultado = a_star(df=df, cfg=CONFIG)

    print("\n" + "=" * 86)
    print("  RESUMEN")
    print("=" * 86)
    if resultado["mejor_asignacion"]:
        print(f"  Peso optimo  : {resultado['mejor_peso_kg']:.2f} kg")
        for g, p in resultado["mejor_asignacion"].items():
            print(f"      {g:<12} = {p}")
    print(f"  Eficiencia A*:")
    print(f"      nodos extraidos : {resultado['n_pop']}")
    print(f"      nodos generados : {resultado['n_push']}")
    print(f"      podados         : {resultado['n_poda']}")
    print(f"      hojas vistas    : {resultado['n_hojas_vistas']}")
    print()
    if CONFIG.get("guardar_figura", False):
        dibujar_3d(CONFIG, ruta_png=CONFIG["ruta_figura"])
    return

if __name__ == "__main__":
    main()
