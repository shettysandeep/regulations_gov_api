# -*- coding: utf-8 -*-

"""
__author__: Sandeep Shetty
__date__: October 21, 2021

Code to extract comments (and  attachments)  from Regulations.gov API

"""

from datetime import datetime
import json, os
import requests
import ast, time
import pandas as pd

class RegCommentAPI:
    """Extract Comments on Docket from Regulation.gov"""

    def __init__(self, api_file, page_size = 250):
        self._url = ''               # Base url with the endpoint for Dockets
        self._docnum = ''            # Docket ID, e.g. CMS-2011-0142
        self._api = ''               # If you want to supply the API directly
        self.api_file = api_file     # File-path of the API
        self._comment_url = ''       # Base url with the endpoint for Comments
        self.page_size = page_size   # Number of comments per page

    @property
    def url(self):
        return self._url

    @property
    def docnum(self):
        return self._docnum

    @property
    def api(self):
        return self._api

    @property
    def comment_url(self):
        return self._comment_url

    @url.setter
    def url(self, url):
        self._url = url

    @docnum.setter
    def docnum(self, docket_num):
        self._docnum=docket_num

    @comment_url.setter
    def comment_url(self, comment_endpoint):
        self._comment_url = comment_endpoint

    def collect_api(self):
        """Collect the API provided directly or via a file (without extension)"""
        if self._api:
            return self._api
        else:
            with open(self.api_file) as f:
                api=f.read()
            return api

    def get_rate_limit(self, url):
        """Get starting X-Rate-Limit"""
        print(url)
        content = requests.get(url) #, rate_limit)
        rate_limit=content.headers['X-RateLimit-Remaining']
        return rate_limit

    def docket_url_maker(self, page_num=1):
        """Create a query-tailored complete API URL"""
        api = self.collect_api()
        url_name = self._url+self._docnum+\
                   '&page[number]='+str(page_num)+\
                   '&page[size]='+str(self.page_size)+\
                   '&api_key='+api
        return str(url_name)

    def make_request(self, url, rate_limit):
        '''API request, collect results'''
        if (int(rate_limit)-2) != 0:
            request_data = requests.get(url)
            rate_limit = request_data.headers['X-RateLimit-Remaining'] #self.get_rate_limit(url)
            print(f"make_request {rate_limit}")
        else:
            print("Come back in an hour. Time is {}".format(time.ctime()))
            seconds_wait = 60*60 # datetime objects resulting
            time.sleep(seconds_wait)
            rate_limit = self.get_rate_limit(url)
            request_data = self.make_request(self, url, rate_limit)
        return request_data, rate_limit

    def execute_request(self, url, rate_limit):
        """Extract all comments"""
        content, rl = self.make_request(url1, rate_limit)
        rate_limit = rl
        data = content.json()
        # Collect document meta information
        total_pages = data['meta']['totalPages']
        total_count = data['meta']['totalElements']
        comment_data = pd.DataFrame(data['data'])
        # More than one page of comments
        if data['meta']['hasNextPage']:
            for i in range(1,total_pages):
                url_update=self.docket_url_maker(page_num=i+1)
                content, rate_limit =self.make_request(url_update, rate_limit)
                data=content.json()
                # Append the comments meta in a dataframe
                comment_data = pd.concat([comment_data,
                                          pd.DataFrame(data['data'])])
        comment_data.reset_index(inplace=True, drop=True)
        print("Number of comments in Docket {}: {}".format(self._docnum,
                                                           total_count))
        return comment_data, rate_limit

    def extract_each_comment(self, url, rate_limit):
        """
        Retrieve comment using the comment url.
        Arguments: comment url (endpoint)
        E.g: https://api.regulations.gov/v4/comments/CMS-2011-0142-0061
        """
        api_key = self.collect_api()
        # Add API key to the url
        comment_url=url+'?include=attachments&api_key='+api_key
        comment_request, rl =self.make_request(comment_url, rate_limit)
        rate_limit = rl
        print("each_comment {}".format(rl))
        comment_json = comment_request.json()
        comment_data = comment_json['data']
        comment_text_meta=comment_data['attributes']
        # If a comment has attachments
        if 'included' in comment_json:
            attachs=comment_json['included']
            att_links=[]
            for i in range(len(attachs)):
                att_links.append(attachs[i]['attributes']['fileFormats'][0]['fileUrl'])
                # info_dict['title']=attachs[i]['attributes']['title']
            comment_attach_link = att_links
        else:
            comment_attach_link = ''
        return comment_text_meta, comment_attach_link

    def comment_attach_data(self, pd_data, rate_limit):
        """
        Iterates through each comment link to download the text and the
        comment meta data. Returns a Pandas DataFrame
        """
        for ind in pd_data.index:
            obtain_link = pd_data.loc[ind,'links']
            extract_link = obtain_link['self']
            # print(extract_link)
            cmnt_info, cmnt_attach_link=self.extract_each_comment(extract_link, rate_limit)
            pd_data.loc[ind, "comment_text"] = cmnt_info["comment"]
            pd_data.loc[ind, "attach_link"] = str(cmnt_attach_link)
        return pd_data

    def json_normal(self, pd_data, cols):
        """
        Some columns are nested as json objects, unpack them
        pd_data: Pandas DataFrame
        cols: JSON object columns to unpack

        """
        dat2 = pd.json_normalize(pd_data[cols])
        pd_data = pd_data.merge(dat2, left_index=True,
                                      right_index=True)
        pd_data.drop(columns=cols, inplace=True)
        return pd_data

    def download_attach(self, url):
        r = requests.get(url)
        fnm0 = url.split("/")[-2]
        fnm1 = url.split("/")[-1]
        fnm = fnm0+fnm1
        with open(fnm, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)


if __name__=="__main__":

    docket_url = r'https://api.regulations.gov/v4/comments?filter[docketId]='
    # docket_url_gt_5000 = r'https://api.regulations.gov/v4/documents?filter[docketId]='

    doc1=RegCommentAPI(api_file='../Reg_API_IMPAQ')
    doc1.url=docket_url
    # doc1.docnum='CMS-2011-0142'
    doc1.docnum = 'HHS-OCR-2015-0006'

    print(doc1.docnum)
    #API request format URL
    url1 = doc1.docket_url_maker()
    print(url1)
    # Starting API request limit
    rt_lt = doc1.get_rate_limit(url1)
    print("Starting API rate limit {}".format(rt_lt))

    # Request and Collect JSON file of comments
    comment_data, rl = doc1.execute_request(url1, rate_limit=rt_lt)

    # Clean up and convert to Pandas DataFrame
    comment_data = doc1.comment_attach_data(comment_data, rate_limit = rl)
    print(comment_data.shape)

    # Unpack column with JSON objects as values
    comment_data_rev = doc1.json_normal(comment_data, cols='attributes')

    # Save the Comment Data with the Docket name
    date_1 = datetime.now().strftime("%Y_%m_%d-%I%M%p")
    comment_data_rev.to_csv("{}_{}.csv".format(doc1.docnum, date_1))

    # Download All Attachments
    # ~~~~
    ## Create and change directory
    save_dir = doc1.docnum+'_attachments'
    os.mkdir(save_dir)
    os.chdir(save_dir)

    ## Cycle through the Download links to fetch the files
    for ind in comment_data_rev.index:
        list_attach=comment_data_rev.loc[ind,"attach_link"]
        if list_attach != "":
            cln_lst_att = ast.literal_eval(list_attach)
            for item in cln_lst_att:
                print(item)
                doc1.download_attach(item)
                print("download {} complete".format(item))
    # ~~~
