def Start():
	HTTP.CacheTime = 0

class Cine21Agent(Agent.Movies):
	name = 'Cine21'
	primary_provider = False
	languages = [Locale.Language.Korean]

	def search(self, results, media, lang):
		pass

	def update(self, metadata, media, lang):
		pass
