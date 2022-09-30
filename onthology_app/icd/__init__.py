import pandas as pd
from collections import OrderedDict
from serpapi import GoogleSearch

from onthology_app import Serializer

from onthology_app.status.messages import messages
from onthology_app.api.jwtvalidator import initAzureAD

import os
import json
import icd10
from datetime import datetime,timezone
import simple_icd_10 as icd
from threading import Thread
import uuid
import concurrent.futures
from shutil import copyfile
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import smtplib, ssl,email
import csv
import spacy
from flask import current_app

def call_init_azure():

    tenant_id = current_app.config['TENANT_ID']
    app_id = current_app.config['APPLICATION_ID']
    initAzureAD(tenant_id, app_id)

def allowed_file_types(filename):
    ALLOWED_EXTENSIONS = set(['csv'])
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def convert_df_to_json(df):
    code = df['Code'].unique().flat[0]
    description_list = df['Description'].to_list()
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

def get_job_status_by_id(id):
    db = get_db()
    return db.query(Job).filter_by(job_id=id).first()



def get_details_from_code(icdcode):

    inputicd = icdcode.replace('.', '').upper()
    local_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    train_data = pd.read_csv(local_path + "/static/ICD_Hier4_rev1_final.csv", encoding='unicode_escape')
    train_data['Code'] = train_data['Code'].str.replace('.', '')
    train_data['Code'] = train_data['Code'].str.strip()
    rslt_df = train_data[train_data['Code'] == inputicd]

    if rslt_df.empty:
        cd = icd10.find(inputicd)

        if cd is None:
            return {"error": messages["code-not-available"]}

        else:
            return {
                "code" : inputicd,
                "description" : cd.description
            }

    else:
        val = convert_df_to_json(rslt_df)
        return val

def get_details_from_description_with_key(description,api_key):
    ds = []
    dk = []
    ip = description
    params = {
        "engine": "google",
        "q": ip + " icd 10 data",
        "location": "United States",
        "hl": "en",
        "gl": "us",
        "google_domain": "google.com",
        "api_key": api_key,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    if "organic_results" in results.keys():

        for result in results["organic_results"]:
            j = result['link']

            if (len(j.split('/')[-1]) <= 10) and not (j.split('/')[-1]).endswith('-') and not (
                    j.split('/')[-1]).endswith('html') and not (j.split('/')[-1]).endswith('htm') and not (
                    j.split('/')[-1]).endswith('pdf'):
                if icd.is_valid_item(j.split('/')[-1]) or icd10.exists(j.split('/')[-1]):
                    ds.append(j.split('/')[-1])
    if ds:
        for code in ds:
            if icd.is_valid_item(code):
                cd = icd.get_description(code)
                dk.append(cd)
            else:
                cd = icd10.find(code)
                dk.append(cd.description)

    df_single = pd.DataFrame(list(zip(ds, dk)), columns=['Predicted_Code', 'Predicted_Description'])
    df_single['Predicted_Code'] = df_single['Predicted_Code'].astype(str).str.replace(".", "")

    val = convert_desc_df_to_json(df_single)

    return val,df_single


def process_data_in_csv_file(input_data,email_id,fname):


    api_key = current_app.config['SERP_API_KEY']
    try:
        db = get_db()
        job_id = str(uuid.uuid1()).replace('-','')
        Job.create_job(db, job_id, 'started', email_id)
        thread = Thread(target=process_data_after_response,args=(api_key,input_data,job_id,email_id,fname,))
        thread.start()
        return {'info':'success','audit_id':job_id}
    except:
        print("Caught exception")



def get_details_from_description(description):

    api_key = '754aee8b575b7c60472576bd3994eafba6ac21ef11bb6f6d04528a3ba6fcff95'
    print("api key")
    print(api_key)
    data = get_details_from_description_with_key(description,api_key)
    return data

def process_data_after_response(key,input_data,job_id,email_id,org_filename):

    local_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    unwanted = ['-',',','(',')','[',']','/','@','<','~','%','\d+',"'",':','.']

    for i in unwanted:
        input_data['icd_description'] = input_data['icd_description'].str.replace(i, '')

    for ind, data in input_data.iterrows():
        icd_data,check_returned_df = get_details_from_description_with_key(data['icd_description'],key)
        if check_returned_df.empty:
            nlp = spacy.load("en_ner_bc5cdr_md")

            ner_code = ner_desc = cd = []

            doc = nlp(data['icd_description'])

            if doc.ents:
                for ent in doc.ents:
                    if ent.label_ == "DISEASE":
                        cd.append(ent.text)

            print("check cd value")
            print(cd)

            if len(cd) == 0:

                print("got the values from POS")

                nlp1 = spacy.load("en_core_web_lg")
                cd1 = []
                doc1 = nlp1(desc)

                for ent in doc1:
                    if ent.pos_ == "NOUN":
                        cd1.append(ent.text)

                combined_string = ' '.join(cd1)
                icd_data, check_returned_df = get_details_from_description_with_key(combined_string, key)

                input_data.at[ind, 'Predicted_Code'] = icd_data[0]['Predicted_Code']
                input_data.at[ind, 'Predicted_Description'] = icd_data[0]['Predicted_Description']

            else:

                print("got the values from NER part")

                combined_string = ' '.join(cd)
                icd_data, check_returned_df = get_details_from_description_with_key(combined_string, key)

                input_data.at[ind, 'Predicted_Code'] = icd_data[0]['Predicted_Code']
                input_data.at[ind, 'Predicted_Description'] = icd_data[0]['Predicted_Description']

        else:

            input_data.at[ind, 'Predicted_Code'] = icd_data[0]['Predicted_Code']
            input_data.at[ind, 'Predicted_Description'] = icd_data[0]['Predicted_Description']

    print("Final output data")
    print(input_data)

    fname = os.path.splitext(org_filename)[0] + '_' + time.strftime("%Y%m%d_%H%M%S") + '.csv'

    input_data.to_csv(local_path + "/static/processed_files/" + fname)

    data = [[job_id, fname, email_id, org_filename, datetime.utcnow()]]
    data = pd.DataFrame(data)
    data.to_csv(local_path + "/static/job_list.csv", mode = 'a', header=False,index=False)


def update_database():

    local_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    subject = current_app.config['SUBJECT']
    body = current_app.config['BODY']
    sender_email = current_app.config['SENDER_EMAIL']
    password = current_app.config['PASSWORD']

    df = pd.read_csv(local_path + "/static/job_list.csv")
    if df.empty:
        print("No action")
    else:
        db = get_db()
        copyfile(local_path + "/static/job_list.csv", local_path + "/static/job_list_temp.csv")

        df_jobs_to_be_updated = pd.read_csv(local_path + "/static/job_list_temp.csv")


        jobs_list = df_jobs_to_be_updated['job_id'].tolist()

        job_test = db.query(Job).filter(Job.job_id.in_(jobs_list)).update({Job.status: 'succeeded'})

        db.commit()

        to_be_deleted = []

        for ind,row in df_jobs_to_be_updated.iterrows():
            job_id = row['job_id']
            filename = row['fname']
            receiver_email = row['email_id']
            original_filename = row['filename']
            end_time = row['end_time']

            ind_job = db.query(Job).filter_by(job_id=job_id).first()
            ind_job.job_end_time = end_time
            ind_job.output_filename = filename
            ind_job.input_filename = original_filename
            db.commit()

            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = receiver_email
            message["Subject"] = subject

            message.attach(MIMEText(body, "plain"))

            email_filename = local_path + "/static/processed_files/" + filename

            with open(email_filename, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)

            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {original_filename}",
            )

            message.attach(part)
            email_text = message.as_string()

            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, email_text)

            to_be_deleted.append(job_id)

        list = df_jobs_to_be_updated.values.tolist()

        lines = []

        with open(local_path + "/static/job_list.csv","r") as readfile:
            reader = csv.reader(readfile)
            next(reader)
            for row in reader:
                if row[0] not in to_be_deleted:
                    lines.append(row)

        with open(local_path + "/static/job_list.csv", 'w',newline='', encoding='utf-8') as writeFile:
            writer = csv.writer(writeFile)
            writer.writerow(["job_id", "fname", "email_id", "filename", "end_time"])
            writer.writerows(lines)

        os.remove(local_path + "/static/job_list_temp.csv")

    return "yes"

def init_icd(app):
    pass
