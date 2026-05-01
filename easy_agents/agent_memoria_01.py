import os
import sys
import time
import numpy as np

# Agregamos la carpeta raíz (ai-search-agents) al buscador de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logging_config import obtener_logger

log = obtener_logger("AgenteMemoria")

# 1. EL ENTORNO REAL
ambiente = np.array([
    [1, 1],
    [0, 1]
])

class AgenteConMemoria:
    def __init__(self, dimensiones):

        self.mapa_mental = np.zeros(dimensiones)
        self.visitados = []

    def actualizar_memoria(self, pos, estado_sucio):

        self.mapa_mental[pos[0], pos[1]] = 1 if estado_sucio else 0
        if pos not in self.visitados:
            self.visitados.append(pos)

    def decidir_accion(self, fila, columna, estado_sucio):

        if estado_sucio:
            return "Limpiar"
        
        # REGLA DE NAVEGACIÓN: Si ya limpió aquí, consulta su memoria para 
        # decidir a dónde ir (esto evita bucles infinitos en el futuro)
        if fila == 0 and columna == 0: return "DERECHA"
        if fila == 0 and columna == 1: return "ABAJO"
        if fila == 1 and columna == 1: return "IZQUIERDA"
        if fila == 1 and columna == 0: return "ARRIBA"
        return "NADA"

# SIMULACION
agente = AgenteConMemoria(ambiente.shape)
pos_actual = [0, 0]

#print("Iniciando Agente con Memoria Interna")
log.info(" Iniciando Agente con Memoria Interna")

for paso in range(6):

    f, c = pos_actual
    sucio_real = ambiente[f, c] == 1
    
    # paso clave
    agente.actualizar_memoria((f,c), sucio_real)
    accion = agente.decidir_accion(f, c, sucio_real)
    print("AMBIENTE ACTUAL")
    print(ambiente)
    log.info(f"\n--- PASO {paso + 1} ---")
    log.info(f"Posicion: [{f},{c}] | Accion: {accion}")
    log.info(f"Celdas que recuerdo haber visitado: {agente.visitados}")

    if accion == 'Limpiar':
        ambiente[f,c] = 0
        agente.actualizar_memoria((f, c), False) #Actualiza su mapa mental

    elif accion == "DERECHA":   pos_actual = [0, 1]
    elif accion == "ABAJO":     pos_actual = [1, 1]
    elif accion == "IZQUIERDA": pos_actual = [1, 0]
    elif accion == "ARRIBA":    pos_actual = [0, 0]

    log.info(f"Mapa Mental del Agente:\n{agente.mapa_mental}")
    time.sleep(1)