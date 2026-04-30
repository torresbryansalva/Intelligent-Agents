import random

class VacuumEnvironment:
    def __init__(self):
        self.locations = {'A': 'Clean', 'B': 'Clean'}
        self.agent_location = random.choice(['A', 'B'])

        #ensuciar aleatoriamente para la prueba
        self.locations['A'] = random.choice(['Clean', 'Dirty'])
        self.locations['B'] = random.choice(['Clean', 'Dirty'])

    def get_perception(self):
        return {
            'location': self.agent_location,
            'status': self.locations[self.agent_location]
        }
    
    def execute_action(self, action):
        print(f"Ejecutando accion: {action}")
        if action == 'Suck':
            self.locations[self.agent_location] = 'Clean'
        elif action == 'Right':
            self.agent_location = 'B'
        elif action == 'Left':
            self.agent_location = 'A'
        
    def display_state(self):
        print(f"Estado Ambiente: {self.locations} | Agente en {self.agent_location}")
        print("-"*30)