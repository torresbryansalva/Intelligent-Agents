import os
import sys
import time
import numpy as np

# Agregamos la carpeta raíz (ai-search-agents) al buscador de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logging_config import obtener_logger

log = obtener_logger("AgenteNXN")

# LOGICA DEL AGENTE
class AgentEvolucionado:
    def __init__(self, filas, columnas):
        self.filas = filas
        self.columnas = columnas
        self.memoria = np.zeros((filas, columnas))
        self.direcion_h = 1  # 1 para la derecha, -1 para izquierda

    def decidir_accion(self, f, c, esta_sucio):
        if esta_sucio:
            return "LIMPIAR"
        
        # logica del movimiento en zig-zag
        
        # opcion1 : intentar moverse horizontalmente
        proxima_col = c + self.direcion_h

        if 0 <= proxima_col < self.columnas:
            return "MOVER_H" # movimiento horizontal (dercha o izquid)
        
        # opcion2 : si choca con pared lateral, intentar bajar
        if f + 1 < self.filas:
            self.direcion_h = -1*self.direcion_h #cambias la direccion
            return "BAJAR"
        
        return "TERMINAR"

# CONFIGURACION DEL MUNDO
N = 3 
ambiente = np.random.choice([0,1], size=(N, N), p=[0.4, 0.6],)
pos_actual = [0, 0] 
print("--- AMBIENTE INICIAL ---")
print(ambiente)

agente = AgentEvolucionado(N, N)
log.info(f" Iniciando limpieza en matriz {N}x{N}")

# BUCLE DINAMICO
ejecutando = True
pasos = 0

while ejecutando and pasos < 50:
    pasos += 1
    f, c = pos_actual
    sucio = ambiente[f, c] == 1

    accion = agente.decidir_accion(f, c, sucio)
    log.info(f"Paso {pasos} | Pos: [{f},{c}] | Accion: {accion}")

    if accion == "LIMPIAR":
        ambiente[f, c] = 0
        log.info(f"<> Limpiado en [{f},{c}]")

    elif accion == "MOVER_H":
        pos_actual[1] += agente.direcion_h

    elif accion == "BAJAR":
        pos_actual[0] += 1
        log.info("⬇ Bajando a la siguiente fila...")
        
    elif accion == "TERMINAR":
        log.info(" ¡Mapa completado según mi memoria!")
        ejecutando = False
    
    log.info("Estado del mundo tras este paso:")
    print(ambiente) 
    print(f"Posicion del agente: [{pos_actual[0]}, {pos_actual[1]}]")
    time.sleep(0.5)

log.info("Resultado Final:")