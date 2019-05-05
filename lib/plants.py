import enum

class Plants(enum.IntFlag):
	NONE = 0
	Foxtail = 1
	Cocklebur = 2
	Ragweed = 4
	Corn = 8
	@classmethod
	def deserialize(cls, string):
		#the optional prefix 'Plants.' is accepted, but not necessary
		prefix = cls.__name__ + '.'
		plant = Plants.NONE
		for s in string.split('|'):
			s = s.strip()
			if s.startswith(prefix):
				s = s[len(prefix):]
			plant |= cls.__members__[s.strip()]
		return plant
	def __iter__(self):
		return [plant for plant in Plants if self & plant != Plants.NONE].__iter__()