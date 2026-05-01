import os
import sys
import time
import numpy as np
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Agregamos la carpeta raíz (ai-search-agents) al buscador de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logging_config import obtener_logger

log = obtener_logger("AgenteNXN")

# CONFIGURACION DEL AMBIENTE

# 0 = Vacio,  1 = Basura (B), -1 = obstaculo (Negro)

ambiente  = np.zeros((7, 7))

ambiente[0, 0] = -1; ambiente[0, 2] = 1; ambiente[0, 4] = 1; ambiente[0, 5] = -1
ambiente[1, 0] = 1; ambiente[1, 1] = 1; ambiente[1, 3] = 1; ambiente[1, 4] = -1; ambiente[1, 6] = 1
ambiente[2, 1] = 1; ambiente[2, 2] = 1; ambiente[2, 3] = 1
ambiente[3, 0] = -1; ambiente[3, 3] = -1; ambiente[3, 5] = -1; ambiente[3, 6] = -1
ambiente[4, 1] = -1
ambiente[5, 1] = 1; ambiente[5, 2] = 1; ambiente[5, 3] = -1; ambiente[5, 4] = -1
ambiente[6, 0] = 1; ambiente[6, 1] = -1; ambiente[6, 2] = -1; ambiente[6, 5] = 1; ambiente[6, 6] = -1
#print("--- AMBIENTE INICIAL ---")
#print(ambiente)

# Estado inicial del agente (según la imagen empieza en fila 1, col 7 -> índice 0, 6)
# Orientación: 0: Arriba (▲), 1: Derecha (▶), 2: Abajo (▼), 3: Izquierda (◀)
agent_pos = [0, 6]     # posicion inicial
orientacion = 1        
choque = False
max_pasos = 50 # control de tiempo/pasos evitar el bucle infinito

'''
def obtener_simbolo(obs):
    return {0: "arriba",
            1: "derecha",
            2: "abajo",
            3: "izquierda"}[obs]
'''
def obtener_simbolo(obs):
    return {0: "▲", 1: "▶", 2: "▼", 3: "◀"}[obs]

# LOGICA DEL AGENTE (reflejo simple)
def decidir_accion(percepcion):
    choque, basura = percepcion

    # regla 1: si hay basura, Limpiar
    if basura:
        return "LIMPIAR"
    
    # regla 2: si choco con pared, Girar
    if choque:
        return "ROTAR_90"
    
    # regla 3: Si no hay nada, Avanzar
    return "AVANZAR"

# BUCLE DE OPERACION
for paso in range(max_pasos):
    f, c = agent_pos
    hay_basura = ambiente[f, c] == 1

    # el agente percibe
    accion = decidir_accion((choque, hay_basura))

    # visualizar
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"PASO: {paso}/{max_pasos} | Direccion: {obtener_simbolo(orientacion)} | Choque: {choque} | Acción: {accion}")

    # Dibujar mapa
    for r in range(7):
        fila_str = ""
        for col in range(7):
            if [r, col] == agent_pos:
                fila_str += f" {obtener_simbolo(orientacion)} "
            elif ambiente[r, col] == -1:
                fila_str += " ██ "
            elif ambiente[r, col] == 1:
                fila_str += " B "
            else:
                fila_str += " . "
        print(fila_str)

    # EJECUTAR LA ACCION
    choque = False # resetar choque
    if accion =="LIMPIAR":
        ambiente[f, c] = 0
    elif accion == "ROTAR_90":
        orientacion = (orientacion + 1) % 4
    elif accion == "AVANZAR":
        nueva_f, nueva_c = f, c
        if orientacion == 0: nueva_f -= 1 # Arriba
        elif orientacion == 1: nueva_c += 1 # Derecha
        elif orientacion == 2: nueva_f += 1 # Abajo
        elif orientacion == 3: nueva_c -= 1 # Izquierda

        if 0 <= nueva_f < 7 and 0 <= nueva_c < 7 and ambiente[nueva_f, nueva_c] != -1:
            agent_pos = [nueva_f, nueva_c]
        else:
            choque = True # sensor detecta el choque y se activa
    
    # Verificación de salida: ¿Queda basura?
    if not np.any(ambiente == 1):
        print(" ¡MAPA LIMPIO! El agente ha terminado.")
        break

    time.sleep(0.5)
        
if paso == max_pasos - 1:
    print(" Se agotó el tiempo (Límite de pasos alcanzado).")
