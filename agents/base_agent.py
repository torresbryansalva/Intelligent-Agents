from abc import ABC, abstractmethod

class Agent(ABC):
    def __init__(self, name="BaseAgent"):
        self.name = name
    
    @abstractmethod
    def act(self, perception):
        """
        Recibe una percepcion del entorno y devuelve una accion
        """
        pass
    