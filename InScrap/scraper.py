import sys
import getopt
from data.config import *

class Session:
	index = 1
	def __init__(self, login, password, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36", use_tor=False):
		self.id = Session.index
		Session.index += 1
		self.alive = True
		self.check_url = 'https://i.instagram.com/api/v1/media/45/comments/'
		self.login_url = 'https://www.instagram.com/accounts/login/'
		self.authorize_url = 'https://www.instagram.com/accounts/login/ajax/'
		self.post_data_url = "https://i.instagram.com/api/v1/media/{}/comments/"
		self.user_agent = user_agent
		self.session_name = login
		self.auth = {'username': login, 'password': password}
		self.headers = {
			'referer': "https://www.instagram.com/accounts/login/",
			'user-agent': self.user_agent,
		}
		self.update_proxies()
		self.proxy = self.proxies if use_tor else ""
		self.session = requests.Session()
		self.check_connection()
		self.__authorize()

	def check_connection(self):
		try:
			self.session.get(self.check_url, proxies=self.proxy)
		except requests.exceptions.ConnectionError:
			self.err('Can\'t connect to instagram!')
			quit(0)

	def log(self, *text, end="\n\r"):
		if(end=="\r"):
			print(" "*(os.get_terminal_size()[0]-1), end='\r')
		print(f"Session{self.id}: {' '.join(text)}", end=end)

	def warn(self, *text, end="\n\r"):
		if(end=="\r"):
			print(" "*(os.get_terminal_size()[0]-1), end='\r')
		print(f"Session{self.id}: {Fore.YELLOW}{' '.join(text)}", end=end)

	def err(self, *text, end="\n\r"):
		if(end=="\r"):
			print(" "*(os.get_terminal_size()[0]-1), end='\r')
		print(f"Session{self.id}: {Fore.RED}{' '.join(text)}", end=end)

	def succ(self, *text, end="\n\r"):
		if(end=="\r"):
			print(" "*(os.get_terminal_size()[0]-1), end='\r')
		print(f"Session{self.id}: {Fore.GREEN}{' '.join(text)}", end=end)

	def update_proxies(self):
		self.proxies = {
			'http': f'socks5://{random.randint(0,99999999)}qe:tor@127.0.0.1:9150',
			'https': f'socks5://{random.randint(0,99999999)}qe:tor@127.0.0.1:9150',
		}

	def __login(self):
		self.log('logging in...', end="\r")
		payload = {
			'username': self.auth['username'],
			'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{datetime.now().timestamp()}:{self.auth['password']}",
			'queryParams': {},
			'optIntoOneTap': 'false'
		}
		req = self.session.get(self.login_url, proxies=self.proxy)
		self.validate_request(req, initial=True)
		self.headers['x-csrftoken'] = re.findall(r"csrf_token\":\"(.*?)\"", req.text)[0]
		req = self.session.post(self.authorize_url, data=payload, headers=self.headers, proxies=self.proxy)
		self.validate_request(req)
		req = self.session.get(self.check_url, proxies=self.proxy)
		if(req.url != self.authorize_url):
			self.err('account is dead')
			self.alive = False
			return
		if(not req.json()['authenticated']):
			raise RuntimeError('wrong authentication data', req.status_code, req.text, self.auth)
		self.succ('logged in', end="\r")
		self.__save_session()

	def __save_session(self):
		with open(f'{SESSIONS_DIR}{self.session_name}.session', 'wb') as f:
			pickle.dump(self.session, f)
		self.succ('session saved', end="\r")

	def __restore_session(self):
		self.log(f'restoring {self.session_name}...', end="\r")
		with open(f'{SESSIONS_DIR}{self.session_name}.session', 'rb') as f:
			self.session = pickle.load(f)
		req = self.session.get(self.check_url, proxies=self.proxy)
		self.validate_request(req)
		self.succ('session restored', end="\r")

	def __authorize(self):
		try:
			self.__restore_session()
		except:
			self.warn('unable to restore session', end="\r")
			self.__login()

	def __get_post_data(self, post_id, min_id = None, queries = 0, counter=0, sr=None):
		start_time = time.time()
		queries+=1
		next_data = {}
		nextneed = False
		headers= {
				'origin': 'https://www.instagram.com',
				'referer': 'https://www.instagram.com/',
				'user-agent': self.user_agent,
				'x-ig-app-id': '936619743392459',
				"x-asbd-id": "198387",
				"x-ig-www-claim": "0",
		}
		url = self.post_data_url.format(post_id)
		url += "?min_id="+min_id if min_id else ""
		req = self.session.get(url, headers=headers, proxies=self.proxy)
		sr(queries)
		self.validate_request(req)
		try:
			post_data = req.json()
		except:
			self.log(req.text[:250], '...')
			return {'comments':[]}, queries, True, counter
		end_time = time.time()
		counter+=len(post_data['comments'])
		self.log(f"collected {counter}/{post_data['comment_count']} +{len(post_data['comments'])} ({queries})", end='\r')
		if('next_min_id' in post_data):
			if(queries<SCRAP_LIMIT):
				next_data, queries, nextneed, c = self.__get_post_data(post_id, min_id=post_data['next_min_id'], queries=queries, counter=counter, sr=sr)
				counter = c
				post_data['comments'].extend(next_data['comments'])
		else:
			return post_data, queries, True, counter
		return post_data, queries, nextneed, counter

	def __shortcode_to_id(self, code):
		id_ = 0;
		alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
		for i in code:
			id_ = (id_ * 64) + alphabet.find(i);
		return id_

	def get_post(self, post_url, min_id = None, q=0,c=0,sr=None):
		headers= {
				'origin': 'https://www.instagram.com',
				'referer': 'https://www.instagram.com/',
				'user-agent': self.user_agent,
		}
		key = post_url.split('/')[-1]
		post_id = self.__shortcode_to_id(key)
		post_data, queries, nextneed, counter = self.__get_post_data(post_id, min_id=min_id, queries=q, counter=c, sr=sr)
		return post_data, queries, nextneed, counter

	def get_comments(self, post, time=0):
		comments = []
		for comment in post['comments']:
			if(comment['created_at_utc'] > time):
				comments.append([comment['created_at_utc'], comment['user']['username'], comment['text'], comment['comment_like_count'] if 'comment_like_count' in comment else 0])
				if 'preview_child_comments' in comment:
					for subcomment in comment['preview_child_comments']:
						comments.append([subcomment['created_at_utc'], subcomment['user']['username'], subcomment['text'], subcomment['comment_like_count'] if 'comment_like_count' in comment else 0])
		return comments

	# def comments_to_csv(self, url, time=0):
	# 	print(url)
	# 	post = s.get_post(url)
	# 	comments = s.get_comments(post, time=time)

	# 	with open(f"output/{url.rsplit('/', 1)[-1]}.csv", "w", encoding="utf-8", newline='\n') as f:
	# 		writer = csv.writer(f, delimiter='	')
	# 		writer.writerows(comments)
	# 	self.log("collected from", url, len(comments))

	def collect(self, url, time=0, min_id = None, q=0, c=0, sr=None):
		if(not self.alive):
			return [], min_id, q, True, c
		self.log(url)
		post, queries, nextneed, counter = self.get_post(url, min_id=min_id, q=q, c=c, sr=sr)
		comments = self.get_comments(post, time=time)
		if('next_min_id' in post):
			min_id = post['next_min_id']
		return comments, min_id, queries, nextneed, counter

	def validate_request(self, req, initial=False):
		if(req.status_code == 429):
			raise RuntimeError('too many requests', req.status_code, req.text[:600])
		# if(req.json()['message']=='checkpoint_required'):
		# 	raise RuntimeError('account is dead!', req.status_code, req.text[:600])
		elif(req.status_code == 400):
			# if('message' in req.json()):
			# 	if(req.json()['message']=='checkpoint_required'):
			# 		r = requests.get(req.json()['checpoint_url'], proxies=self.proxies)
			# 		print
			raise RuntimeError('incorrect request', req.status_code, req.text[:600])
		elif(req.status_code == 405):
			raise RuntimeError('method not allowed', req.status_code, req.text[:600])
		elif(req.status_code == 403):
			raise RuntimeError('forbidden', req.status_code, req.text[:600])
		elif(req.status_code != 200):
			raise RuntimeError('unknown error', req.status_code, req.text[:600])
		elif('not-logged-in' in req.text and not initial):
			self.warn('session is out', end="\r")
			self.__login()


class Worker:
	def __init__(self, auth_data):
		self.sessions = []
		self.authorize(auth_data)
		self.validate()
		self.get_target()

	def validate(self):
		if(len(self.sessions)==0):
			print('Sessions are over')
			quit(0)

	def get_target(self):
		try:
			with open(f'{CACHE_DIR}last_target', 'r') as f:
				self.target, self.queries, fp = map(int,f.read().split())
				if(fp != self.footprint):
					raise RuntimeError('footprint doesn\'t match')
		except:
			self.target, self.queries = 0, 0
		print('starting from', self.queries, self.sessions[self.target].session_name)

	def save_target(self, q):
		with open(f'{CACHE_DIR}last_target', 'w') as f:
			f.write(f'{self.target} {q} {self.footprint}')

	def authorize(self, auth_data):
		for i in auth_data:
			s = Session(i['login'], i['password'])
			if(s.alive):
				self.sessions.append(s)
		self.footprint = str(self.sessions)

	def next(self):
		if(self.target<len(self.sessions)-1):
			self.target+=1
		if(self.target==len(self.sessions)-1):
			self.target = 0
		# self.save_target()

	def comments_to_csv(self, url, comments):
		with open(f"{OUTPUT_DIR}{url.rsplit('/', 1)[-1]}.csv", "w", encoding="utf-8", newline='\n') as f:
			writer = csv.writer(f, delimiter=',')
			writer.writerows(comments)

	def save_comments(self, post):
		with open(f'{CACHE_DIR}comments', 'wb') as f:
			pickle.dump([self.comments, post], f)

	def load_comments(self, post):
		comments = []
		counter = 0
		try:
			with open(f'{CACHE_DIR}comments', 'rb') as f:
				c, p = pickle.load(f)
				if(p==post):
					comments = c
					counter = len(self.c)
		except:
			pass
		return comments, counter

	def parse_post_comments(self, post, time):
		min_id=None
		comments, counter = self.load_comments(post)
		while True:
			session = self.sessions[self.target]
			try:
				c, min_id, self.queries, nextneed, counter = session.collect(post, time=time, min_id=min_id, q=self.queries, c = counter, sr=self.save_target)
			except RuntimeError as e:
				session.log(e, session.session_name)
				self.next()
				continue
			if(self.queries>=SCRAP_LIMIT):
				self.queries=0
				self.next()
			comments.extend(c)
			self.save_comments(post)
			if(nextneed):
				print('\ncollected', len(comments), 'comments')
				return comments

	def parse_posts_from_csv_to_sqlite(self, posts, db_path):
		with open(posts) as f:
			data = csv.reader(f)
			for i in data:
				comments = self.parse_post_comments(i[0], int(i[1]))
				self.comments_to_csv(i[0], comments)
def boot():
	import requests, pickle, random, re, csv, threading, time, os, json
	from pyfiglet import Figlet
	from datetime import datetime
	from colorama import init, Fore, Back, Style
	init(autoreset=True)

def execute(args):
	help_text = 'scraper.py [-i/-o/-h] [run/comments_csv_sqlite]\n\tcomments_csv_sqlite\n\t\t-i --input <inputPath>\n\t\t-o --output <outputPath>\n\t\t(runs inscrap with specified data)\n\trun (runs inscrap with data from config file)'
	try:
		opts, args = getopt.getopt(args,"hi:o:",["input=", 'output='])
	except getopt.GetoptError:
		print(help_text)
		sys.exit(2)
	if('run' in args):
		custom_fig = Figlet()
		print(custom_fig.renderText(f'InScrap v{APP_VERSION}'))
		authdata = open(f'{DATA_DIR}authdata.json', 'r').read()
		authdata = json.loads(authdata)
		worker = Worker(authdata)
		worker.parse_posts_from_csv_to_sqlite(f'{DATA_DIR}/post.csv', f'{OUTPUT_DIR}/comments.sqlite')
	else:
		for opt, arg in opts:
			if opt in ('-h', '--help'):
				print(help_text)
				sys.exit()
			elif opt in ("-i", "--input"):
				input = arg
			elif opt in ("-o", "--output"):
				output = arg

if (__name__ == '__main__'):
	args = sys.argv[1:]
	execute(args)