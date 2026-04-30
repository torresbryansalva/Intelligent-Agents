from agents.reflex_agent import SimpleReflexVacuumAgent
from utils.simulation import VacuumEnvironment
import time

def main():
    env = VacuumEnvironment()
    agent = SimpleReflexVacuumAgent()

    print("--- Iniciando Simulacion de Agente Aspiradora ---")

    #Ejecutar 5 pasos de tiempo
    for i in range(5):
        print(f"\nPaso {i+1}:")
        env.display_state()

        perception = env.get_perception()
        action = agent.act(perception)
        env.execute_action(action)

        time.sleep(1)

    print("\nSimulacion finalizada.")
    env.display_state()

if __name__ == '__main__':
    main()