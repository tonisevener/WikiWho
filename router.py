from flask import Flask, request, abort
from flask_restful import Resource, Api
import requests
from wikiwho import Wikiwho
from utils import iter_rev_tokens
from whoColorHandler import WhoColorHandler
import threading

app = Flask(__name__)
api = Api(app)

cache = {}
isCaching = {}

class ArticleAnalyzer (Resource):
	def analyseHistory(self, page_id, wikiwho):

		params = {'pageids': page_id, 'action': 'query', 'prop': 'revisions',
				  'rvprop': 'content|ids|timestamp|sha1|comment|flags|user|userid',
				  'rvlimit': 'max', 'format': 'json', 'continue': '', 'rvdir': 'newer'}
		if wikiwho is not None:
			if wikiwho.rvcontinue is not None:
				params = {'pageids': page_id, 'action': 'query', 'prop': 'revisions',
				  'rvprop': 'content|ids|timestamp|sha1|comment|flags|user|userid',
				  'rvlimit': 'max', 'format': 'json', 'continue': '', 'rvdir': 'newer', 'rvstartid': wikiwho.rvcontinue}
			else:
				print("shouldn't get here")

			url = 'https://en.wikipedia.org/w/api.php'

			# gets only first 50 revisions of given page
			result = requests.get(url=url, params=params).json()
			if 'error' in result:
				raise Exception('Wikipedia API returned the following error:' + str(result['error']))

			pages = result['query']['pages']
			if "-1" in pages:
				raise Exception('The article ({}) you are trying to request does not exist!'.format(page_id))

			_, page = result['query']['pages'].popitem()
			if 'missing' in page:
				raise Exception('The article ({}) you are trying to request does not exist!'.format(page_id))

			wikiwho.analyse_article(page.get('revisions', []))
			resultContinue = result.get('continue')
			if resultContinue is not None:
				rvContinue = resultContinue.get('rvcontinue')
				if rvContinue is not None:
					wikiwho.rvcontinue = rvContinue.split("|",1)[1]
				else:
					wikiwho.rvcontinue = None
			else:
				wikiwho.rvcontinue = None

			return wikiwho
		else:
			url = 'https://en.wikipedia.org/w/api.php'

			result = requests.get(url=url, params=params).json()
			if 'error' in result:
				raise Exception('Wikipedia API returned the following error:' + str(result['error']))

			pages = result['query']['pages']
			if "-1" in pages:
				raise Exception('The article ({}) you are trying to request does not exist!'.format(page_id))

			_, page = result['query']['pages'].popitem()
			if 'missing' in page:
				raise Exception('The article ({}) you are trying to request does not exist!'.format(page_id))
			
			wikiwho = Wikiwho(page['title'])

			wikiwho.analyse_article(page.get('revisions', []))
			resultContinue = result.get('continue')
			if resultContinue is not None:
				rvContinue = resultContinue.get('rvcontinue')
				if rvContinue is not None:
					wikiwho.rvcontinue = rvContinue.split("|",1)[1]
				else:
					wikiwho.rvcontinue = None
			else:
				wikiwho.rvcontinue = None

			return wikiwho

	def kickoffWhoColor(self, title, revID):
		handler = WhoColorHandler(page_title=title)
		response = handler.handle()
		cache[title] = (revID, response)
		isCaching[title] = False

	def getLatestRevID(self, title):
		#prepare request
		data = {'url': 'https://en.wikipedia.org/w/api.php'}
		params = {'action': 'query', 'prop': 'revisions', 'rvprop': 'ids|timestamp', 'rvlimit': '1', 'format': 'json', 'titles': title, 'rvdir': 'older'}
		data['data'] = params
		#make request
		response = requests.post(**data).json()

		if 'error' in response:
			return None
		pages = response['query']['pages']
		if '-1' in pages:
			return None
		for page_id, page in response['query']['pages'].items():
			namespace = page['ns']
			revisions = page.get('revisions')
			if revisions is None:
				return None
			else:
				return revisions[0]['revid']

	def cachedResponseForTitleAndRevision(self, title, revID):
		if cache.get(title) is not None:
			cachedTuple = cache[title]
			if cachedTuple[0] == revID:
				return cachedTuple[1]
			else:
				return None
		else:
			return None

	def get(self, title):

		latestRevID = self.getLatestRevID(title)
		if latestRevID is None:
			abort(500, 'Failure getting latest revision ID')
		else:
			cachedResponse = self.cachedResponseForTitleAndRevision(title, latestRevID)
			if cachedResponse is not None:
				return cachedResponse
			elif isCaching.get(title):
				abort(500, 'Article is currently caching.')
			else:
				#TODO: if there's some sort of exception on a background thread, be sure to reset isCaching somehow
				isCaching[title] = True
				download_thread = threading.Thread(target=self.kickoffWhoColor, name="Downloader", args=(title,latestRevID,))
				download_thread.start()
				abort(500, 'Article not cached, kicking off caching.')

		# page_id = 47189019

		# wikiwho = self.analyseHistory(page_id, None)
		# while (wikiwho.rvcontinue is not None):
		# 	wikiwho = self.analyseHistory(page_id, wikiwho)

		# l = []
		# for token in iter_rev_tokens(wikiwho.revisions[wikiwho.ordered_revisions[-1]]):
		# 	d = {"str": str(token.value), "o_rev_id": token.origin_rev_id, "token_id": token.token_id}
		# 	l.append(d)
		# return l

api.add_resource(ArticleAnalyzer, '/whocolor/<string:title>/') # Route_1

if __name__ == '__main__':
	app.run('0.0.0.0','3333')