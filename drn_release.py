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
import subprocess
import json
import re
#import requests
#from requests_toolbelt.multipart.encoder import MultipartEncoder

class corp_conn:
    def __init__(self, url, payload=None, verbose=False, proxy_url=None, pub_s3_url=None):
        self.url = url
        self.payload = payload
        self.verbose = verbose
        config = configparser.ConfigParser()
        config.read('credential.ini')		
        self.domain_user = base64.b64decode(config['gene']['corpuser']).decode('utf-8').rstrip()
        self.short_user = base64.b64decode(config['gene']['username']).decode('utf-8').rstrip()
        self.password = base64.b64decode(config['gene']['password']).decode('utf-8').rstrip()
        self.token_prefix = base64.b64decode(config['gene']['token_prefix']).decode('utf-8').rstrip()
        self.uep_user = base64.b64decode(config['uep_admin']['username']).decode('utf-8').rstrip()
        self.uep_pwd = base64.b64decode(config['uep_admin']['password']).decode('utf-8').rstrip()
        self.pub_video_url = config['pub']['videoUrl']
        self.pub_swver = config['pub']['SwVer']
        self.uep_folder_made = False
        if pub_s3_url:
            self.pub_s3_url = pub_s3_url + 'drn_{0}'.format(self.pub_swver) + '/'
        self.proxy_url = config['url']['proxy_url']
    def request(self, request_url, method='GET', payload=None):
        self.payload=payload
        self.url=request_url
        conn = pycurl.Curl()
        try:
            json.loads(self.payload)
        except:
            pass
        else:
            conn.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
        buffer = BytesIO()
        conn.setopt(conn.WRITEDATA, buffer)		
        conn.setopt(pycurl.URL, self.url)
        conn.setopt(pycurl.FOLLOWLOCATION, 1)
        if self.verbose :
            conn.setopt(pycurl.VERBOSE, 1)
        conn.setopt(pycurl.COOKIEJAR, 'cookies')
        conn.setopt(pycurl.COOKIEFILE, 'cookies')
        conn.setopt(pycurl.FAILONERROR, 0)
        if self.payload and method == 'UEP_UPLOAD':
            try:
                uep_add_folder_name = 'drn_' + self.pub_swver
            except:
                print ('wrong payload')
                sys.exit(-1)
            if 'file' in self.payload:
                if self.uep_folder_made == False:
                    self.request(method='UEP_UPLOAD')
                    self.uep_folder_made = True
                uep_add_folder_url = os.path.join(self.url, uep_add_folder_name)
                conn.setopt(conn.URL, uep_add_folder_url)
                local_file = os.path.join('./media', self.payload['file'])
                conn.setopt(conn.HTTPPOST, [('name', 'upload_file'), (self.payload['file'], (conn.FORM_FILE, local_file))])
            else:
                conn.setopt(conn.URL, self.url)
                conn.setopt(conn.HTTPPOST, [('fileset_name', uep_add_folder_name)])
            credential = self.uep_user + ':' + self.uep_pwd
            conn.setopt(conn.USERPWD, credential)
        if self.payload and method == 'POST':
            conn.setopt(pycurl.POST, 1)
            conn.setopt(pycurl.POSTFIELDS, self.payload)
        elif self.payload and method == 'PUT':
            conn.setopt(pycurl.CUSTOMREQUEST, 'PUT')
            conn.setopt(pycurl.POSTFIELDS, self.payload)
        elif method == 'DELETE':
            conn.setopt(pycurl.CUSTOMREQUEST, 'DELETE')       
        if self.proxy_url :
            if ':' in self.proxy_url:
                proxy = self.proxy_url.rsplit(':', 1)[0]
                port = int(self.proxy_url.rsplit(':', 1)[1])               
            conn.setopt(pycurl.PROXY, proxy)
            conn.setopt(pycurl.PROXYPORT, port)
            conn.setopt(pycurl.PROXYUSERPWD, "%s:%s" % (self.short_user,self.password))
        conn.perform()
        self.body = buffer.getvalue()
        buffer.close()
        self.destination = conn.getinfo(pycurl.EFFECTIVE_URL)
        self.status_code = conn.getinfo(pycurl.HTTP_CODE)
        conn.close()
        print (self.destination,self.status_code,self.body.decode('utf-8'))
    def get_value_from_credential(self, index, section):
        config = configparser.ConfigParser()
        config.read('credential.ini')
        if section=='gene' or section=='uep_admin':
            return base64.b64decode(config[section][index]).decode('utf-8').rstrip()
        else:
            return config[section][index].rstrip()
    def gen_payload(self, type):
        if type == 'TOKEN':
            token_pincode = getpass.getpass()
            token = self.token_prefix + token_pincode
            self.payload=urlencode({
                'username': self.short_user,
                'password': token,
                'vhost': 'standard'
                })
        elif type == 'AUTH':		
            self.payload=urlencode({
                'UserName': self.domain_user,
                'Password': self.password,
                'AuthMethod': 'FormsAuthentication'
                })
        elif type == 'PUB':
            #special characater replacement and concatenate with url
            urls=list()
            filenames = os.listdir('./media')
            for filename in filenames:
                new_name = re.sub(r"([^A-Za-z0-9])", r"_", filename.rsplit(".", 1)[0]) + '.' + filename.rsplit(".", 1)[1]
                os.rename(os.path.join(path, filename), os.path.join(path, new_name))
                urls.append(self.pub_s3_url + new_name)
            skeleton={
                "graphicUrl": None,
                "graphicUrlCable": None,
                "screenShotUrls": None,
                "videoUrl": None 
            }
            skeleton["screenShotUrls"]=urls
            skeleton["videoUrl"]=self.pub_video_url
            self.payload = json.dumps(skeleton)
    def saml_resp(self):
        self.request(url=self.url)
        if self.destination != self.url:			
            if self.destination == 'https://fs.[redacted].com/my.policy':
                if os.path.isfile('cookies'):
                    os.remove('cookies')
                    self.request(url=self.url)
                self.gen_payload('TOKEN')
                self.request(self.destination, 'POST', self.payload)
                self.gen_payload('AUTH')
                self.request(self.destination, 'POST', self.payload)
            else:
                self.gen_payload('AUTH')
                self.request(self.destination, 'POST', self.payload)
            soup = BeautifulSoup(self.body, 'html.parser')
            for inputtag in soup.find_all('form'):
                if inputtag.get('name') == 'hiddenform' :
                    saml_endpoint_url = inputtag.get('action')
            for inputtag in soup.find_all('input'):
                if inputtag.get('name') == 'SAMLResponse' :
                    assertion = inputtag.get('value')
            self.request(saml_endpoint_url, method='POST', payload=urlencode({'SAMLResponse':assertion}))	
def pub():
    config = configparser.ConfigParser()
    config.read('credential.ini')
    pub_swid_lst=config['pub']['SwId'].spilit(',')
    pub_swver=config['pub']['SwVer']
    for swid in pub_swid_lst:
        rn_url = config['url']['get_rn_id'] % ( swid, pub_swver )
        uep_s3_url= config['url']['uep_s3']
        get_rn_id = corp_conn(rn_url, verbose=False)
        rn_media_url = config['url']['put_media_data'] % (json.loads(get_rn_id.saml_resp())[0]['releaseNoteId'],)
        put_rn_info = corp_conn(rn_media_url, verbose=False, pub_s3_url = uep_s3_url)
        put_rn_info.gen_payload(type='DRN')
        put_rn_info.request(method='PUT')
    uep_url = config['url']['uep_url']
    put_file_from_uep_admin = corp_conn(uep_url, verbose=False)
    for local_file in os.listdir('./media'):
        put_file_from_uep_admin.request(method='UEP_UPLOAD', payload={'file': local_file})

def release():
    config = configparser.ConfigParser()
    config.read('credential.ini')
    payload=json.dumps({
        "published":True,
        "targetSwId":config['release']['targetSwId'],
        "targetSwVer":config['release']['targetSwVer'],
        "targetCdfId":config['release']['targetCdfId'],
        "targetCdfRev":config['release']['targetCdfRev']
        }) 
    psql_credential={		
            'password':base64.b64decode(config['drn_db']['password']).decode('utf-8').rstrip(), 
            'port':5411, 
            'user': base64.b64decode(config['drn_db']['user']).decode('utf-8').rstrip(), 
            'db_name':base64.b64decode(config['drn_db']['db_name']).decode('utf-8').rstrip(),
            'endpoint':config['drn_db']['endpoint']
            }
    release_note_id=1927
    url=config['url']['releases_url'] % release_note_id
    
    print (subprocess.check_output('ssh -f -o ExitOnForwardFailure=yes {5} sleep 10; echo "SELECT * FROM public.release_note WHERE id = \"{4}\"; UPDATE public.release_note SET type = \'OPERATOR\' WHERE id = \"{4}\"; SELECT * FROM public.release_note WHERE id = \"{4}\";"|PGPASSWORD="{0}" psql.exe --host=localhost --port="{1}" --username="{2}" --dbname="{3}"'.format(psql_credential['password'], psql_credential['port'], psql_credential['user'], psql_credential['db_name'], release_note_id, psql_credential['endpoint']), shell=True).decode("utf-8"))
    gene = corp_conn(url, verbose=False)
    gene.saml_resp()
    gene.request(gene.url, 'POST', payload)
    gene.saml_resp()
def unpub():
    config = configparser.ConfigParser()
    config.read('credential.ini')
    SwId=config['unpub']['SwId'].spilit(',')
    types = ['updates', 'fileupload']
    envs = ['s1test-apklive', 's1test-apktest', 'pcm-apklive', 's1live-apklive']
    grps = ['user', 'userdebug', 'eng']
    urls = []
    for i in range(0, len(types)):
        for j in range(0, len(envs)):
            for k in range(0, len(grps)):
                for l in range(0, len(SwId)):
                        urls.append(config['url']['uep_delete'] % (types[i], envs[j], grps[k], SwId[l]))
    for url in urls:
        delete_file = corp_conn(url, verbose=False)
        delete_file.saml_resp()
        if delete.status_code == '200':
            delete_file.request(method='DELETE')
        elif delete.status_code == '404':
            print ('file not found')
            continue
        else:
            print ('unexpect error')
if __name__ == '__main__':
    release()
