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
    [-1,  0,  -1,  0]
])

inicio = (0, 0)
meta = (3, 3)

print(ambiente)

# logica de DFS 
def buscar_dfs():
    pila = [inicio] # LIFO : last in First out
    visitados = set()  # conjunto unico
    historial_pasos = [] # para animacion
    i = 0
    while pila:
        nodo_actual = pila[-1] # mirar el ultimo elemento
        print(f"\n PASO: {i}")
        print(f"pila: {pila}")
        print(f"nodo actual: {nodo_actual}")
        print(f"visitados: {visitados}")

        # condicion de salida, evitar el loop infinito
        if nodo_actual == meta:
            historial_pasos.append((list(pila), list(visitados)))
            return pila, historial_pasos 
         
        # marcar como visitado
        visitados.add(nodo_actual)

        # importante el orden de esta lista define que hijo busca primero
        # Abajo, derecha, arriba, izquierda
        r, c = nodo_actual
        vecinos = [(r+1, c), (r, c+1), (r-1, c), (r, c-1)]
        
        encontro_hijo = False
        for vr, vc in vecinos:
            if 0 <= vr < N and 0 <= vc < M and ambiente[vr, vc] != -1 and (vr, vc) not in visitados:
                pila.append((vr, vc))
                encontro_hijo = True
                break # Se sumerge inmediatamente (DFS puro)

        # 3. BACKTRACKING: Si no encontró ningún vecino libre, retrocede
        if not encontro_hijo:
            pila.pop()
            
        historial_pasos.append((list(pila), list(visitados)))
    return None, historial_pasos

# interfaz grafica
plt.ion()
fig, ax = plt.subplots(figsize=(6, 6))

def dibujar(paso_n, camino_actual, visitados):
    ax.clear()

    display_map = np.full((N, N), 0.8) # gris claro: vacio
    for r, c in visitados: display_map[r, c ] = 0.5 # gris oscuro :explorado
    for r, c in camino_actual: display_map[r, c ] = 0.3 # azulado: camino actual

    for r in range(N):
        for c in range(M):
            if ambiente[r, c] == -1 : display_map[r, c] = 0 #negro: pared
    
    ax.imshow(display_map, cmap='nipy_spectral', origin='upper')

    # Marcar inicio y meta
    ax.text(inicio[1], inicio[0], "INICIO", ha='center', va='center', color='green', weight='bold')
    ax.text(meta[1], meta[0], 'META', ha='center', va='center', color='gold', weight='bold')

    # dibujar el agente 
    if camino_actual:
        pos = camino_actual[-1]
        ax.plot(pos[1], pos[0], 'ro', markersize=15, label='Agente')
    
    ax.set_title(f"DFS - Paso: {paso_n}\nExplorando profundidad...")
    ax.set_xticks(np.arange(-.5, M, 1), minor=True)
    ax.set_yticks(np.arange(-.5, N, 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=2)
    plt.draw()
    plt.pause(1)

# ===== EJECUCIÓN =====
print("Iniciando búsqueda DFS...")
camino_final, historial = buscar_dfs()

for i, (camino, vis) in enumerate(historial):
    dibujar(i, camino, vis)

if camino_final:
    print(f"¡Meta alcanzada en {len(historial)} pasos!")
else:
    print("No se encontró un camino.")

plt.ioff()
plt.show()