import pandas as pd
from collections import OrderedDict
from serpapi import GoogleSearch
from flask import request,Response
import spacy
import werkzeug
import os
from werkzeug.utils import secure_filename
import time
import uuid
from flask_restful import Resource, reqparse, fields, marshal_with
from onthology_app.icd import get_details_from_code,get_details_from_description,process_data_in_csv_file,allowed_file_types,update_database,get_job_status_by_id,call_init_azure
from onthology_app.status.messages import messages
from onthology_app.api.jwtvalidator import checkAuthorization
from onthology_app.models.user import User
from msal import ConfidentialClientApplication
from onthology_app import Serializer
from flask import g
import sys,datetime

parser = reqparse.RequestParser()
parser1 = reqparse.RequestParser()
# default location is flask.Request.values and flask.Request.json
# check help text careful it must be string
parser.add_argument("username",required=True, help=messages["no-username-help"]["message"])
parser.add_argument("password",required=True, help=messages["no-password-help"]["message"])
#parser.add_argument("client_id",required=True, help=messages["no-email-help"]["message"])
#parser.add_argument("client_secret",required=True, help=messages["no-client-secret"]["message"])
#parser.add_argument("tenant_id",required=True, help=messages["no-email-help"]["message"])
parser1.add_argument("refresh_token",required=True, help=messages["no-refresh-token"]["message"])



class Authorization(Resource):

    def post(self):
        args = parser.parse_args()
        return User.authenticate(args["username"], args["password"])


class Refresh(Resource):

    def post(self):
        args = parser1.parse_args()
        return User.get_access_token(args["refresh_token"])