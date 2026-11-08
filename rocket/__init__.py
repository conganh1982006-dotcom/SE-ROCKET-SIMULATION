"""C5 educational reference, independent of the unavailable wmlab toolkit."""
from .model import Parameters
from .simulator import simulate
from .interface import Event, Trajectory, Simulator, quantities

__all__ = ["Parameters", "simulate", "Event", "Trajectory", "Simulator", "quantities"]
