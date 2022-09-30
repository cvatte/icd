import pandas as pd
import requests
from collections import OrderedDict
from onthology_app import Serializer
from onthology_app.status.messages import messages
from onthology_app.api.jwtvalidator import initAzureAD
import os
import json
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime,timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import smtplib, ssl,email
import csv
import spacy
import simplejson as json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz as ld
import math
from flask import current_app
import re

def call_init_azure():

    tenant_id = current_app.config['TENANT_ID']
    app_id = current_app.config['APPLICATION_ID']
    initAzureAD(tenant_id, app_id)

def convert_df_to_json(df):

    code = str(df['OCode'].unique().flat[0])
    description_list = df['ODescription'].to_list()
    return  {
        "code" : code,
        "description" : description_list
    }

def convert_desc_df_to_json(df):
    print("after calling the function")
    print(df)
    js = df.to_dict(orient='records')
    print("Json value")
    print(js)
    return js

def common_words(inp_desc_comm,train_desc_comm):
    lst3 = [value for value in inp_desc_comm if value in train_desc_comm]

    if len(lst3):
        return 'True'
    else:
        return 'False'

def total_common_words(train_desc,inp_desc_comm):

    words_1 = inp_desc_comm.lower().replace('-', '').replace('(', '').replace(')', '').split()
    words_2 = train_desc.lower().replace('-', '').replace('(', '').replace(')', '').split()
    lst3 = [value for value in words_1 if value in words_2]
    return len(lst3)

def get_details_from_code(rxnormcode):

    header = {'Accept': 'application/json'}
    inputrxnormcode = rxnormcode
    local_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    train_data = pd.read_csv(local_path + "/static/RXNorm_Data_Test.csv", encoding='unicode_escape')

    rslt_df = train_data[train_data['OCode'] == inputrxnormcode]

    print("result dataframe")
    print(rslt_df)

    if rslt_df.empty:

        base_url='https://rxnav.nlm.nih.gov/REST/rxcui/'

        get_data_from_api =requests.get(base_url+str(inputrxnormcode)+'.json',headers=header)

        json_output = json.loads(get_data_from_api.text)
        if ("name" in json_output['idGroup'].keys()):
            return {
                "Code" : inputrxnormcode,
                "Description" : json_output['idGroup']['name']
            }
        else:
            return {"error": messages["rx-code-not-available"]}
    else:
        val = convert_df_to_json(rslt_df)
        return val


def rat_calc(train_desc, inp_desc):
    rat = ld.token_sort_ratio(train_desc, inp_desc)
    return rat

def rat_calc_set(train_desc, inp_desc):
    rat = ld.ratio(train_desc, inp_desc)
    return rat


def get_details_from_description(description):

    local_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    train_data = pd.read_csv(local_path + "/static/RXNorm_Data_Test.csv", encoding='unicode_escape')

    drug_name = description.replace('  ', ' ')
    desc = drug_name

    """
    train_data['ratio'] = train_data.apply(lambda x: rat_calc(x['description'], desc), axis=1)
    res = train_data.sort_values(['ratio'], ascending=[False]).head(1).values.tolist()
    val = res[0][1]
    """

    unwanted = ['-', ',', '(', ')', '[', ']', '/', '@', '<', '~', '%', "'", ':', '.']

    contains_digit = any(map(str.isdigit, desc))
    if contains_digit == True:
        desc_txt = re.split('\d+', desc)
        desc_1 = desc_txt[0]
        #desc_1 = desc_1.replace('-',' ').replace('&',' ').replace('+',' ').replace('/',' ').replace('[', '').replace(']', '')
        for i in unwanted:
            desc_1 = desc_1.replace(i,' ')
        print("if")
        print("description")
        print(desc_1)
    else:
        wordscnt = len(desc.split())
        half = int(math.ceil(wordscnt / 2))
        a = desc.split()[:half]
        res = ' '.join(a)
        desc_1 = res
        #desc_1 = desc_1.replace('-', ' ').replace('&', ' ').replace('+',' ')
        for i in unwanted:
            desc_1 = desc_1.replace(i,' ')
        print("else")
        print("description")
        print(desc_1)

    desc_new = desc.lower().split()

    copy_df = train_data

    if True:
        print("else case final")
        desc_1 = desc_1.lower().replace('vitamins','vitamin')
        print(desc_1)

        copy_df['Original_Desc'] = desc
        copy_df['common_words_extract'] = copy_df.apply(lambda x: total_common_words(x['ODescription'], desc_1), axis=1)

        length = len(desc_1.split())

        rxnorm_two = copy_df[copy_df['common_words_extract']==length]

        print("rxnorm_two result")
        print(rxnorm_two)

        if rxnorm_two.empty:
            copy_df['ratio'] = copy_df.apply(lambda x: rat_calc(x['ODescription'], desc_1), axis=1)
            desc1 = copy_df['ratio']
            ratio = desc1.max()
            print("maximum ratio")
            print(ratio)
            if ratio >= 50:
                rxnorm_two = copy_df.sort_values(['ratio'], ascending=[False]).head(5).values.tolist()
                rat_list = copy_df['ratio'].values
                sort_rat_list = sorted(rat_list, reverse=True)
                b = list(set(sort_rat_list))
                df_new = copy_df[(copy_df.ratio.isin(b[-6:]))]
                print("this is a whole new thing")
                print(df_new)
                rxnorm_final = df_new.sort_values(['ratio','common_words_extract'], ascending=[False,False]).head(3)
                rxnorm_final = rxnorm_final.drop(columns=['common_words_extract', 'ratio','Original_Desc'])
                rxnorm_final.rename(columns={"OCode": "Predicted_Code"}, inplace=True)
                rxnorm_final.rename(columns={"ODescription": "Predicted_Description"}, inplace=True)
                val = convert_desc_df_to_json(rxnorm_final)
                return val
        else:
            rxnorm_two['ratio'] = rxnorm_two.apply(lambda x: rat_calc(x['ODescription'], desc), axis=1)
            rxnorm_final = rxnorm_two.sort_values(['common_words_extract', 'ratio'], ascending=[False, False]).head(5)

            rxnorm_final = rxnorm_final.drop(columns=['common_words_extract', 'ratio','Original_Desc'])

            print("after applying ratio")
            print(rxnorm_two)
            print("final result")
            print(rxnorm_final)
            rxnorm_final.rename(columns={"OCode": "Predicted_Code"}, inplace=True)
            rxnorm_final.rename(columns={"ODescription": "Predicted_Description"}, inplace=True)

            val = convert_desc_df_to_json(rxnorm_final)
            return val