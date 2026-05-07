import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

# --- Configuración inicial del ambiente (Tu lógica original) ---
N, M = 10, 10
ambiente = np.random.choice([0, 1, -1], size=(N, M), p=[0.4, 0.5, 0.1])
f  = np.random.randint(0, N-1)
c  = np.random.randint(0, M-1)
agent_pos = [f, c]
orientacion = 1 
max_pasos = 30

print(f"  =========================================== REGLAS ================================================")
print(f"| Regla |    Borde    |  Piso Actual  |   Piso Izq   |  Piso Cen  |  Piso Der  |  Orient  |  Accion  |")
print(f"|   1   |   Contacto  |       *       |      *       |      *     |     *      |    *     |    +90   |")
print(f"|   2   | No Contacto |    Oscuro     |    Oscuro    |   Oscuro   |   Oscuro   |    *     |  Avanzar |")
print(f"|   3   | No Contacto |    Oscuro     |  No Oscuro   |   Oscuro   |  No Oscuro |    *     |  Avanzar |")
print(f"|   4   | No Contacto |    Oscuro     |    Oscuro    |  No Oscuro |  No Oscuro |    *     |    -90   |")
print(f"|   5   | No Contacto |    Oscuro     |  No Oscuro   |  No Oscuro |   Oscuro   |    *     |    +90   |")
print(f"|   6   | No Contacto |    Oscuro     |    Borde     |      *     |     *      |    *     |    +90   |")
print(f"|   7   | No Contacto |    Oscuro     |      *       |      *     |   Borde    |    *     |    -90   |")
print(f"|   8   | No Contacto |  No Oscuro    |    Oscuro    |      *     |     *      |    *     |    -90   |")
print(f"|   9   | No Contacto |  No Oscuro    |      *       |      *     |   Oscuro   |    *     |    +90   |")
print(f"|  10   | No Contacto |  No Oscuro    |  No Oscuro   |   Oscuro   |  No Oscuro |    *     |  Avanzar |")
print(f"|  11   | No Contacto |  No Oscuro    |  No Oscuro   |  No Oscuro |  No Oscuro |    *     |  Avanzar |")


# ===== FUNCIONES DE LÓGICA (Tus funciones originales) =====
def obtener_orientacion_str(obs):
    """
    Funcion que se encarga de obtener la direccion del agente
    input: int
    output: str
    """

    return {0: "Arriba", 1: "Derecha", 2: "Abajo", 3: "Izquierda"}[obs]

def camara1(vision):
    """
    Funcion que simula la la camara 1 que sol mira el piso
    input: bool
    output: str
    """
    if vision:
        return "OSCURO"
    return "NO OSCURO"

def camara2(valor1, valor2, valor3):
    """
    Funcion que simula la la camara 2 y que observa las 3 celdas delante del robot
    input: int, int, int
    output: dic{key:value}
    """
    
    valores = {0:'NO OSCURO', 1: 'OSCURO', -1:'PARED'}
    
    return {'AVANZAR CELDA IZQUIERDA': valores[valor1],
            'AVANZAR CELDA CENTRAL': valores[valor2],
            'AVANZAR CELDA DERECHA': valores[valor3]
        }

def get_valor_seguro(matrix, i, j, valor_por_defecto=-1):
    """
    Funcion que verifica los limites de la matriz y algun calculo se sale de los lmites se marca como pared :-1

    input: np.ndimm, int, int, int
    output: int
    """
    filas, columnas = matrix.shape
    if 0 <= i < filas and 0 <= j < columnas:
        return matrix[i,j]
    return valor_por_defecto

def posicion_celdas_delanteras(ambiente, orientacion, pos):
    """
    fucion que se encarga de obtener las posiciones i, j de la celdas delantes vistas por la camara 2

    input: matriz(n, m), int, tupla(int, int)
    output: list(int, int, int)
    """
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
    
    # Izquierda
    else:
        izq_valor = get_valor_seguro(ambiente, i+1, j-1)
        cen_valor = get_valor_seguro(ambiente, i, j-1)
        der_valor = get_valor_seguro(ambiente, i-1, j-1)

    return [izq_valor, cen_valor, der_valor]

def decidir_accion(estados_delanteros, pasos_sin_linea):
    """
    funcion que se encarga de mover/girar al agente a una estado nuevo

    input: dict(key, values), int
    output: str
    """
    izq = estados_delanteros['AVANZAR CELDA IZQUIERDA']
    cen = estados_delanteros['AVANZAR CELDA CENTRAL']
    der = estados_delanteros['AVANZAR CELDA DERECHA']

    if cen == "OSCURO":     # prioridad 1 buscar por el cen
        return "AVANZAR CELDA CENTRAL"
    if der == "OSCURO":   # prioridad 2 buscar por el der
        return "AVANZAR CELDA DERECHA"
    if izq == "OSCURO":  # prioridad 3 buscar por el izq
        return "AVANZAR CELDA IZQUIERDA"
    
    # Línea perdida: rotar una vez, luego avanzar
    # Ciclo determinista: +90 → avanzar → -90 → avanzar → repite
    if pasos_sin_linea % 4 == 0:
        return "ROTAR_+90"
    elif pasos_sin_linea % 4 == 1:
        return "AVANZAR CELDA CENTRAL"
    elif pasos_sin_linea % 4 == 2:
        return "ROTAR_-90"
    elif pasos_sin_linea % 4 == 3: # caso en las esquinas y estado blanco
        return "ROTAR_-90"
    else:
        return "AVANZAR CELDA CENTRAL"
    

# ===== CONFIGURACIÓN DE LA INTERFAZ MATPLOTLIB =====
plt.ion() # Modo interactivo encendido
fig, (ax_mapa, ax_info) = plt.subplots(1, 2, figsize=(10, 5), gridspec_kw={'width_ratios': [1, 1]})

def dibujar_mundo(paso, accion, v_izq, v_cen, v_der, estado_actual, estados_delanteros):
    """
    Funcion que se encarga de dibujar la interfaz vizual
    """
    ax_mapa.clear()
    
    display_map = np.zeros((N, M, 3))  # ahora es RGB
    for r in range(N):
        for c in range(M):
            if ambiente[r, c] == 1:
                display_map[r, c] = [0.3, 0.3, 0.3]           # negro → línea
            elif ambiente[r, c] == -1:
                display_map[r, c] = [0.55, 0.27, 0.07]  # marrón → pared
            else:
                display_map[r, c] = [1, 1, 1]            # blanco → camino libre

    ax_mapa.imshow(display_map, origin='upper')  # sin cmap, ahora usa RGB directo
    
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
    
    # ── agregar estas 2 líneas ──
    ax_mapa.set_xlim(-0.5, M - 0.5)
    ax_mapa.set_ylim(N - 0.5, -0.5)  # invertido porque origin='upper'

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
"""
Funcion principal del agente donde  percibe su entonro y actua
"""
try:
    for paso in range(max_pasos):
        # Lógica de sensores (PERCEPCIONES)

        f, c = agent_pos
        es_oscuro = ambiente[f, c] == 1
        estado_actual = camara1(es_oscuro)
        v_izq, v_cen, v_der = posicion_celdas_delanteras(ambiente, orientacion, agent_pos)
        estados_delanteros = camara2(v_izq, v_cen, v_der)

        # detectar si hay linea visible
        hay_linea = any(
            v == "OSCURO" for v in estados_delanteros.values()
        )

        if hay_linea:
            pasos_sin_linea = 0 # resetear contador 
        else:
            pasos_sin_linea += 1 #acumular perdida

        accion = decidir_accion(estados_delanteros, pasos_sin_linea)
        
        # Dibujar antes de mover para ver el estado actual
        dibujar_mundo(paso, accion, v_izq, v_cen, v_der, estado_actual, estados_delanteros)
        
        print(f"\nPASO: {paso}")
        print(f"Posicion: {agent_pos} | Orientacion: {obtener_orientacion_str(orientacion)}")
        print(f"valores delanteos: Izq= {v_izq}, Cen= {v_cen}, Der= {v_der}")
        print(f"Estado Actual: {estado_actual}")
        print(f"Estados delante: {estados_delanteros}")
        print(f"Accion: {accion}")
        print(f"="*70)

        # EJECUTAR LAS ACCIONES (Simplificado para el ejemplo)
        
        if accion == "ROTAR_-90":
            orientacion = (orientacion + 1) % 4
            
        elif accion =="ROTAR_+90":
            if orientacion == 0:
                orientacion = 4
            orientacion = (orientacion - 1) % 4
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