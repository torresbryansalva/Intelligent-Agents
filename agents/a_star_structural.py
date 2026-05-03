import heapq

# 1 CATALOGO DE PERFILES  (simplificado)
# Nombre: (Area en in2, Peso en lb/ft, Inercia en in4)
CATALOGO_AISC = [
    {"nombre": "W10X12", "area": 3.54, "peso": 12, "inercia": 53.8},
    {"nombre": "W10X30", "area": 8.84, "peso": 30, "inercia": 170.0},
    {"nombre": "W12X50", "area": 14.6, "peso": 50, "inercia": 391.0},
    {"nombre": "W14X90", "area": 26.5, "peso": 90, "inercia": 999.0}
]

# Ordenar por peso - lo heuristico sea eficiente
CATALOGO_AISC = sorted(CATALOGO_AISC, key=lambda x: x['peso'])

class AStarEstructural:
    def __init__(self, carga_kips, longitud_viga, altura_columna, grupos):
        self.carga = carga_kips
        self.L = longitud_viga
        self.H = altura_columna
        self.grupos = grupos # hay que tener un orden de asignacion
    
    def heuristica(self, nivel):
        """Estimacion optimista del peso restante"""
        elementos_finitos = len(self.grupos) - nivel
        if elementos_finitos <= 0: 
            return 0
        return elementos_finitos * CATALOGO_AISC[0]['peso'] * 15 # 15ft prom
    
    def es_factible(self, asignaciones):
        """
        Simulacion del Oraculo (AISC 360-22)
        Aqui se integra funciones para verificar esfuerzos
        """
        if "travesanio"  in asignaciones:
            perfil_v = next(p for p in CATALOGO_AISC if p['nombre'] == asignaciones['travesanio'])
            if perfil_v['inercia'] < (self.carga*10): # Simulación de chequeo de deflexión
                return False
        return True

    def optimizar(self):
        # Prioridad QUEUE (f_score, nivel_actual, asignaciones_dict, g_score)
        open_set = []
        heapq.heappush(open_set, (0 + self.heuristica(0), 0, {}, 0))
        while open_set:
            f, nivel, asignaciones, g = heapq.heappop(open_set)

            # CASO OBJETIVO O LA META: todos los grupos tienen perfil asignado
            if nivel == len(self.grupos):
                return asignaciones, g
            
            grupo_actual = self.grupos[nivel]
            for perfil in CATALOGO_AISC:
                nuevas_asignaciones = asignaciones.copy()
                nuevas_asignaciones[grupo_actual] = perfil['nombre']

                if self.es_factible(nuevas_asignaciones):
                    nuevo_g = g + (perfil['peso']) * (self.H  if grupo_actual == 'Columnas' else self.L)
                    nuevo_f = nuevo_g + self.heuristica(nivel + 1)

                    heapq.heappush(open_set, (nuevo_f, nivel+1, nuevas_asignaciones, nuevo_g))
        
        return None

# EJECUCION
grupos = ['columna_1', 'travesanio', 'columna_2']
portico = AStarEstructural(carga_kips=50, longitud_viga=30, altura_columna=15, grupos=grupos)
resultado, peso_total = portico.optimizar()

print(f"--- Resultado de la Optimización A* ---")
print(f"Configuración Óptima: {resultado}")
print(f"Peso Total Estimado: {peso_total} lbs")


# COMO CORRER EN TERMINAL
# python agents/a_star_structural.py

# que es heapq