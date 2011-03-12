import urllib2, urllib, string, random, types, unicodedata, re, datetime

CINE21_OPEN_API_URL = 'http://kr.lgtvsdp.com/SearchOpenAPI/api/search.xml?query=%s'
CINE21_META_URL = 'http://kr.lgtvsdp.com/SearchOpenAPI/api/searchDetail.xml?titleId=%s'

def Start():
#  HTTP.CacheTime = CACHE_1HOUR * 4
    HTTP.CacheTime = 0

class Cine21Agent(Agent.Movies):
  name = 'Cine21'
  primary_provider = True
  languages = [Locale.Language.Korean]
  accepts_from = ['com.plexapp.agents.localmedia']

  def GetFixedXML(self, url, isHtml=False):		# function for getting XML in the corresponding URL
    xml = HTTP.Request(url)
    #Log("xml in GetFixedXML = %s" % xml)
    return XML.ElementFromString(xml, isHtml)

  def search(self, results, media, lang):   
    name = unicodedata.normalize('NFKC', media.name.decode('utf-8')).encode('utf-8')   
    media_name = name.lower()
    #Log("after scanning! [media_name]: %s (%s), [media_year]: %s" %(media.name, name, media.year) )
    
    if media.year is None :
	yearMatch = re.search('([1-2][0-9]{3})', media_name)
	if yearMatch :
		yearStr = yearMatch.group(1)
		#yearAfter = yearMatch.group(3)
		yearInt = int(yearStr)
		if yearInt > 1900 and yearInt < (datetime.date.today().year + 1):
			media.year = yearInt
			media_name = media_name.replace(yearStr, '')	
    
    #Log("after revising! [media_name]: %s, [media_year]: %s" %(media_name, media.year) )

    url = CINE21_OPEN_API_URL %(urllib.quote(media_name))	# URL for movie name search
    xml = self.GetFixedXML(url)                                                           # to get XML for search result
    items = xml.xpath('//content')            
    order = 0

    for item in items:
	score = 95 - order*10										# score is set depending on the search ranking   
	order = order + 1											# A score for the first candidate is 95 and score is reduced by 10
	
	years = item.xpath('makeYear')								# at first, year is compared
        if years != [] : year = int(years[0].text)
	else :	    year = 0      
	if media.year is not None and year != 0:
		if( (int(media.year) - year) > 1 or (int(media.year) - year) < -1) :	# if year is different, other attributes are not compared
			#Log('year is different! this candidate is deleted!')
			continue
	
	id = item.xpath('titleId')[0].text								# ID

	thumb = ''
	#thumbs =item.xpath('imageList/image/imageUrl')				# thumb is not required. In update function, thumb image will be updated later. 
	#if thumbs != [] : thumb = thumbs[0].text
	#else :               thumb = ' '

	kor_title_cand = item.xpath('korName')[0].text					# Korean title
	eng_title_cands = item.xpath('engName')						# English title
	if eng_title_cands != [] :
		#eng_title_cand = eng_title_cands[0].text.replace(' ', '')
		eng_title_cand = eng_title_cands[0].text.lower()
	else :			
		org_title_cands = item.xpath('orgName')					# getting original title when english title is not given
		if org_title_cands != [] :
			eng_title_cand = org_title_cands[0].text.lower()
		else :
			eng_title_cand = '?'
	
	kor_score = Util.LevenshteinDistance(media_name, kor_title_cand)		                                # media name is compared with Korean title
	if eng_title_cand != '?' :	eng_score = Util.LevenshteinDistance(media_name, eng_title_cand)	# media name is compared with English title
	else :				eng_score = 100
	
	len_title = 0
	len_media = 0
	leng = 0
	if re.search('[a-zA-Z]+', media_name) and eng_title_cand != '?' :                                 # if media name includes alphabet, then the media name is considered as english title not korean title                          
		score_cand = eng_score		
		#eng_title_cand = unicodedata.normalize('NFKC', eng_title_cand.decode('utf-8')).encode('utf-8')
		len_title = len(eng_title_cand)
		#lang_flag = 'en'
	else :                                                                                   	                                                # if media name do not includes alphabet, then the media name is considered as korean title    
		score_cand = kor_score	
		#kor_title_cand = unicodedata.normalize('NFKC', kor_title_cand.decode('utf-8')).encode('utf-8')
		len_title = len(kor_title_cand)
		#lang_flag ='ko'
	#if kor_score > eng_score : score_cand = eng_score
	#else :                               score_cand = kor_score

	len_media = len(media_name)                              # variable for the length of movie title is required, because searching rate of movie with short titile is low                                  
	if len_title > len_media :                                          # if a movie has longer title, the movie is searched more exactly.
 		leng = len_media                                             # therefore, dependency about the length will be applied 
	else :                            leng = len_title
	
	if score_cand == 0   : score = 99								# if media name is exactly matched, final score is set to the highest value 96 and other factors are not compared
	elif score_cand == 1 : score = 98 - 10*score_cand/leng                        # score is dependant on score_cand and leng
	elif score_cand == 2 : score = 97 - 20*score_cand/leng	
	else : 
		if media_name.find(kor_title_cand) != -1 :					# if media name includes english candidate name, score is set to the high value 96		
			score = 96 - 10*score_cand/leng			
			Log('find kor!')
		elif media_name.find(eng_title_cand) != -1 :					# if media name includes korean candidate name, score is set to the high value 96	
			score = 96 - 15*score_cand/leng			
			Log('find eng!')	
		else :
			#if lang_flag =='en' :		score = score - 25*score_cand/leng                  # if difference between media name and candidate title is large, score is reduced		
			#else :				score = score - 10*score_cand/leng	
			score = score - 25*score_cand/leng	#score = score - 20*score_cand/leng	
		
	#Log('ID=%s, media_name=%s, kor_cand=%s, kor_score=%s, eng_cand=%s, eng_score=%s, score_cand=%s, len=%s, len_title=%s, len_media=%s, final score =%d' %(id, media_name, kor_title_cand, kor_score, eng_title_cand, eng_score, score_cand, leng, len_title, len_media,score))      
	results.Append(MetadataSearchResult(id=id, name=kor_title_cand, year=year, thumb=thumb, lang=lang, score=score))
	results.Sort('score', descending=True)

  def update(self, metadata, media, lang):
    proxy = Proxy.Preview
    #Log('in update ID = %s' % metadata.id)
    url = CINE21_META_URL % metadata.id
    xml = self.GetFixedXML(url)
    
    try :													#title
	metadata.title = xml.xpath('//korName')[0].text
	#Log('metadata.title = %s', metadata.title)
    except :
	pass   

    try :													#year
	metadata.year = int(xml.xpath('//makeYear')[0].text)
	#Log('metadata.year = %d', metadata.year)
    except :
	pass

    try :													# rating
	total = 0
	c_nodes = xml.xpath('//commentList/comment')
	for c_node in c_nodes : total = total + int(c_node.xpath('point')[0].text)	
	if c_nodes != [] :
		c_num = float(xml.xpath('//commentList/size')[0].text) 
		point = float(total) / c_num
		metadata.rating = point
    except :
	pass
 
    try :													# summary
        summary = xml.xpath('//description')[0].text
	summary = summary.replace('<b>', '\n')
	summary = summary.replace('</b>', '!\n')
	summary = summary.replace('<br>', '\n')
	metadata.summary = unicode('<데이터 제공: 시네21> ', 'cp949') + summary
	#Log('metadata.summary = %s', metadata.summary)
  
    except :	
	pass  

    try :													# genres
	metadata.genres.clear()
	all_genres = xml.xpath('//genre')[0].text
	genres = all_genres.split(',')
	#Log('genres = %s' %genres)
	for genre in genres:
		genre = genre[ : -5]
		#Log(' revised genre = %s' %genre)
		metadata.genres.add(genre)        
    except :
	pass    

    try :													# duration
	duration = xml.xpath('//runningTime')[0].text
	duration = duration[ :-1]
	metadata.duration = int(duration)*60*1000   
    except :
        pass
    
    try :													# actors    &     directors   &   writers
        metadata.roles.clear()
	metadata.directors.clear()
	metadata.writers.clear()
	nodes = xml.xpath('//person')
	for node in nodes:
		pRole = node.xpath('personRole')[0].text
		if pRole == '0':
			role = metadata.roles.new()
			role.actor = node.xpath('personName')[0].text
       			
		elif pRole == unicode('감독', 'cp949') :
			metadata.directors.add (node.xpath('personName')[0].text)
       		
		elif pRole == unicode('각본', 'cp949') or pRole == unicode('원작', 'cp949') :
			metadata.writers.add (node.xpath('personName')[0].text)
       		
    except :
	pass

    try :													# art
	images = xml.xpath('//image')
	for img in images :
		image_kind = img.xpath('imageKind')[0].text                                             
		if image_kind == unicode('스틸컷', 'cp949') :                                                		 
			art_url = img.xpath('imageUrl')[0].text
			art = HTTP.Request(art_url)
			metadata.art[art_url] = proxy(art, sort_order = 1)
			break
    except :
	pass
   
    try:
	#images =xml.xpath('//image')					# thumb_poster
	for img in images :
		image_kind = img.xpath('imageKind')[0].text                                             
		if image_kind == unicode('포스터', 'cp949') :                                                		 
			art_url = img.xpath('imageUrl')[0].text
			art = HTTP.Request(art_url)
			metadata.posters[art_url] = proxy(art, sort_order = 1)
			break
    except :
	pass