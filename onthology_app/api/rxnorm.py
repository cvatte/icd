import pandas as pd
from collections import OrderedDict
from flask import request,Response
import requests
#import simplejson as json
import spacy
#from sklearn.feature_extraction.text import TfidfVectorizer
#from sklearn.metrics.pairwise import cosine_similarity
import werkzeug
import os
from werkzeug.utils import secure_filename
import time
import uuid

from flask_restful import Resource, reqparse, fields, marshal_with
from onthology_app.rxnorm import get_details_from_code,call_init_azure,get_details_from_description
from onthology_app.api.jwtvalidator import checkAuthorization
from onthology_app.status.messages import messages
from onthology_app import Serializer
from flask import g
import sys


parser = reqparse.RequestParser()
parser.add_argument("file", required=True, type=werkzeug.datastructures.FileStorage, location = 'files', help=messages["no-file-help"]["message"])
parser.add_argument("emailid", required=True, help=messages["no-email-help"]["message"])

class RxNormCodeInfo(Resource):

    def get(self, rxnormcode):
        #call_init_azure()
        #jwt_decoded, resp = checkAuthorization()
        #if resp:
        #    return resp
        rxnormdata = get_details_from_code(rxnormcode)
        return rxnormdata

class RxNormDescInfo(Resource):

    def get(self,description):
        #call_init_azure()
        #jwt_decoded, resp = checkAuthorization()
        #if resp:
        #    return resp
        rxnormdata = get_details_from_description(description)
        return rxnormdata


