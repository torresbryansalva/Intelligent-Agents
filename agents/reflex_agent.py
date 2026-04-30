from .base_agent import Agent

class SimpleReflexVacuumAgent(Agent):
    def __init__(self):
        super().__init__(name="SimpleReflexVacuum")

        #Reglas de condicion-accion
        self.rules = {
            'Dirty': 'Suck',
            'Location_A': 'Right',
            'Location_B': 'Left'
        }

    def act(self, perception):
        """
        Perception format: {'Location': 'A', 'Status': 'Dirty'}
        """
        location = perception['location']
        status = perception['status']

        print(f"[{self.name}] Percibo que en {location} el estado es: {status}")

        if status == 'Dirty':
            return self.rules['Dirty']
        elif location == 'A':
            return self.rules['Location_A']
        elif location == 'B':
            return self.rules['Location_B']
