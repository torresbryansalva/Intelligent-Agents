import heapq
import itertools # para el contador unico
from anastruct import SystemElements



# CATALOGO AISC  (Unidades: cm2, kg/m, cm4)
# Formato: {"nombre": str, "area_cm2": float, "peso_kgm": float, "inercia_cm4": float}
CATALOGO = [
    {"nombre": "W10X12", "area": 22.84, "peso": 17.86, "inercia": 2239.32},
    {"nombre": "W10X19", "area": 36.26, "peso": 28.27, "inercia": 4008.31},
    {"nombre": "W12X26", "area": 49.35, "peso": 38.69, "inercia": 8491.11},
    {"nombre": "W14X30", "area": 57.10, "peso": 44.64, "inercia": 12112.32},
    {"nombre": "W10X30", "area": 57.03, "peso": 44.64, "inercia": 7075.93},
    {"nombre": "W16X31", "area": 58.84, "peso": 46.13, "inercia": 15608.66},
    {"nombre": "W18X35", "area": 66.45, "peso": 52.09, "inercia": 21227.78},
    {"nombre": "W10X45", "area": 85.81, "peso": 66.97, "inercia": 10322.53},
    {"nombre": "W12X50", "area": 94.19, "peso": 74.41, "inercia": 16274.63},
    {"nombre": "W16X57", "area": 108.39, "peso": 84.83, "inercia": 31550.31},
    {"nombre": "W14X61", "area": 115.48, "peso": 90.78, "inercia": 26638.78},
    {"nombre": "W18X71", "area": 134.19, "peso": 105.66, "inercia": 48699.03},
    {"nombre": "W12X72", "area": 136.13, "peso": 107.15, "inercia": 24849.00},
    {"nombre": "W14X90", "area": 500.97, "peso": 500.76, "inercia": 15441581.48}
]

# Ordenar por peso - lo heuristico sea eficiente
CATALOGO = sorted(CATALOGO, key=lambda x: x['peso'])

# ─── Factores de conversión ───────────────────────────────────────────────────
# anastruct usa kN y metros internamente.
# E acero = 200 GPa = 2.0e8 kN/m²
# Inercia catálogo en cm⁴  →  m⁴ : multiplicar por 1e-8
# EI [kN·m²] = 2.0e8 [kN/m²] * I[cm⁴] * 1e-8 [m⁴/cm⁴]
#            = 2.0 * I[cm⁴]
E_KNM2 = 2.0e8          # kN/m²  (200 GPa)
CM4_A_M4 = 1e-8         # factor cm⁴ → m⁴

def ei(perfil):
    return E_KNM2 * perfil['inercia'] * CM4_A_M4   # kN·m²

class AStarEstructural:
    def __init__(self, carga_knm, longitud_viga, altura_columna, grupos):
        """
        carga_knm   : carga distribuida en kN/m (negativa = hacia abajo)
        longitud_viga / altura_columna : en METROS
        """

        self.carga = carga_knm
        self.L = longitud_viga
        self.H = altura_columna
        self.grupos = grupos # hay que tener un orden de asignacion
        self.counter = itertools.count() # genera numeros unicos
    
    def analizar_estructura(self, asignaciones):
        ss = SystemElements()

        p1 = next(p for p in CATALOGO if p['nombre'] == asignaciones['columna_1'])
        pT = next(p for p in CATALOGO if p['nombre'] == asignaciones['travesanio'])
        p2 = next(p for p in CATALOGO if p['nombre'] == asignaciones['columna_2'])

        # Geometría en metros, EI en kN·m²
        ss.add_element(location=[[0, 0],        [0, self.H]],         EI=ei(p1))
        ss.add_element(location=[[0, self.H],   [self.L, self.H]],    EI=ei(pT))
        ss.add_element(location=[[self.L, self.H], [self.L, 0]],      EI=ei(p2))

        ss.add_support_fixed(node_id=1)
        ss.add_support_fixed(node_id=4)
        ss.q_load(element_id=2, q=self.carga)   # kN/m

        ss.solve()

        displacements = ss.get_node_displacements()
        disp_max = max(
            max(abs(d['ux']), abs(d['uy'])) for d in displacements
        )

        limite = self.L / 360
        #print(f"  [check] {asignaciones} | δ_max={disp_max*100:.4f} cm | límite={limite*100:.4f} cm → {'OK' if disp_max <= limite else 'FALLA'}")
        return disp_max <= limite

    def optimizar(self):
        # Prioridad QUEUE 
        # Estructura: (f, count, nivel, asignaciones, g)
        open_set = [] # este es el monton
        heapq.heappush(open_set, (0, next(self.counter), 0, {}, 0)) # push: poner un item en el monto

        while open_set:
            f, _,  nivel, asignaciones, g = heapq.heappop(open_set) # pop: saca item mas pequeño del monton

            # CASO OBJETIVO O LA META: todos los grupos tienen perfil asignado
            if nivel == len(self.grupos):
                return asignaciones, g
            
            grupo_actual = self.grupos[nivel]
            longitud_grupo = self.L if 'travesanio' in grupo_actual else self.H

            for perfil in CATALOGO:
                temp_asign = asignaciones.copy()
                temp_asign[grupo_actual] = perfil['nombre']

                # solo validar con anaStruct si ya completmos el arco para este nodo
                es_valido = True # memoria simple
                if nivel == len(self.grupos) -1:
                    es_valido = self.analizar_estructura(temp_asign)
                
                if es_valido:
                    nuevo_g = g + perfil['peso'] * longitud_grupo
                    # Heuristica: peso restante asumiendo el perfil mas liviano <= es es nuestro objetivo y aporte
                    h = sum(
                        CATALOGO[0]['peso'] * (self.L if 'travesanio' in self.grupos[n] else self.H)
                        for n in range(nivel + 1, len(self.grupos))
                    )

                    heapq.heappush(open_set, (nuevo_g + h, next(self.counter), nivel + 1, temp_asign, nuevo_g))
        
        return None, 0 # Eres salao no encontro ningun perfil

# EJECUCION
grupos = ['columna_1', 'travesanio', 'columna_2']

portico = AStarEstructural(
    carga_knm=-70,          # kN/m  (≈ 7.14 tf/m, carga pesada para L=2 m)
    longitud_viga=2.0,      # m
    altura_columna=2.0,     # m
    grupos=grupos
)

disenio, peso_total = portico.optimizar()

print("\n--- Resultado de la Optimización A* ---")
if disenio:
    print(f"Configuración Óptima : {disenio}")
    print(f"Peso Total Encontrado: {peso_total:.2f} kg")
else:
    print("No se encontró solución válida. Considera ampliar el catálogo o revisar la carga.")

# COMO CORRER EN TERMINAL
# python agents/a_star_structural.py