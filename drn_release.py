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
        try:
            self.proxy_url = config['url']['proxy_url']
        except:
            self.proxy_url = False
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
        if self.payload and method == 'UEP_ADD':
            credential = self.uep_user + ':' + self.uep_pwd
            conn.setopt(conn.USERPWD, credential)
            conn.setopt(pycurl.HTTPHEADER, ['Content-Type: application/xml'])
            conn.setopt(pycurl.POST, 1)
            conn.setopt(pycurl.POSTFIELDS, self.payload)
        if self.payload and method == 'UEP_PACK':
            credential = self.uep_user + ':' + self.uep_pwd
            conn.setopt(conn.USERPWD, credential)
            conn.setopt(conn.HTTPPOST, [('name', 'upload_file'), ('file', (conn.FORM_FILE, self.payload))])
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
        return self.body.decode('utf-8')
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
        self.request(request_url=self.url)
        if self.destination != self.url:			
            if self.destination == 'https://fs.[redacted].com/my.policy':
                if os.path.isfile('cookies'):
                    os.remove('cookies')
                    self.request(request_url=self.url)
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
def add(file_name, sim_id_lst_pattern):
    config = configparser.ConfigParser()
    config.read('credential.ini')
    #file_name = config['add']['file']
    app_sw_id = config['add']['app_sw_id']
    sim_id_lst = sim_id_lst_pattern.split(',')
    info = list(file_name.split('_'))
    model_id = info[0]
    cdf_id = info[1] 
    src_cdf_rev = list(info[2].split('-'))[0]
    cdf_rev = list(info[2].split('-'))[1]
    src_ver = list(info[5].split('-'))[0]
    target_ver = list(info[5].split('-'))[1]
    gen_type = info[4]
    apk_type = info[6].lower()
    user_type = info[7]
    red_brown = { 'Brown': 'test', 'Red': 'live' }
    s1_type = red_brown[info[8].split('.')[0]]
    uid = config['add']['uid']


    file_path = '/cygdrive/c/Users/{1}/Desktop/{0}'.format(file_name, uid)
    dl_url =   config['add']['uep_dl_url'] 
    api_url = config['add']['uep_api_url']
    up_url = config['add']['up_url']

    rom_url = '{0}/s1{5}-apk{3}/{4}/{1}/{2}'.format(dl_url, model_id, file_name, apk_type, user_type, s1_type)
    query_url = '{0}/s1{4}-apk{2}/{3}/{1}/metadataaccessors'.format(api_url, model_id, apk_type, user_type, s1_type)
    url = '{0}/s1{4}-apk{2}/{3}/{1}/metadata'.format(api_url, model_id, apk_type, user_type, s1_type)
    upload_url = '{0}/s1{4}-apk{2}/{3}/{1}'.format(up_url, model_id, apk_type, user_type, s1_type)
      
    import os
    file_size = os.path.getsize(file_path)
    sha256sum = subprocess.check_output("sha256sum %s|awk '{print $1}'" % file_path, shell=True).decode("utf-8").rstrip('\n')

    payload = '<MetaData><TargetSoftwareRevision>{0}</TargetSoftwareRevision><TargetCustomRevision>{1}</TargetCustomRevision><TargetFileSystemVariant>{5}</TargetFileSystemVariant><TargetFileSystemRevision>{0}</TargetFileSystemRevision><DownloadURL>{2}</DownloadURL><Size>{3}</Size><Hash>{4}</Hash></MetaData>'.format(target_ver, cdf_rev, rom_url, file_size, sha256sum, gen_type)
    gene = corp_conn(url, verbose=False)
    gene.saml_resp()
    resp_xml = gene.request(gene.url, 'UEP_ADD', payload)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp_xml)
    uep_id = root.find('ID').text
    query_url = query_url + '/' + uep_id
    query_gene = corp_conn(query_url, verbose=False)
    query_gene.saml_resp()
    for sim_id in sim_id_lst:
        if sim_id == '':
            payload = '<AccessPath>ota:{0}:{1}:{2}:{3}</AccessPath>'.format(app_sw_id, src_ver, cdf_id, src_cdf_rev) 
        else:
            payload = '<AccessPath>ota:{0}:{1}:{2}:{3}:*:*:*:*:{4}</AccessPath>'.format(app_sw_id, src_ver, cdf_id, src_cdf_rev, sim_id)
    query_gene.request(query_gene.url, 'UEP_ADD', payload)

    pack_up = corp_conn(upload_url, verbose=True)
    pack_up.saml_resp()
    pack_up.request(pack_up.url, 'UEP_PACK' , file_path)

    get_sha256 = pack_up.request(upload_url + '/' + file_name)
    if sha256sum == get_sha256:
        print('finished')
    else:
        print("sha256 hash didn't match")
def multi_add():
    import configparser
    config = configparser.ConfigParser()
    config.read('credential.ini')
    for file_name, sim_id_lst_pattern in  zip(config ['add']['file'].split(','), config['add']['sim_id'].split(';')):
        add(file_name, sim_id_lst_pattern)

if __name__ == '__main__':
    multi_add()

