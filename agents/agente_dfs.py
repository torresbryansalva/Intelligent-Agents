import time
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DEL ESCENARIO 4x4 ---
N, M = 4, 4
# 0: libre, -1: pared
ambiente = np.array([
    [ 0,  0,  0,  0],
    [ 0, -1, -1,  0],
    [ 0,  0, -1,  0],
    [-1,  0,  0,  0]
])

inicio = (0, 0)
meta = (3, 3)

print(ambiente)

# logica de DFS 
def buscar_dfs():
    pila = [inicio] # LIFO : last in First out
    visitados = set()  # conjunto unico
    historial_pasos = [] # para animacion
    while pila:
        nodo_actual = pila[-1] # mirar el ultimo elemento
        
        # condicion de salida, evitar el loop infinito
        if nodo_actual == meta:
            historial_pasos.append((list(pila), list(visitados)))
            return pila, historial_pasos 
         

