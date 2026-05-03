import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

# --- Configuración inicial del ambiente (Tu lógica original) ---
N, M = 7, 8
ambiente = np.random.choice([0, 1, -1], size=(N, M), p=[0.4, 0.5, 0.1])
f  = np.random.randint(0, N-1)
c  = np.random.randint(0, M-1)
agent_pos = [f, c]
orientacion = 1 
max_pasos = 10

# ===== FUNCIONES DE LÓGICA (Tus funciones originales) =====
def obtener_orientacion_str(obs):
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
        izq_valor = get_valor_seguro(ambiente, i+1, j+1)
        cen_valor = get_valor_seguro(ambiente, i+1, j)
        der_valor = get_valor_seguro(ambiente, i+1, j-1)
    
    # Icquierda
    else:
        izq_valor = get_valor_seguro(ambiente, i+1, j-1)
        cen_valor = get_valor_seguro(ambiente, i, j-1)
        der_valor = get_valor_seguro(ambiente, i-1, j-1)

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

# ===== CONFIGURACIÓN DE LA INTERFAZ MATPLOTLIB =====
plt.ion() # Modo interactivo encendido
fig, (ax_mapa, ax_info) = plt.subplots(1, 2, figsize=(10, 5), gridspec_kw={'width_ratios': [1, 1]})

def dibujar_mundo(paso, accion, v_izq, v_cen, v_der, estado_actual, estados_delanteros):
    ax_mapa.clear()
    display_map = np.zeros((N, M))
    for r in range(N):
        for c in range(M):
            if ambiente[r, c] == 1: display_map[r, c] = 0.5  # Gris para camino
            elif ambiente[r, c] == -1: display_map[r, c] = 1 # Negro para pared
    
    ax_mapa.imshow(display_map, cmap='binary', origin='upper')
    
    # Dibujar al Robot (una flecha roja)
    # Ajustamos la rotación (Matplotlib usa grados, 0 es derecha)
    direcciones = {
        0: (0, -0.35),  # Arriba
        1: (0.35, 0),   # Derecha
        2: (0, 0.35),   # Abajo
        3: (-0.35, 0)   # Izquierda
    }
    dx, dy = direcciones[orientacion]
    x_inicio = agent_pos[1] - (dx / 2)
    y_inicio = agent_pos[0] - (dy / 2)
    # Dibujamos una flecha con cuerpo y cabeza
    ax_mapa.arrow(x_inicio, y_inicio, dx, dy, 
             head_width=0.3,      # Ancho de la punta
             head_length=0.3,     # Largo de la punta
             width=0.08,          # Grosor de la colita
             fc='red', ec='darkred', zorder=5)
    
    # Estética de la cuadrícula
    ax_mapa.set_title(f"Ambiente - Paso {paso}")
    ax_mapa.grid(which='minor', color='black', linestyle='-', linewidth=1)
    ax_mapa.set_xticks(np.arange(-.5, M, 1), minor=True)
    ax_mapa.set_yticks(np.arange(-.5, N, 1), minor=True)
    
    # 2 LIMPIAR Y DIBUJAR
    ax_info.clear()
    ax_info.axis('off') # Ocultar ejes del panel de texto
    
    info_texto = (
        f"--- ESTADO DEL AGENTE ---\n\n"
        f"Paso actual: {paso}\n"
        f"Posición: {agent_pos}\n"
        f"Orientación: {obtener_orientacion_str(orientacion)}\n\n"
        f"--- SENSORES ---\n"
        f"Estado Actual: {estado_actual}\n"
        f"Valores delante: {v_izq, v_cen, v_der}\n"
        f"Percepción:\n  Izq: {estados_delanteros['AVANZAR CELDA IZQUIERDA']}\n"
        f"  Cen: {estados_delanteros['AVANZAR CELDA CENTRAL']}\n"
        f"  Der: {estados_delanteros['AVANZAR CELDA DERECHA']}\n\n"
        f"--- DECISIÓN ---\n"
        f"Acción: {accion}"
    )
    # Escribir el texto en el segundo subplot
    ax_info.text(0.05, 0.95, info_texto, transform=ax_info.transAxes, 
                 fontsize=11, verticalalignment='top', family='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    plt.draw()
    plt.pause(1.0)

# ===== BUCLE DE OPERACIÓN CON INTERFAZ ======
try:
    for paso in range(max_pasos):
        # Lógica de sensores (PERCEPCIONES)
        f, c = agent_pos
        es_oscuro = ambiente[f, c] == 1
        estado_actual = camara1(es_oscuro)
        v_izq, v_cen, v_der = posicion_celdas_delanteras(ambiente, orientacion, agent_pos)
        estados_delanteros = camara2(v_izq, v_cen, v_der)
        accion = decidir_accion(estados_delanteros)
    
        
        # Dibujar antes de mover para ver el estado actual
        dibujar_mundo(paso, accion, v_izq, v_cen, v_der, estado_actual, estados_delanteros)
        '''
        # DIBUJAR EL ROBOT EN EL MAPA
        print(f"--- AMBIENTE {paso} ---")
        for row in range(N):
            fila_str = ""
            for col in range(M):
                if [row, col] == agent_pos:
                    fila_str = fila_str + f" {obtener_orientacion_str(orientacion)}  "
                elif ambiente[row, col] == 1:
                    fila_str = fila_str + " 1 "
                elif ambiente[row, col] == -1:
                    fila_str = fila_str + " P "
                else:
                    fila_str = fila_str + " 0 "

            print(fila_str)


        print(f"Posicion: {agent_pos} | Orientacion:{obtener_orientacion_str(orientacion)}")
        print(f"valores delanteos:{v_izq}, {v_cen}, {v_der}")
        print(f"Estado Actual: {estado_actual}")
        print(f"Estados delante: {estados_delanteros}")
        print(f"Accion: {accion}")
        '''
        # EJECUTAR LAS ACCIONES (Simplificado para el ejemplo)
        if accion == "ROTAR_-90":
            orientacion = (orientacion + 1) % 4
        else:
            # Lógica de movimiento
            nf, nc = f, c
            if accion == "AVANZAR CELDA CENTRAL":
                if orientacion == 0: nf -= 1
                elif orientacion == 1: nc += 1
                elif orientacion == 2: nf += 1
                elif orientacion == 3: nc -= 1
                # Validar límites y paredes
                if 0 <= nf < N and 0 <= nc < M and ambiente[nf, nc] != -1:
                    agent_pos = [nf, nc]
                else:
                    pared = True
            elif accion == "AVANZAR CELDA IZQUIERDA":
                if orientacion == 0: nf, nc = f-1, c-1
                elif orientacion == 1: nf, nc = f-1, c+1
                elif orientacion == 2: nf, nc = f+1, c+1
                elif orientacion == 3: nf, nc = f+1, c-1
                # Validar límites y paredes
                if 0 <= nf < N and 0 <= nc < M and ambiente[nf, nc] != -1:
                    agent_pos = [nf, nc]
                else:
                    pared = True
            elif accion == "AVANZAR CELDA DERECHA":
                if orientacion == 0: nf, nc = f-1, c+1
                elif orientacion == 1: nf, nc = f+1, c+1
                elif orientacion == 2: nf, nc = f+1, c-1
                elif orientacion == 3: nf, nc = f-1, c-1
                # Validar límites y paredes
                if 0 <= nf < N and 0 <= nc < M and ambiente[nf, nc] != -1:
                    agent_pos = [nf, nc]
                else:
                    pared = True
            
    print("Simulación terminada.")
    plt.ioff()
    plt.show()

except KeyboardInterrupt:
    print("Simulación detenida por el usuario.")







"""
Como correr: En terminal de VScode 
* Abrir terminal:       ctrl + shift + ñ
* Correr:               python agents/tarea3_view.py 
"""