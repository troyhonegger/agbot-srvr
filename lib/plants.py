NONE = 0
FOXTAIL = 1
COCKLEBUR = 2
RAGWEED = 4
CORN = 8

"""Represents a structure specifying the existence of one or more plants"""
class PlantInfo:
	def __init__(self, *plants):
		self.plants = NONE
		for plant in plants:
			self.plants |= plant
	def add(self, plant):
		self.plants |= plant
	def contains(self, plant):
		return self.plants & plant != NONE
	def __repr__(self):
		return str(self)
	def __str__(self):
		plants = []
		if self.contains(FOXTAIL):
			plants.append('Foxtail')
		if self.contains(COCKLEBUR):
			plants.append('Cocklebur')
		if self.contains(RAGWEED):
			plants.append('Ragweed')
		if self.contains(CORN):
			plants.append('Corn')
		
		if len(plants) == 0:
			return ''
		else:
			return ', '.join(plants)