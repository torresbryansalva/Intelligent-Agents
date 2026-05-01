import os
import sys
import time
import numpy as np
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregamos la carpeta raíz (ai-search-agents) al buscador de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logging_config import obtener_logger

log = obtener_logger("Tarea3fundamentosIA")
# 0 es para linea (No oscuro), 1 es linea(oscuro), -1 es para pared (P)
N = 5
M = 5
ambiente = np.random.choice([0, 1, -1], size=(N, M), p=[0.5, 0.4, 0.1])
f  = np.random.randint(0, N-1)
c  = np.random.randint(0, M-1)
agent_pos = [0, 0]
orientacion = 1 # Derecha
pared = False
max_pasos = 7

print("AMBIENTE ORIGAL")
print(ambiente)
# ===== LOGICA DEL ROBOT =====
def obtener_orientacion(obs):
    """
    0: arriba
    1: derecha
    2: abajo
    3: izquierda
    """
    return {0: "▲", 1: "▶", 2: "▼", 3: "◀"}[obs]

def camara1(vision):
    """
    Solo mira el piso: Oscuro
    """
    if vision:
        return "OSCURO"
    return "NO OSCURO"

def camara2(valor1, valor2, valor3):
    """
    Observa las 3 celdas delante del robot
    """
    
    valores = {0:'NO OSCURO', 1: 'OSCURO', -1:'PARED'}
    
    return {'AVANZAR CELDA IZQUIERDA': valores[valor1],
            'AVANZAR CELDA CENTRAL': valores[valor2],
            'AVANZAR CELDA DERECHA': valores[valor3]
        }

def get_valor_seguro(matrix, i, j, valor_por_defecto=-1):
    """
    Validacion de limites y pared
    """
    filas, columnas = matrix.shape
    if 0 <= i < filas and 0 <= j < columnas:
        return matrix[i,j]
    return valor_por_defecto

def posicion_celdas_delanteras(ambiente, orientacion, pos):
    i, j = pos

    # Arriba
    if orientacion == 0: 
        izq_valor = get_valor_seguro(ambiente, i-1, j-1 )
        cen_valor = get_valor_seguro(ambiente, i-1, j)
        der_valor =get_valor_seguro(ambiente, i-1, j+1)
    
    # Derecha
    elif orientacion == 1:
        izq_valor = get_valor_seguro(ambiente, i-1, j+1)
        cen_valor = get_valor_seguro(ambiente, i, j+1)
        der_valor = get_valor_seguro(ambiente, i+1, j+1)

    # Abajo
    elif orientacion == 2:
        izq_valor = get_valor_seguro(ambiente, i+1, j-1)
        cen_valor = get_valor_seguro(ambiente, i+1, j)
        der_valor = get_valor_seguro(ambiente, i+1, j+1)
    
    # Icquierda
    else:
        izq_valor = get_valor_seguro(ambiente, i-1, j-1)
        cen_valor = get_valor_seguro(ambiente, i, j-1)
        der_valor = get_valor_seguro(ambiente, i+1, j-1)

    return [izq_valor, cen_valor, der_valor]


def decidir_accion(percepcion_estados):
    
    if percepcion_estados['AVANZAR CELDA CENTRAL'] == "OSCURO":     # prioridad 1 buscar por el cen
        return "AVANZAR CELDA CENTRAL"
    elif percepcion_estados['AVANZAR CELDA DERECHA'] == "OSCURO":   # prioridad 2 buscar por el der
        return "AVANZAR CELDA DERECHA"
    elif percepcion_estados['AVANZAR CELDA IZQUIERDA'] == "OSCURO":   # prioridad 3 buscar por el izq
        return "AVANZAR CELDA IZQUIERDA"
    else:
        return "ROTAR_-90"


# ===== BUCLE DE OPERACION ======
#  0 es linea no oscura
#  1 es linea oscura
# -1 es pared (P)

for paso in range(max_pasos):
    f, c = agent_pos
    es_oscuro = ambiente[f, c] == 1 # se convirete en un bool/ True o False
    estado_actual = camara1(es_oscuro)  # oscuro o no oscuro
    valor_izq, valor_cen, valor_der = posicion_celdas_delanteras(ambiente, orientacion, agent_pos)
    estados_delanteros = camara2(valor_izq, valor_cen, valor_der)
    accion = decidir_accion(estados_delanteros)
    
    # DIBUJAR EL ROBOT EN EL MAPA
    print(f"--- AMBIENTE {paso} ---")
    for row in range(N):
        fila_str = ""
        for col in range(M):
            if [row, col] == agent_pos:
                fila_str = fila_str + f" {obtener_orientacion(orientacion)}  "
            elif ambiente[row, col] == 1:
                fila_str = fila_str + " 1 "
            elif ambiente[row, col] == -1:
                fila_str = fila_str + " P "
            else:
                fila_str = fila_str + " 0 "
            
        print(fila_str)
    print(f"Posicion: {agent_pos} | Orientacion:{obtener_orientacion(orientacion)}")
    print(f"valores delanteos:{valor_izq}, {valor_cen}, {valor_der}")
    print(f"Estado Actual: {estado_actual}")
    print(f"Estados delante: {estados_delanteros}")
    print(f"Accion: {accion}")

    
    #print(ambiente)

    # EJECUTAR LAS ACCIONES
    pared = False
    if accion == "ROTAR_-90":
        orientacion = (orientacion + 1) % 4 # definicion de modulo
    if accion == "AVANZAR CELDA CENTRAL":
        #estado_actual = estados_delanteros[accion]
        nueva_f, nueva_c = f, c
        if orientacion == 0:
            nueva_f = nueva_f - 1
        elif orientacion == 1:
            nueva_c = nueva_c + 1
        elif orientacion == 2:
            nueva_f = nueva_f + 1
        elif orientacion == 3:
            nueva_c = nueva_c - 1
        if 0 <= nueva_f < N and 0 <= nueva_c < M and ambiente[nueva_f, nueva_c] != -1:
            agent_pos = [nueva_f, nueva_c]
        else:
            pared = True
    if accion == "AVANZAR CELDA IZQUIERDA":
        #estado_actual = estados_delanteros[accion]
        nueva_f, nueva_c = f, c
        if orientacion == 0:
            nueva_f = nueva_f - 1
            nueva_c = nueva_c - 1
        elif orientacion == 1:
            nueva_f = nueva_f - 1
            nueva_c = nueva_c + 1
        elif orientacion == 2:
            nueva_f = nueva_f + 1
            nueva_c = nueva_c + 1
        elif orientacion == 3:
            nueva_f = nueva_f + 1
            nueva_c = nueva_c - 1
        if 0 <= nueva_f < N and 0 <= nueva_c < M and ambiente[nueva_f, nueva_c] != -1:
            agent_pos = [nueva_f, nueva_c]
        else:
            pared = True
    if accion == "AVANZAR CELDA DERECHA":
        nueva_f, nueva_c = f, c
        if orientacion == 0:
            nueva_f = nueva_f - 1
            nueva_c = nueva_c + 1
        elif orientacion == 1:
            nueva_f = nueva_f + 1
            nueva_c = nueva_c + 1
        elif orientacion == 2:
            nueva_f = nueva_f + 1
            nueva_c = nueva_c - 1
        elif orientacion == 3:
            nueva_f = nueva_f - 1
            nueva_c = nueva_c - 1
        if 0 <= nueva_f < N and 0 <= nueva_c < M and ambiente[nueva_f, nueva_c] != -1:
            agent_pos = [nueva_f, nueva_c]
        else:
            pared = True

    time.sleep(0.5)
