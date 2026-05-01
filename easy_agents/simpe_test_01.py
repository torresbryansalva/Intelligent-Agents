import time
import numpy as np


#

# 1. EL ENTORNO (la matriz)

# Estados: 1 = Sucio, 0 = Limpio

ambiente = np.array([
    [1, 1],
    [0, 1]
    ]
)

print("EL AMBIENTE INICIAL:")
print(ambiente)
agent_pos = [0, 0]

# 2 LA FUNCIN DEL AGENTE (reflejo simple)
def decidir_accion(fila, columna, estado_sucio):
    if estado_sucio:
        return "Limpiar"
    
    # Movimiento en "S" para recorrer la matriz 2x2
    if fila == 0 and columna == 0: return "DERECHA"
    if fila == 0 and columna == 1: return "ABAJO"
    if fila == 1 and columna == 1: return "IZQUIERDA"
    if fila == 1 and columna == 0: return "ARRIBA"

    return "nada"

# 3 BUCLE DE EJECUCION

for paso in range(6):
    f, c = agent_pos
    suciedad = ambiente[f][c] == 1

    # el agente percibe y actua
    accion = decidir_accion(f, c, suciedad)
    print(f"Paso {paso +1}: Agente en [{f}, {c}] - Sucio:{suciedad} -> Accion:{accion}")

    # aplicar la accione en el ambiente
    if accion == "Limpiar":
        ambiente[f, c] = 0
        print("ESTADO ACTUAL")
        print(ambiente)
    elif accion == "DERECHA":
        agent_pos = [0, 1]
    elif accion == "ABAJO":
        agent_pos = [1, 1]
    elif accion == "IZQUIERDA":
        agent_pos = [1, 0]
    elif accion == "ARRIBA":
        agent_pos = [0, 0]

    time.sleep(1)

print("\nResultado final del mundo:")
print(ambiente)
