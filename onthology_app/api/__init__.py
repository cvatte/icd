from flask_restful import Api
from onthology_app.api.icd import CodeInfo,DescriptionInfo,TestAuth
from onthology_app.api.rxnorm import RxNormCodeInfo,RxNormDescInfo
from onthology_app.api.auth import Authorization
from onthology_app.api.auth import Refresh
from flask import g, request


def init_api(app):
    #print("starting point in api")
    api = Api(app)




    api.add_resource(CodeInfo, '/api/icdcode/<string:icdcode>')

    api.add_resource(DescriptionInfo, '/api/icddesc/<string:description>')

    api.add_resource(RxNormCodeInfo, '/api/rxnormcode/<int:rxnormcode>')

    api.add_resource(RxNormDescInfo, '/api/rxnormdesc/<string:description>')

    api.add_resource(TestAuth, '/api/testauth')

    api.add_resource(Authorization, '/api/authorize')

    api.add_resource(Refresh, '/api/refresh')




