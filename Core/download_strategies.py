
import re

def default_strategy(self, url):
    resp = self.session.get(url, headers = self.request_header)
    if (resp.status_code is not 200):
        raise Exception("Request returned status code: "+str(resp.status_code))
    return resp

def prepare_datafilehost_response(self,datafilehost_url):
        params = {}
        cookies = {}
        params["file"] = re.search(r"d\/([0-9A-Za-z]*)", datafilehost_url).group(1)
        #params["export"] = "download"
        resp = self.send_request(datafilehost_url)
        for cookie,value in resp.cookies.items():
            if 'PHPSESSID' in cookie:
                cookies['PHPSESSID']=value
        resp = self.send_request("https://drive.google.com/uc", params=params)
            
def prepare_google_response(self, google_url):
    params = {}
    params["id"] = re.search(r"(?:id=|d\/)([a-zA-Z-0-9]*)", google_url).group(1)
    params["export"] = "download"
    resp = self.send_request("https://drive.google.com/uc", params=params)
    for cookie,value in resp.cookies.items():
        if 'download_warning_' in cookie:
            params['confirm']=value
    resp = self.send_request("https://drive.google.com/uc", params=params)
    return resp