# -*- coding: utf-8 -*-

"""
__author__: Sandeep Shetty
__date__: October 21, 2021

Code to extract comments (and  attachments)  from Regulations.gov API

"""

from datetime import datetime
import json, os
import requests
import ast
import pandas as pd

class RegCommentAPI:
    """Extract Comments on Docket from Regulation.gov"""

    def __init__(self, api_file, page_size = 25):
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
        if self._api:
            return self._api
        else:
            with open(self.api_file) as f:
                api=f.read()
            return api

    def docket_url_maker(self, page_num=1):
        api = self.collect_api()
        url_name = self._url+self._docnum+\
                   '&page[number]='+str(page_num)+\
                   '&page[size]='+str(self.page_size)+\
                   '&api_key='+api
        return str(url_name)

    def make_request(self, url):
        '''API request, collect results'''
        request_data = requests.get(url)
        return request_data

    def execute_request(self, url):
        """Extract all comments"""
        content = self.make_request(url1)
        data = content.json()

        # Collect document meta information
        total_pages = data['meta']['totalPages']
        total_count = data['meta']['totalElements']
        comment_data = pd.DataFrame(data['data'])

        # More than one page of comments
        if data['meta']['hasNextPage']:
            for i in range(1,total_pages):
                url_update=self.docket_url_maker(page_num=i+1)
                self.make_request(url_update)
                content=self.make_request(url_update)
                data=content.json()
                # Append the comments meta in a dataframe
                comment_data = pd.concat([comment_data,
                                          pd.DataFrame(data['data'])])
        comment_data.reset_index(inplace=True, drop=True)
        print("Number of comments in Docket {}: {}".format(self._docnum,
                                                           total_count))
        return comment_data

    def extract_each_comment(self, url):
        """
        Retrieve comment using the comment url.
        Arguments: comment url (endpoint)

        """
        api_key = self.collect_api()
        # Add API key to the url
        comment_url=url+'?include=attachments&api_key='+api_key
        comment_request=self.make_request(comment_url)
        comment_json = comment_request.json()
        comment_data = comment_json['data']
        comment_text_meta=comment_data['attributes']
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

    def comment_attach_data(self, pd_data):
        """
        Iterates through each comment link to download the text and the
        comment meta data.

        Returns an Pandas DataFrame

        """
        for ind in pd_data.index:
            obtain_link = pd_data.loc[ind,'links']
            extract_link = obtain_link['self']
            # print(extract_link)
            cmnt_info, cmnt_attach_link=self.extract_each_comment(extract_link)
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

    doc1=RegCommentAPI(api_file='Reg_API_AIR')
    doc1.url=docket_url
    doc1.docnum='CMS-2011-0142'

    print(doc1.docnum)
    url1 = doc1.docket_url_maker()

    comment_data = doc1.execute_request(url1)

    comment_data = doc1.comment_attach_data(comment_data)
    print(comment_data.shape)

    # Unpack column with JSON objects as values
    comment_data_rev = doc1.json_normal(comment_data, cols='attributes')
    comment_data_rev.drop(columns=['attributes'], inplace=True)

    # Save the Comment Data with the Docket name
    date_1 = datetime.now().strftime("%Y_%m_%d-%I%M%p")
    comment_data_rev.to_csv("{}_{}.csv".format(doc1.docnum, date_1))

    # Download attachments
    save_dir = doc1.docnum+'_attachments'
    os.mkdir(save_dir)
    os.chdir(save_dir)
    for ind in comment_data_rev.index:
        list_attach=comment_data_rev.loc[ind,"attach_link"]
        if list_attach != "":
            cln_lst_att = ast.literal_eval(list_attach)
            for item in cln_lst_att:
                print(item)
                doc1.download_attach(item)
                print("download {} complete".format(item))
