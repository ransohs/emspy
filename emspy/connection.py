from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import object
import json, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse, ssl, sys, io, gzip
from numbers import Number
import pprint as pp
from . import common



class Connection(object):
	'''
	Object for connection to EMS API
	'''
	def __init__(self, user=None, pwd=None, proxies=None, verbose=False, ignore_ssl_errors=False, server="prod", server_url=None):

		self.__user 		= user
		self.__pwd  		= pwd
		self.__proxies      = proxies
		self.__ntrials      = 0
		self.__uri_root     = None
		self.__ignore_ssl_errors = ignore_ssl_errors
		self.token 			= None
		self.token_type 	= None

		# We assign the uri root to a member variable up front, and use that everywhere to
		# simplify. In order to use an alternate uri root, it must be specified in the constructor.
		if server_url is not None:
			self.__uri_root = server_url
		else:
			self.__uri_root = common.uri_root[server]

		if (user is not None) and (pwd is not None):
			self.connect(user, pwd, proxies, verbose)
		else:
			print("An empty connection is instantiated because credentials are not provided.\n")



	def connect(self, user, pwd, proxies=None, verbose=False):
		'''
		Connect to EMS system using given credentials.
		'''
		if proxies is not None:
			proxy_handler = urllib.request.ProxyHandler(proxies)
			opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPHandler)
			urllib.request.install_opener(opener)	

		headers = {'Content-Type':'application/x-www-form-urlencoded', 'User-Agent':common.user_agent}
		data   = {'grant_type': 'password', 'username': user, 'password': pwd}

		resp_h, content = self.request(
			rtype="POST", uri_keys=('sys','auth'), data=data, 
			headers = headers, proxies=proxies, verbose=verbose
			)

		# Add error handling --

		# Get the token
		self.token      = content['access_token']
		self.token_type = content['token_type']
		return resp_h, content


	def reconnect(self, verbose = False):

		if self.__ntrials >= 3:
			sys.exit("Stop trying to reconnect EMS API after %d trials" % self.__ntrials)

		self.__ntrials +=1
		return self.connect(self.__user, self.__pwd, self.__proxies, verbose)


	def request(self,
			rtype="GET", uri=None, uri_keys=None, uri_args=None, 
			headers=None, body=None, data=None, jsondata=None, proxies=None, 
			verbose=False
		):

		# If no custom headers are given, use our own
		if headers is None: 
			headers = {'Authorization': ' '.join([self.token_type, self.token]), 'Accept-Encoding': 'gzip', 'User-Agent': common.user_agent }

		# If uri_keys are given, find the uri from the uris dictionary
		if uri_keys is not None:
			uri    = self.__uri_root + common.uris[uri_keys[0]][uri_keys[1]]

		# Provide the input to the request
		if uri_args is not None:
			# uri    = uri % uri_args
			# Unencoded url does not work all of sudden...
			
			# encode_args = lambda x: urllib.parse.quote(x) if type(x) in (str, unicode) else x
			# if type(uri_args) in (list, tuple):
			# 	uri = uri % tuple(map(encode_args, uri_args))
			# else:
			# 	uri = uri % encode_args(uri_args)
			
			if type(uri_args) not in (list, tuple):
				uri_args = [uri_args]
				
			uri_args = [x if isinstance(x, Number) else urllib.parse.quote(x) \
						for x in uri_args]
			uri = uri % tuple(uri_args)
			
		# Append query to the uri if body is given
		if body is not None:
			uri    = uri + "?" + urllib.parse.urlencode(body)

		# Encode the data
		if data is not None:
			data 	= urllib.parse.urlencode(data).encode('utf-8')

		if jsondata is not None:
			headers['Content-Type'] = 'application/json'
			data = json.dumps(jsondata).encode('utf-8')

		# uri = uri.encode('utf-8')
		req = urllib.request.Request(uri, data=data, headers=headers)
		try:
			resp = self.__send_request(req)
			statcode = resp.getcode()
			if statcode!=200:
				print("Http status code: %d" % statcode)
				verbose = True
		except:
			(eType, eValue, eTrace) = sys.exc_info()
			if eType is ssl.CertificateError:
				print("A certificate verification error occured for the request to '%s'. Certificate verification is required by default, but can be disabled by using the ignore_ssl_errors argument for the Connection constructor." % uri )
				raise

			print("Trying to reconnect the EMS API.")
			self.reconnect()
			print("Done.")
			resp = self.__send_request(req)
		resp_h   = resp.getheaders()

		# If the response is compressed, decompress it.
		if resp.info().get('Content-Encoding') == 'gzip':
			buffer = io.BytesIO(resp.read())
			file = gzip.GzipFile(fileobj=buffer)
			content = json.loads(file.read())
		else:
			content = json.loads(resp.read())
			
		if verbose:
			print("URL: %s" % resp.geturl())
			pp.pprint(resp_h)
			pp.pprint(content)

		return resp_h, content


	def __send_request(self, req):
		"""Sends the request and returns the response, optionally ignoring ssl errors."""

		# Normally you do NOT want to ignore SSL errors, but this is
		# sometimes necessary on beta API endpoints without a proper cert.
		return urllib.request.urlopen(req,
							   context = ssl._create_unverified_context() if self.__ignore_ssl_errors else None)


def print_resp(resp):
	
	for r in resp:
		pp.pprint(r)
