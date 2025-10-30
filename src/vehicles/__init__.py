"""Vehicles package (collection of drivable objects).

Currently contains a single `Bike` vehicle implementation.
"""
from .bike import Bike
from .car import Car

__all__ = ["Bike", "Car"]
