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

def proxy_auth():
    return quote(decrypt('username')) + ':' + quote(decrypt('password'))

class curl:
    def __init__(self, verbose=True):
        self.verbose = verbose 
    def request(self, url, output, content=None, proxy=None, method='GET'):
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        if self.verbose :
            c.setopt(pycurl.VERBOSE, 1)
        c.setopt(pycurl.COOKIEJAR, 'cookies')
        c.setopt(pycurl.COOKIEFILE, 'cookies')
        c.setopt(pycurl.FAILONERROR, 1)

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
        c.close()
        return (body if output == 'body' else dest if output == 'dest' else -1)

def upload(dir_name=None,file_name=None, profile='stage'):
    credential = decrypt('username','uep_admin') + ':' + decrypt('password','uep_admin')
    if profile == 'stage':
        url = 'redacted'
    elif profile == 'prod':
        url = 'redacted'
    else:
        print ("key-in correct enviroment parameters!")
        sys.exit(2)
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.VERBOSE, 0)
    c.setopt(c.FOLLOWLOCATION, 1)
#    c.setopt(c.FAILONERROR, 1)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.USERPWD, credential)
    if dir_name and file_name:
        dir_url = os.path.join(url, dir_name)
        local_file = os.path.join('./media', file_name)
        c.setopt(c.URL, dir_url)
        c.setopt(c.HTTPPOST, [('name','upload_file'),(file_name,(c.FORM_FILE, local_file))])
    else:
        c.setopt(c.URL, url)
        c.setopt(c.HTTPPOST, [('fileset_name',dir_name)])
    c.perform()
    print (buffer.getvalue())
    buffer.close()
    c.close()
    return;

def rename(path='./media', SwVer = 'redacted', videoUrl = 'redacted', profile = 'stage'):
    #session = boto3.Session(profile_name='saml')
    #s3_client = session.client('s3')
    if profile == 'stage':
        s3_url='redacted' % ( SwVer,)
    elif profile == 'prod':
        s3_url='redacted' % ( SwVer,)
    else:
        print ("key-in correct enviroment parameters!")
        sys.exit(2)
    filenames = os.listdir(path)
    for filename in filenames:
        newname = re.sub(r"([^A-Za-z0-9])", r"_", filename.rsplit(".", 1)[0]) + '.' + filename.rsplit(".", 1)[1]
        os.rename(os.path.join(path, filename), os.path.join(path, newname))
        #key='filerepository/application/redacted/drn_%s/' % ( SwVer,) + newname 
        #s3_client.upload_file(os.path.join(path, newname),'envstage-filerepository',key)
    DICT={
            "graphicUrl": None,
            "graphicUrlCable": None,
            "screenShotUrls": None,
            "videoUrl": None 
            }
    LIST=[]
    for filename in os.listdir('./media'):
        LIST.append(s3_url+filename)
    DICT["screenShotUrls"]=LIST
    DICT["videoUrl"]=videoUrl
    DATA = json.dumps(DICT)
    return DATA

if len(sys.argv) != 2:
    print ("key-in correct enviroment parameters!")
    sys.exit(2)
else:
    profile_name = sys.argv[1]


somc_proxy = 'redacted'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
DATA=rename(SwVer=decrypt('SwVer','drn'),videoUrl=decrypt('videoUrl','drn'),profile = profile_name)
LIST=decrypt('SwId','drn').split(',')


for SwId in LIST:
    if profile_name == 'stage':
        DRN_SP='redacted' % ( SwId, decrypt('SwVer','drn'))
    elif profile_name == 'prod':
        DRN_SP='redacted' % ( SwId, decrypt('SwVer','drn'))
    else:
        print ("key-in correct enviroment parameters!")
        sys.exit(2)
    conn = curl(verbose=True)
    saml_request = conn.request(DRN_SP,'dest',proxy=somc_proxy)
    if saml_request == DRN_SP:
        result = conn.request(DRN_SP,'body',proxy=somc_proxy)
    else:
        if os.path.isfile('cookies'):
            os.remove('cookies')
            saml_request = conn.request(DRN_SP,'dest',proxy=somc_proxy)
        saml_response = conn.request(url=saml_request,output='body',content=auth('AUTH'),method='POST',proxy=somc_proxy)
        para3 = {}
        AUTH = {}
        del para3
        del AUTH
        soup = BeautifulSoup(saml_response, 'html.parser')
        for inputtag in soup.find_all('form'):
            if inputtag.get('name') == 'hiddenform' :
                sso = inputtag.get('action')
        for inputtag in soup.find_all('input'):
            if inputtag.get('name') == 'SAMLResponse' :
                assertion = inputtag.get('value')
        result = conn.request(url=sso,output='body',content=urlencode({'SAMLResponse':assertion}),method='POST',proxy=somc_proxy)
    if len(json.loads(result)) != 1:
        print ('Wrong Records in DRN')
        continue
    if profile_name == 'stage':
        MEDIA = 'redacted' % json.loads(result)[0]['releaseNoteId']
    elif profile_name == 'prod':
        MEDIA = 'redacted' % json.loads(result)[0]['releaseNoteId']
    else:
        print ("key-in correct enviroment parameters!")
        sys.exit(2)
    RnId_media = conn.request(url=MEDIA,output='body',method='GET',proxy=somc_proxy)
    if json.loads(RnId_media)["videoUrl"]:
        conn.request(MEDIA,'body',proxy=somc_proxy,method='DELETE')
        conn.request(MEDIA,'body',DATA,somc_proxy,'PUT')
    
    else:
        conn.request(MEDIA,'body',DATA,somc_proxy,'PUT')
    del conn

os.environ['HTTP_PROXY'] = 'redacted' % proxy_auth()
os.environ['HTTPS_PROXY'] = 'redacted' % proxy_auth()

dir_name = 'drn_' + decrypt('SwVer','drn')
upload(dir_name, profile = profile_name)
file_names = os.listdir('./media')
for file_name in file_names:
    upload(dir_name,file_name, profile = profile_name)


#content = MultipartEncoder(fields={'name': 'upload_file', 'filename': ( file_name, open('./media/test_1.png', 'rb'), 'image/png')})
#req = requests.post('redacted', data = {'fileset_name': dir_name}, auth = ('user','password'))
#requests.post('redacted', data = content, headers={'Content-Type': content.content_type}, auth = ('user','password'))
