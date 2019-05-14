#!/usr/bin/python3
import os, sys
import pycurl
from io import BytesIO
import configparser
import base64
from urllib.parse import urlencode
from urllib.parse import quote
import getpass
from bs4 import BeautifulSoup
import base64
import json
import re
#import requests
#from requests_toolbelt.multipart.encoder import MultipartEncoder
#decode base64 e.g.  decrypt('password','uep_admin')
def decrypt(index,section='gene'):
    #with open('cert.64', 'r') as s:
        #my_profile = s.readlines()
    #return base64.b64decode(my_profile[index]).decode('utf-8').rstrip()
    config = configparser.ConfigParser()
    config.read('credential.ini')
    if section=='gene' or section=='uep_admin':
        return base64.b64decode(config[section][index]).decode('utf-8').rstrip()
    else:
        return config[section][index].rstrip()
#token authenticationg / basic authentication (username / passwd)
def auth(credential='AUTH'):
    if credential == 'TOKEN':
        passwd = getpass.getpass()
        passwd = decrypt('token_prefix') + passwd
        para={
                'username': decrypt('username'),
                'password': passwd,
                'vhost': 'standard'
                }
    elif credential == 'AUTH':
        para={
                'UserName': decrypt('corpuser'),
                'Password': decrypt('password'),
                'AuthMethod': 'FormsAuthentication'
                }
    return urlencode(para)
#proxy auth with basic authentication 
def proxy_auth():
    return quote(decrypt('username')) + ':' + quote(decrypt('password'))

class curl:
    def __init__(self, verbose=False):
        self.verbose = verbose 
    def request(self, url, output, content=None, proxy=None, method='GET'):
        buffer = BytesIO()
        credential = decrypt('username','uep_admin') + ':' + decrypt('password','uep_admin')
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        c.setopt(c.USERPWD, credential)
        if self.verbose :
            c.setopt(pycurl.VERBOSE, 1)
        c.setopt(pycurl.COOKIEJAR, 'cookies')
        c.setopt(pycurl.COOKIEFILE, 'cookies')
#        c.setopt(pycurl.FAILONERROR, 1)

        if content and method == 'POST':
            c.setopt(pycurl.POST, 1)
            c.setopt(pycurl.POSTFIELDS, content)
        if content and method == 'PUT':
            c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
            c.setopt(pycurl.CUSTOMREQUEST, 'PUT')
            c.setopt(pycurl.POSTFIELDS, content)
        if method == 'DELETE':
            c.setopt(pycurl.CUSTOMREQUEST, 'DELETE')
        
        if proxy :
            port = 8080
            if ':' in proxy:
                port = int(proxy.rsplit(':', 1)[1])
                proxy = proxy.rsplit(':', 1)[0]
            c.setopt(pycurl.PROXY, proxy)
            c.setopt(pycurl.PROXYPORT, port)
            c.setopt(pycurl.PROXYUSERPWD, "%s:%s" % (decrypt('username'),decrypt('password')))            
        c.setopt(c.WRITEDATA, buffer)
        c.perform()
        body = buffer.getvalue()
        buffer.close()
        dest = c.getinfo(pycurl.EFFECTIVE_URL)
        code = c.getinfo(pycurl.RESPONSE_CODE)
        c.close()
        return (body if output == 'body' else dest if output == 'dest' else code if output == 'code' else -1)
def unpub(url, somc_proxy = None):
    conn = curl(verbose = False)
    if conn.request(url, 'code', proxy=somc_proxy, method='GET') == 200:
        return conn.request(url, 'body', proxy=somc_proxy, method='DELETE')
    elif  conn.request(url, 'code', proxy=somc_proxy, method='GET') == 404:
        return 'folder not found!' 
    else:
        return 'unexpected error!'
if len(sys.argv) !=2:
    print ("please key-in correct parameter!")
    sys.exit(2)
else:
    profile_name = sys.argv[1]
import configparser
config = configparser.ConfigParser()
config.read('credential.ini')
SwId = config['unpub']['SwId'].split(',')

types = ['updates', 'fileupload']
envs = ['redacted']
grps = ['redacted']
urls = []
somc = 'http://redacted:8080'
for i in range(0, len(types)):
    for j in range(0, len(envs)):
        for k in range(0, len(grps)):
            for l in range(0, len(SwId)):
                if profile_name == 'stage':
                    urls.append('https:///services/%s/firmware/%s/%s/%s/' % (types[i], envs[j], grps[k], SwId[l]))
                elif profile_name == 'prod':
                    urls.append('https:///services/%s/firmware/%s/%s/%s/' % (types[i], envs[j], grps[k], SwId[l]))
                elif profile_name == 'test':
                    urls.append('https:///services/%s/firmware/%s/%s/%s/' % (types[i], envs[j], grps[k], SwId[l]))
                else:
                    print ("please key-in correct parameter!")
                    sys.exit(2)



for url in urls:
    print(url,unpub(url))
