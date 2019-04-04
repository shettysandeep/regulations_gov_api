
# coding: utf-8

# ### Code for extracting data via API from Regulations.gov 
# #### Author: Sandeep
# Sat 28 Sep 2017 12:16 AM EST

# **Title of the Regulation**
# Application of the Fair Labor Standards Act to Domestic Service
# 
# ** Docket ID **
# WHD-2011-0003
# 

# In[ ]:

# modules imported
import requests 
import pandas as pd
import numpy as np
import json 
import time
import datetime as dt
import itertools


# In[ ]:

# User-defined parameters change:

# Defining the url (base link, API, etc)

base = 'https://api.data.gov/regulations/v3/documents'
api = '' 										# Insert API key as string
docnum = 'WHD-2011-0003'                         # Docket Id
dattyp = 'json'                                  # record type requested


# In[ ]:

'''
Some of the variables below are specific to Regulations.gov API. 
For this website, user doesn't need to enter values of 'numres' 
if the intention is collect all comments. 
Change only if you have any want test using smaller batches

'''

numres = 9830             # total number of records (No input required)
rpp = 500                 # results per page (Set by the user)
pg = 0                    # page offset (calculated in the code as per Regulations.gov instructions)
all_limit = 1000          # request per hour allowed (Regulations.gov API default is 1000)
nreqhr = int(numres/rpp)  # number of requests needed to download data


# In[ ]:

def url_maker(base, api, docnum, dattyp, rpp, pg):
    
    '''Uses the parameters above (url,API key, etc.) 
           and creates url
    '''
    url_name = base + '.' + dattyp + '?api_key=' + api + '&D=' + docnum + '&rpp=' + str(rpp) + '&po=' + str(pg)
    #url_name = url_base
    
    return url_name


# In[ ]:

def request_maker(pg=0):
    
    '''Function makes 1 request. Outputs comments in a json file
       Default is 0. It reuests and collects the first page of 
       results. Parameterizing for multiple requests below
    ''' 
    res1 = requests.get(url_maker(base, api, docnum, dattyp, rpp, pg))
    data = res1.json()    
    
    return (data, res1)


# In[ ]:

def document_info():
    '''Collects some information regarding the Docket. Such as Total 
       number of records, etc.
    '''
    r = request_maker()
    dt = r[0]
    return (dt.get('totalNumRecords'), r[1].headers.get('X-RateLimit-Remaining'))


# In[ ]:

def date_converter(date):
    ''' Args: string date from the API
        Output: date in datetime format '''
    
    t1t = date.replace("GMT","").rstrip()
    t1 = dt.datetime.strptime(t1t,"%a, %d %b %Y %H:%M:%S")
    #t2 - t1 + dt.timedelta(hours = 1)
    return t1


# In[ ]:

def data_getter():
    
    '''Uses the .json output file from request_maker() as input,
       and returns pandas data frame. Tests if requests exceed the 
       alloted number per hour. Pauses the execution for some time
    '''
    tst = pd.DataFrame()                 # Generating an empty dataset
    
    
    rate_limit = int(document_info()[1]) # starting number of available requests
    tot_com = document_info()[0]         # total number of comments present in the docket
    nreqhr = int(tot_com/rpp)            # total number of requests needed to extract all comments
    

    while tot_com > 0 :                  #  while total comments available or needed is positive 
        
        new_tot_com = (rate_limit*rpp)       # apportion feasible number of comments based on the rate available
        
        if rate_limit > nreqhr :         # check permitted requests (if more than needed)
            
            print("inside if")
            
            for val in  np.arange(0 , tot_com, rpp):
                data = request_maker(val)
                tmpdat = pd.DataFrame(data[0].get('documents'))
                tst = tst.append(tmpdat)
        
       
    
            '''If the # of permitted requests available is less than needed
            then break the API data requests into permissible chunks per hour'''

        else:
            
            print("inside else")
            
            start_time = int(data[1].headers.get('Date'))  # start time record
            time1 = date_converter(start_time)             # function to convert date 

            
            for val in  np.arange(0 , new_tot_com, rpp):
                data = request_maker(val)
                tmpdat = pd.DataFrame(data[0].get('documents'))
                tst = tst.append(tmpdat)        

            
            
            end_time = int(data[1].headers.get('Date'))
            time2 = date_converter(pause_time)

            halt_time = time1 + dt.timedelta(hours = 1)         # check if 1 hour has passed since

            if end_time < halt_time:                            # Pause process till limit is reset at completion of the hour

                seconds_wait = (half_time - pause_time).seconds # datetime objects resulting 
                time.sleep(seconds_wait.seconds())

        # updating decision variables 
        tst_len = len(tst)                                     # no of comments downloaded
        rate_limit = int(data[1].
                         headers.get('X-RateLimit-Remaining'))  # obtain new  rate limit
        tot_com = tot_com - tst_len                             # obtain remaining comments to extract
        nreqhr = int(tot_com/rpp)                               # calculate requests needed to extract remaining comments
        print(tot_com)      
                
    return tst


# In[ ]:

dats = data_getter()


# In[ ]:

dats.to_csv(docnum + "1.csv")


# In[ ]:

print("The number of comment received: {}".format(len(dats)))


# In[ ]:

print("Unique comments: {}".format(dats['documentId'].unique().shape))


# ### Next section of code is to download the attachments from comments

# In[ ]:

print("Total Count of attachments\n{}".format(dats.attachmentCount.value_counts()))


# In[ ]:

tt1 = dats.loc[dats['attachmentCount']>0,['documentId','attachmentCount']]


# **Over `5100` attachments in this docket.  
# To avoid getting tied up in this subprogram  
# I am commented it out.   
# Uncomment the below code if you want to run this.**

# In[ ]:

'''

url2 = 'https://www.regulations.gov/contentStreamer?documentId={}&attachmentNumber={}&contentType=pdf'

def doc_extract():
    
         
        #Extracts attachments from comments that using 
        #the pandas DataFrame to filter comments with 
        #attachments. Saves them in the current 
        #working directory.
        
    
    for row in tt1.index:
        id1 = tt1.loc[row,'documentId']
        at2 = tt1.loc[row, 'attachmentCount']
        
        for i in np.arange(1,at2+1):
            
            newurl = url2.format(str(id1),str(i))
            
            r = rq.get(newurl)
            
            fnm = 'att{}-{}.pdf'.format(str(id1),str(i))
                
            # alternate filename
            #r.headers.get('Content-Disposition').split('=')[1]
               
            with open(fnm, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=128):
                    fd.write(chunk)
                    
    return None
'''


# In[ ]:



