from flask import Blueprint, request, abort
import uuid
# import datetime
from decorators import asJSON, requiresToken, requiresAdmin
from typeform import getMoreResponses
import hashlib
from models.judge import Judge
from models.application import Application
from models.judgement import Judgement
from models.db import db
from sqlalchemy import desc, asc

apiv1 = Blueprint('apiv1', __name__)

# AUTH LOGIN
# GET /api/v1/login
@apiv1.route('/api/v1/login', methods=['POST'])
@asJSON
def login_user():
    login_data = request.get_json()
    username = login_data['user']
    pwd = hashlib.sha512(login_data['password']).hexdigest()

    user = Judge.query.filter_by(name=username, password=pwd).first()
    if user is not None:
        token = str(uuid.uuid4())
        user.token = token
        db.session.commit()
        return {'token': token, 'admin': user.admin}
    else:
        abort(403)


# GET ALL APPLICANTS
# GET /api/v1/applicants
@apiv1.route('/api/v1/applicants', methods=['GET'])
@requiresToken
@asJSON
def get_applicants():
    applications = Application.query.all()
    applications_json = []
    for app in applications:
        applications_json.append(app.to_dict())

    return applications_json


# GET LAST JUDGED APPLICATION
# GET /api/v1/application/last
@apiv1.route('/api/v1/application/last', methods=['GET'])
@requiresToken
@asJSON
def get_last_application():
    id = Judge.getJudgeIdByToken()

    judgement = Judgement.query\
        .filter_by(judge_id=id, )\
        .filter(Judgement.rating != '')\
        .order_by(desc(Judgement.judge_index))\
        .first()

    if judgement is None:
        return {}

    app_id = judgement.app_id

    app = Application.query.filter_by(id=app_id).first()
    return app.to_dict()

# GET NEXT APPLICATION TO JUDGE
# GET /api/v1/application/next
@apiv1.route('/api/v1/application/next', methods=['GET'])
@requiresToken
@asJSON
def get_next_application():
    id = Judge.getJudgeIdByToken()

    judgement = Judgement.query \
        .filter_by(judge_id=id, ) \
        .order_by(desc(Judgement.judge_index)) \
        .first()

    if (judgement is not None) and (judgement.rating == ''):
        print "ayyyy"
        app_id = judgement.app_id
        app = Application.query.filter_by(id=app_id).first()
    else:
        if judgement is None:
            first_app = Application.query.order_by(asc(Application.id)).first()
            next_app = first_app
            new_app_id = next_app.id
        else:
            new_app_id = judgement.app_id + 1
            next_app = Application.query.filter_by(id=new_app_id).first()

        if next_app is not None:
            newJudgement = Judgement(app_id=new_app_id, judge_id=id)
            newJudgement.rating = ''
            if judgement is None:
                newJudgement.judge_index = 0
            else:    
                newJudgement.judge_index = judgement.judge_index + 1

            db.session.add(newJudgement)
            db.session.commit()
            app = next_app
        else:
            app = None

    if app is not None:
        return app.to_dict()
    else:
        return {}

# RATE AN APPLICATION
# POST /api/v1/rate/<rating>
@apiv1.route('/api/v1/rate/<rating>', methods=['POST'])
@requiresToken
@asJSON
def rate_application(rating):
    id = Judge.getJudgeIdByToken()
    judgement = Judgement.getCurrentJudgementByJudgeId(id)

    if judgement is None:
        return {"status": "ko"}

    judgement.rating = rating
    db.session.commit()

    return {"status": "ok"}

# CHANGE STATE OF APPLICATION
# POST /api/v1/state/<int:application_id>/<state>
@apiv1.route('/api/v1/state/<int:application_id>/<state>', methods=['POST'])
@requiresToken
@requiresAdmin
@asJSON
def change_application_state(application_id, state):
    app = Application.query.filter_by(id=application_id).first()

    if app is not None:
        app.state = state
        db.session.commit()
        return {"result": "ok"}

    return {"result": "ko"}  

# GET APPLICATION DETAIL
# POST /api/v1/application/<int:application_id>
@apiv1.route('/api/v1/application/<int:application_id>', methods=['GET'])
@requiresToken
@asJSON
def get_application_detail(application_id):
    app = Application.query.filter_by(id=application_id).first()

    if app is not None:
        return app.to_dict()
    else:
        abort(404)


# GET /api/v1/fetch
@apiv1.route('/api/v1/fetch', methods=['GET'])
@asJSON
def fetch_responses():
    getMoreResponses()
    return {"result": "ok"}
