import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ===== CONFIGURACIÓN INICIAL DEL AMBIENTE =====
N, M = 7, 8
ambiente = np.random.choice([0, 1, -1], size=(N, M), p=[0.4, 0.5, 0.1])

f = np.random.randint(0, N)
c = np.random.randint(0, M)

# Evitar iniciar en pared
while ambiente[f, c] == -1:
    f = np.random.randint(0, N)
    c = np.random.randint(0, M)

agent_pos = [f, c]
orientacion = 1
max_pasos = 100

# ===== FUNCIONES AUXILIARES====
def obtener_orientacion_str(o):
    return {0: "Arriba", 1: "Derecha", 2: "Abajo", 3: "Izquierda"}[o]

def camara1(v):
    return "OSCURO" if v else "NO OSCURO"

def camara2(v1, v2, v3):
    mapa = {1: "OSCURO", 0: "NO OSCURO", -1: "PARED"}
    return {'Celda Izq.': mapa[v1], 'Celda Cent.': mapa[v2], 'Celda Der.': mapa[v3]}

def get_valor_seguro(mat, i, j):
    if 0 <= i < mat.shape[0] and 0 <= j < mat.shape[1]:
        return mat[i, j]
    return -1

def posicion_celdas_delanteras(amb, o, pos):
    i, j = pos
    if o == 0:
        return get_valor_seguro(amb,i-1,j-1), get_valor_seguro(amb,i-1,j), get_valor_seguro(amb,i-1,j+1)
    elif o == 1:
        return get_valor_seguro(amb,i-1,j+1), get_valor_seguro(amb,i,j+1), get_valor_seguro(amb,i+1,j+1)
    elif o == 2:
        return get_valor_seguro(amb,i+1,j+1), get_valor_seguro(amb,i+1,j), get_valor_seguro(amb,i+1,j-1)
    else:
        return get_valor_seguro(amb,i+1,j-1), get_valor_seguro(amb,i,j-1), get_valor_seguro(amb,i-1,j-1)

def decidir_accion(estados, pasos):
    izq = estados['Celda Izq.']
    cen = estados['Celda Cent.']
    der = estados['Celda Der.']
    if cen == "PARED":
        return "ROTAR_-90"
    if cen == "OSCURO":
        return "AVANZAR"
    if der == "OSCURO" and cen == "NO OSCURO":
        return "AVANZAR,-90"
    if izq == "OSCURO" and cen == "NO OSCURO":
        return "AVANZAR,+90"
    if der == "PARED" and cen == "NO OSCURO":
        return "ROTAR_-90"
    if izq == "PARED" and cen == "NO OSCURO":
        return "ROTAR_-90"
    if izq == "NO OSCURO" and cen == "NO OSCURO" and der == "NO OSCURO":
            return "ROTAR_-90"
    # Búsqueda
    if pasos % 4 == 0:
        return "ROTAR_+90"
    elif pasos % 4 == 1:
        return "AVANZAR"
    elif pasos % 4 == 2:
        return "ROTAR_-90"
    else:
        return "ROTAR_-90"

def rotar(o, acc):
    if acc == "ROTAR_-90":
        return (o + 1) % 4
    elif acc == "ROTAR_+90":
        return (o - 1) % 4
    return o

def avanzar_central(f, c, o):
    if o == 0: return f-1, c
    if o == 1: return f, c+1
    if o == 2: return f+1, c
    if o == 3: return f, c-1

def es_valido(nf, nc):
    return 0 <= nf < N and 0 <= nc < M and ambiente[nf, nc] != -1

def describir(v):
    return {1:"oscuro",0:"blanco",-1:"pared"}.get(v,"?")

# ===== INTERFAZ GRAFICA =====
plt.ion()
fig, ax = plt.subplots()

def dibujar(paso):
    ax.clear()
    img = np.zeros((N, M, 3))

    for i in range(N):
        for j in range(M):
            if ambiente[i,j] == 1:
                img[i,j] = [0.3,0.3,0.3]
            elif ambiente[i,j] == -1:
                img[i,j] = [0.6,0.3,0.1]
            else:
                img[i,j] = [1,1,1]

    ax.imshow(img)

    # Dibujar agente como flecha
    direcciones = {
        0: (0, -0.4),  # arriba
        1: (0.4, 0),  # derecha
        2: (0, 0.4),  # abajo
        3: (-0.4, 0)  # izquierda
    }
    dx, dy = direcciones[orientacion]

    ax.arrow(
        agent_pos[1] - dx / 2,
        agent_pos[0] - dy / 2,
        dx, dy,
        head_width=0.3,
        head_length=0.3,
        width=0.08,
        fc='red',
        ec='darkred',
        zorder=5
    )

    # Sombra
    for r in range(N):
        for c in range(M):
            sombra = patches.Rectangle(
                (c - 0.45, r - 0.45), 1, 1,
                facecolor=[0.2, 0.2, 0.2],  # sombra (gris oscuro suave),
                alpha=0.08,
                linewidth=0,
                zorder=1
            )
            ax.add_patch(sombra)

    # Hatch en paredes
    for r in range(N):
        for c in range(M):
            if ambiente[r, c] == -1:
                rect = patches.Rectangle(
                    (c - 0.5, r - 0.5), 1, 1,
                    hatch='--',
                    fill=False,
                    edgecolor='darkred',
                    linewidth=0,
                    zorder=3
                )
                ax.add_patch(rect)

    # Estética de la cuadrícula
    ax.set_title(f"Paso {paso + 1}")
    # Límites del eje
    ax.set_xlim(-0.5, M - 0.5)
    ax.set_ylim(N - 0.5, -0.5)

    # Ticks mayores (ocultos)
    ax.set_xticks(np.arange(0, M, 1))
    ax.set_yticks(np.arange(0, N, 1))
    ax.set_xticklabels([])
    ax.set_yticklabels([])

    # Ticks menores (para la grilla)
    ax.set_xticks(np.arange(-0.5, M, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, N, 1), minor=True)

    # Cuadrícula
    ax.grid(which='minor', color='black', linestyle='-', linewidth=1)

    # Bordes negros gruesos
    for spine in ax.spines.values():
        spine.set_visible(True)  # importante
        spine.set_edgecolor('black')  # negro
        spine.set_linewidth(3)  # grosor

    plt.draw()
    plt.pause(0.7)

    # GUARDAR IMAGEN
    #nombre_archivo = os.path.join(carpeta_frames, f"frame_paso_{paso + 1:03d}.png")
    #plt.savefig(nombre_archivo)

# ===== LOOP =====
pasos_sin_linea = 0
estados_visitados = {}  # {(f, c, orientacion, pasos_sin_linea % 4): paso}
bucle_info = None

for paso in range(max_pasos):
    f, c = agent_pos
    estado_actual = camara1(ambiente[f,c] == 1)
    v_izq, v_cen, v_der = posicion_celdas_delanteras(ambiente, orientacion, agent_pos)
    estados = camara2(v_izq, v_cen, v_der)
    hay_linea = any(v=="OSCURO" for v in estados.values())
    pasos_sin_linea = 0 if hay_linea else pasos_sin_linea + 1

    # Detección de bucle infinito: estado interno repetido => decisión repetida (entorno estático)
    clave_estado = (f, c, orientacion, pasos_sin_linea % 4)
    if clave_estado in estados_visitados and bucle_info is None:
        inicio = estados_visitados[clave_estado]
        largo_ciclo = paso - inicio
        bucle_info = {
            "iter_hasta_bucle": inicio + 1,
            "largo_ciclo": largo_ciclo,
            "complejidad_total": paso + 1,
        }
        print(f"\n>>> BUCLE detectado en paso {paso+1}")
        print(f"    Primera visita del estado: paso {inicio+1}")
        print(f"    Iteraciones hasta entrar al bucle: {inicio+1}")
        print(f"    Largo del ciclo: {largo_ciclo}")
        print(f"    Complejidad total: {inicio+1} + {largo_ciclo} (bucle)")
        break
    estados_visitados[clave_estado] = paso

    accion = decidir_accion(estados, pasos_sin_linea)
    dibujar(paso)
    print(f"\nPaso {paso+1}")
    print(f"Pos: [{agent_pos[0] + 1}, {agent_pos[1] + 1}] | {obtener_orientacion_str(orientacion)}")
    print(f"Celda actual (CAM1): {estado_actual}")
    print(f"Celdas delanteras (CAM2):")
    print(f"Izq:{describir(v_izq)} Cen:{describir(v_cen)} Der:{describir(v_der)}")
    print(f"Contacto: {'Si' if v_cen == -1 else 'No'}")
    print(f"Acción: {accion}")

    # ===== EJECUCIÓN =====
    for acc in accion.split(","):

        if acc == "AVANZAR":
            nf, nc = avanzar_central(agent_pos[0], agent_pos[1], orientacion)

            if es_valido(nf, nc):
                agent_pos = [nf, nc]
            else:
                break
        elif acc == "+90":
            orientacion = rotar(orientacion, "ROTAR_+90")
        elif acc == "-90":
            orientacion = rotar(orientacion, "ROTAR_-90")
        elif acc in ["ROTAR_+90", "ROTAR_-90"]:
            orientacion = rotar(orientacion, acc)

print("\nSimulación terminada")
if bucle_info is not None:
    print(f"Iteraciones hasta entrar al bucle: {bucle_info['iter_hasta_bucle']}")
    print(f"Largo del ciclo: {bucle_info['largo_ciclo']}")
    print(f"Complejidad total: {bucle_info['iter_hasta_bucle']} + {bucle_info['largo_ciclo']} (bucle)")
else:
    print(f"No se detectó bucle en {max_pasos} pasos.")
plt.ioff()
plt.show()