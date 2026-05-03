# A. COMO CORRER EN TERMINAL

python agents/a_star_structural.py

# B. modulos 
# b1. el modulo heapq :
    modulo que implementa una estructura de datos llamado *COLA DE PRIORIDAD*(Priority Queue), revis el nodo mas prometedor (En este caso revisa el peso total estimado mas bajo)

    Como trabaja en el codigo: A* usa a heapq para elegir que combinacion de perfiles W probar a continuacion - basado en el peso

# b2. el modulo anastruct: (es el oraculo)
    modulo que implementa el trabajo pesado de ingenieria
    - calculo de esfuerzos
    - calculo de demoraciones
    - similar en capacidad a SAP2000 o ETABS

    anastruct recibe la combinacion, "arma" virtualmente y calcula los esfuerzos

El codigo usa b1 y b2 para verificar si esos esfuerzos cumplen con la AISC 360-22, Si cumple pasa a la sgte, sino descarta la opcion y pide otra a heapq.
