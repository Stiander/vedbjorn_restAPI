__author__ = 'Stiander'
print('main.py begin')

import datetime
import os

import uvicorn
from fastapi import FastAPI, Request, Response, Query, File, UploadFile
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from libs.qrpcclientlib.grpcClient import CoordinateToLocation , GetUser , LocationToGraph , DeleteSellRequest , \
    CreateUser, DeleteUser, BuyRequestToUser, GetBuyRequest, DeleteBuyRequest, SellRequestToUser, GetSellRequest , \
    DriveRequestToUser, GetDriveRequest, DeleteDriveRequest, FindCoordinatesInAddress, NameToLocation, GetMarketInfo , \
    GetPlannedRoute , SetAcceptPlannedRoute , GetOngoingRoute , PushVisit , GetVisit, GetCompletedRoutes , GetBuyRequestMatch , \
    PushFeedbackComplaintNondelivery, GetMessages, GetBuyRequestNotification, GetDeliveryProof , PushFeedbackAcceptDelivery , \
    PushFeedbackRejectDelivery, GetAllCompletedDeliveryInfoForBuyer, GetDeliveryReceipt, GetFinishedRouteReceipt, \
    GetNewSellerDealInfoList, GetNewSellerDealAccept, GetOngoingSellerDealInfoList, GetCompletedSells, GetSellsReceipt, \
    VerifyUserEmailStart, VerifyUserEmail, GetPaymentInfo, UpdatePaymentInfo_vippsOrderId, UpdatePaymentInfo_paymentStatus, \
    UpdateCompany, GetCompany, GetBatchSellRequest, UpdateBatchSellRequest, GetFinishedRouteInvoice, GetSellsInvoice, \
    OrderAdmMassEmails, GetPrices, SetPrices, GetSeasonOnOrOff, SetSeasonOnOrOff, GetAllCompletedDeliveryInfoForBuyerAdm ,\
    GetDeliveryReceiptAdm

from libs.commonlib.db_insist import get_db

import cv2
import numpy as np
import base64
import pytz
import auth

IS_DEBUG = str(os.getenv('debug', '')) == 'true'

class PriceDefinition(BaseModel) :
    county : str
    price : float
    product : str

class OnOrOff(BaseModel) :
    value : bool

class AllPrices(BaseModel) :
    items : List[PriceDefinition]

class AdmMassEmails(BaseModel) :
    title : str
    text : str
    toBuyers : bool
    toSellers : bool
    toDrivers : bool
    emails : list

class UserBody(BaseModel) :
    location_name : str
    phone: str
    firstname : str
    lastname : str
    email : str

class OrderRef(BaseModel) :
    orderId : str
    vedbId : str

class BuyRequest(BaseModel) :
    current_requirement : int
    reserved_weeks : int

class SellRequest(BaseModel) :
    current_capacity : int

class DriveRequest(BaseModel) :
    available : bool

class NewUserVerificationContent(BaseModel) :
    email: str
    phone : str
    firstname: str
    lastname: str
    lat: float
    lng: float
    zip: str
    county: str
    country: str
    municipality: str
    road: str

class DeliveryRejectReason(BaseModel) :
    isWrongAmount : bool
    badQuality : bool
    wrongPrice : bool

app = FastAPI()

# SERVICE Configurations
HOST=os.getenv("HOST", "0.0.0.0")
PORT= int(os.getenv("PORT",8080))

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
    "https://vedbjorn.web.app/",
    "https://vedbjorn.web.app",
    "https://vedbjorn.web.app:8080",
    "https://vedbjorn.no"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
Testing the GRPC server connection
"""
print('Build-time : 21.05.2023 - 13:08')
print('REST Server : Will try to contact gRPC server...')
its_ok = GetMarketInfo({'municipality' : 'Oslo' ,'county' : 'Oslo'})
print('gRPC client working? : ' , its_ok)

@app.get("/")
async def index():
    return {'index_page' : 'nothing_much'}

@app.get("/areainfo")
async def get_areainfo(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    ret : dict = {}
    muni = GetMarketInfo({
        'municipality' : req.query_params.get('muni' , '') ,
        'county' : req.query_params.get('county' , '')
    })
    county = GetMarketInfo({
        'county': req.query_params.get('county', '')
    })
    if muni :
        ret['muni'] = county
    if county :
        ret['county'] = county
    return ret

@app.get("/addrfromcoords")
async def get_addrfromcoords(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    return CoordinateToLocation(
        float(req.query_params.get('lat' , -1)),
        float(req.query_params.get('lng' , -1)))

@app.get("/addrfromname")
async def get_addrfromname(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    return NameToLocation(req.query_params.get('name' , ''))

@app.post("/adm/sendemails")
async def mass_send_emails(body : AdmMassEmails, req : Request, res : Response) :
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 403
        return None

    if DEBUG_USER and 'email' in DEBUG_USER :
        email = DEBUG_USER['email']
    else :
        email = auth_content['email']

    adm = get_db().insist_on_find_one_q('admins' , {'email' : email})
    if not adm :
        res.status_code = 403
        return None

    return OrderAdmMassEmails(body.title, body.text, body.toBuyers, body.toSellers, body.toDrivers, body.emails)


@app.get("/adm/prices")
async def get_adm_prices(req: Request, res: Response):
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 403
        return None

    if DEBUG_USER and 'email' in DEBUG_USER :
        email = DEBUG_USER['email']
    else :
        email = auth_content['email']

    adm = get_db().insist_on_find_one_q('admins', {'email': email})
    if not adm:
        res.status_code = 403
        return None

    return GetPrices()


@app.post("/adm/prices")
async def post_adm_prices(body : AllPrices , req: Request, res: Response):
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 403
        return None

    if DEBUG_USER and 'email' in DEBUG_USER :
        email = DEBUG_USER['email']
    else :
        email = auth_content['email']

    adm = get_db().insist_on_find_one_q('admins', {'email': email})
    if not adm:
        res.status_code = 403
        return None

    prices : list = list()
    for prc in body.items :
        prices.append({
            'county' : prc.county ,
            'price' : prc.price ,
            'product' : prc.product
        })
    return SetPrices(prices)

@app.get("/adm/inseason")
async def get_adm_inseason(req: Request, res: Response):
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 403
        return None

    return GetSeasonOnOrOff()

@app.post("/adm/inseason")
async def post_adm_inseason(body : OnOrOff, req: Request, res: Response):
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 403
        return None

    if DEBUG_USER and 'email' in DEBUG_USER :
        email = DEBUG_USER['email']
    else :
        email = auth_content['email']

    adm = get_db().insist_on_find_one_q('admins', {'email': email})
    if not adm:
        res.status_code = 403
        return None

    if body.value == False :
        on_or_off = 'off'
    else:
        on_or_off = 'on'
    return SetSeasonOnOrOff(on_or_off)

@app.post("/location")
async def create_location(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    return LocationToGraph(
        float(req.query_params.get('lat' , -1)),
        float(req.query_params.get('lng' , -1)))

@app.get("/user")
async def get_user(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', '')
    if DEBUG_USER :
        dbgUserObj = GetUser(email=DEBUG_USER)
        auth_content['phone'] = dbgUserObj['phone']
        auth_content['email'] = dbgUserObj['email']

    if not auth.let_me_in(auth_content):
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    authed_phone = auth_content.get('phone', '')

    #param_email = req.query_params.get('email' , '')
    usr = GetUser(authed_email, authed_phone)

    if not usr['info']['ok'] :
        res.status_code = usr['info']['code']
        return usr['info']['content']
    del usr['info']
    return usr

@app.get("/usertaken")
async def get_user(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    usr = GetUser(req.query_params.get('email' , ''))
    if usr and usr['info']['code'] == 200:
        return True
    else:
        return False

@app.get("/user/verify/start")
async def get_user_verify_start(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email' , '')
    return VerifyUserEmailStart(authed_email)

@app.get("/user/verify")
async def get_user_verify(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    return VerifyUserEmail(authed_email, req.query_params.get('code' , ''))

@app.delete("/user")
async def delete_user(req : Request, res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    grpc_ret = DeleteUser(authed_email, req.query_params.get('phone' , ''))
    res.status_code = grpc_ret['code']
    return {'content' : grpc_ret['content']}

@app.post("/user")
async def create_user(req : Request, user : UserBody , res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')

    grpc_ret = CreateUser({
        'email' : authed_email , # user.email ,
        'phone' : user.phone ,
        'firstname' : user.firstname ,
        'lastname' : user.lastname ,
        'location_name' : user.location_name
    })
    res.status_code = grpc_ret['code']
    return {'content' : grpc_ret['content']}

@app.post("/checkuserverify")
async def checkuserverify(req : Request, user : NewUserVerificationContent , res : Response):

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')

    userObj : dict = {
        'email' : authed_email, #user.email ,
        'phone' : user.phone ,
        'firstname' : user.firstname ,
        'lastname' : user.lastname
    }
    locationObj : dict = {
        'country' : user.country ,
        'county' : user.county ,
        'municipality' : user.municipality ,
        'road' : user.road ,
        'zip' : user.zip
    }
    usr = GetUser(userObj['email'] , userObj['phone'])
    is_taken = (usr and usr['info']['code'] == 200)
    if is_taken :
        return {
            'verified' : False,
            'msg' : 'User taken'
        }
    loc = FindCoordinatesInAddress(locationObj)
    if loc['info']['code'] != 200 :
        res.status_code = loc['info']['code']
        return loc['info']
    del loc['info']
    return loc

@app.put("/buyrequest")
async def put_buyrequest(req : Request, buyreq : BuyRequest, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    #email = req.query_params.get('email' , '')
    authed_email = auth_content.get('email', '')

    grpc_ret = BuyRequestToUser(authed_email , {
        'current_requirement': buyreq.current_requirement,
        'reserved_weeks': buyreq.reserved_weeks
    })
    res.status_code = grpc_ret['code']
    if str(grpc_ret['content']).lower() == 'no changes made' :
        res.status_code = 200
    return {'content': grpc_ret['content']}

@app.get("/buyrequest")
async def get_buyrequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    #email = req.query_params.get('email' , '')
    authed_email = auth_content.get('email', '')

    ret = GetBuyRequest(authed_email)
    if 'code' in ret and ret['code'] != 200:
        if ret['code'] == 404 :
            return {'info' : 'no buyreq'}
        res.status_code = ret['code']
        return ret
    del ret['info']
    return ret

@app.get("/buyrequest/notification")
async def get_buyrequest_notification(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')

    return GetBuyRequestNotification({
        'receiverEmail' : authed_email
    })

@app.get("/buyrequest/match")
async def get_buyrequest_match(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    #email = req.query_params.get('email' , '')
    authed_email = auth_content.get('email', '')
    return GetBuyRequestMatch(authed_email)

@app.delete("/buyrequest")
async def delete_buyrequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    grpc_ret = DeleteBuyRequest(authed_email)
    res.status_code = grpc_ret['code']
    return {'content' : grpc_ret['content']}

@app.put("/sellrequest")
async def put_sellrequest(req : Request, sellreq : SellRequest, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    grpc_ret = SellRequestToUser(authed_email , {
        'current_capacity': sellreq.current_capacity
    })
    res.status_code = grpc_ret['code']
    return {'content': grpc_ret['content']}

@app.get("/sellrequest")
async def get_sellrequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    ret = GetSellRequest(authed_email)
    if 'code' in ret and ret['code'] != 200:
        if ret['code'] == 404:
            return {'info' : 'no sellreq'}
        res.status_code = ret['code']
        return ret
    del ret['info']
    return ret

@app.get("/sellrequest/deals/new")
async def get_sellrequest_newdeals(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    return GetNewSellerDealInfoList(authed_email)

@app.get("/sellrequest/deals/ongoing")
async def get_sellrequest_ongoingdeals(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    return GetOngoingSellerDealInfoList(authed_email)

@app.put("/sellrequest/deals/new/accept")
async def put_sellrequest_newdeals_accept(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    if auth.ALWAYS_LET_ME_IN :
        authed_email = req.query_params.get('email' , '')
    else:
        authed_email = auth_content.get('email', '')
    return GetNewSellerDealAccept(
        email = authed_email ,
        id = req.query_params.get('id', '') ,
        accept = req.query_params.get('accept', 'true') == 'true'
    )

@app.delete("/sellrequest")
async def delete_sellrequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    grpc_ret = DeleteSellRequest(authed_email)
    res.status_code = grpc_ret['code']
    return {'content' : grpc_ret['content']}

@app.put("/driverequest")
async def put_driverequest(req : Request, drivereq : DriveRequest, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    grpc_ret = DriveRequestToUser(authed_email , {
        'available': drivereq.available
    })
    res.status_code = grpc_ret['code']
    return {'content': grpc_ret['content']}

@app.get("/driverequest")
async def get_driverequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    ret = GetDriveRequest(authed_email)
    if ret['info']['code'] != 200 :
        if ret['info']['code'] == 404 :
            return {'info' : 'no drivereq'}
        res.status_code = ret['info']['code']
        return ret['info']
    del ret['info']
    return ret

@app.get("/plannedroute")
async def get_driverequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    # TODO :
    # TODO : CHeck if the resource is available according to auth_content.email
    # TODO :

    #driveName = req.query_params.get('name' , '')
    authed_email = auth_content.get('email', '')
    route = GetPlannedRoute(authed_email)
    if route['info']['ok'] != True :
        return route['info']
    return route

@app.put("/plannedrouteaccept")
async def put_plannedrouteaccept(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    if auth.ALWAYS_LET_ME_IN :
        authed_email = req.query_params.get('name', '')
        if not '@' in authed_email :
            authed_email = DEBUG_USER['email']
    else:
        authed_email = auth_content.get('email', '')
    #driveName = req.query_params.get('name' , '')
    accepted = req.query_params.get('accept' , 'true') == 'true'
    route = SetAcceptPlannedRoute(authed_email , accepted)
    return route

@app.delete("/driverequest")
async def delete_driverequest(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    grpc_ret = DeleteDriveRequest(authed_email)
    res.status_code = grpc_ret['code']
    return {'content' : grpc_ret['content']}

@app.get("/ongoingroute")
async def get_ongoingroute(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #driveName = req.query_params.get('name' , '')
    route = GetOngoingRoute(authed_email)
    return route

@app.get("/ongoingroute/old")
async def get_ongoingroute_old(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #driveName = req.query_params.get('name' , '')
    routes = GetCompletedRoutes(authed_email)
    return routes

@app.get("/ongoingroute/old/receipt")
async def get_ongoingroute_old_receipt(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    id = req.query_params.get('id', '')
    ret = GetFinishedRouteReceipt(id, authed_email)
    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

@app.get("/ongoingroute/old/invoice")
async def get_ongoingroute_old_invoice(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    id = req.query_params.get('id', '')
    ret = GetFinishedRouteInvoice(id, authed_email)
    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

def readb64(contents):
   encoded_data = contents.split(',')[1]
   nparr = np.fromstring(base64.b64decode(encoded_data), np.uint8)
   img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
   return img

@app.post("/visitedproof")
async def post_visitedproof(req : Request, res : Response, file: UploadFile = File(...) ) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    if auth.ALWAYS_LET_ME_IN :
        authed_email = req.query_params.get('email', '')
    else:
        authed_email = auth_content.get('email', '')

    if not authed_email and DEBUG_USER != None :
        authed_email = DEBUG_USER['email']

    driveName = req.query_params.get('name', '')
    route = GetOngoingRoute(authed_email)
    if route['info']['ok'] != True :
        return {
            'failed' : 'Route not found' ,
            'content' : route['info']['content']
        }
    try:
        index = int(req.query_params.get('index', -1))
        if index < 0 or index >= len(route['route']) :
            res.status_code = 400
            return {'failed' : 'Visit at route index not found'}
        visit = route['route'][index]
        if visit['type'] == 'pickup' :
            img_text = driveName + ' har hentet ' + str(visit['loaded_after'] - visit['loaded_before']) + ' vedsekker'
        else :
            img_text = driveName + ' har levert ' + str(visit['loaded_before'] - visit['loaded_after']) + ' vedsekker'

        contents = file.file.read()
        try:
            contents_str = contents.decode('utf-8')
        except UnicodeDecodeError :
            contents_str = ''

        if contents_str :
            encoded_data = contents_str.split(',')[1]
            nparr = np.fromstring(base64.b64decode(encoded_data), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img = cv2.putText(
                img = img ,
                text = img_text ,
                org = (20, 20) ,
                fontFace = cv2.FONT_HERSHEY_SCRIPT_COMPLEX ,
                fontScale = 0.5,
                color=(83, 199, 111),
                thickness = 1
            )

            utc_time = datetime.datetime.utcnow()
            NOR_TIME = pytz.timezone('Europe/Oslo')

            img = cv2.putText(
                img = img ,
                text = 'Tidspunkt (UTC) : ' + utc_time.astimezone(NOR_TIME).strftime('%d-%m-%Y %H:%M:%S') ,
                org = (20, 40) ,
                fontFace = cv2.FONT_HERSHEY_SCRIPT_COMPLEX ,
                fontScale = 0.5,
                color=(83, 199, 111),
                thickness = 1
            )
            img = cv2.putText(
                img=img,
                text='Vennlig hilsen Vedbjorn :)',
                org=(20, 60),
                fontFace=cv2.FONT_HERSHEY_SCRIPT_COMPLEX,
                fontScale=0.5,
                color=(83, 199, 111),
                thickness=1
            )
            image_bytes = cv2.imencode('.jpg', img)[1].tobytes()
        else:
            image_bytes = None

        ret = PushVisit({
            'img' : image_bytes ,
            'index' : index ,
            'driverName' : authed_email ,
            'type' : visit['type'] ,
            'img_text' : img_text ,
            'timestamp' : datetime.datetime.utcnow().timestamp()
        })
        #cv2.imwrite('./test1.jpeg' , img)

    except Exception as e:
        raise e
    finally:
        file.file.close()
    return ret

@app.get("/visitedproof")
async def get_visitedproof(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    driveName = req.query_params.get('name', '')
    route = GetOngoingRoute(authed_email)
    if route['info']['ok'] != True :
        return {
            'failed' : 'Route not found' ,
            'content' : route['info']['content']
        }

    index = int(req.query_params.get('index', -1))
    if index < 0 or index >= len(route['route']) :
        res.status_code = 400
        return {'failed' : 'Visit at route index not found'}
    ret = GetVisit(index, authed_email)
    b64_content = b'data:image/jpeg;base64,' + base64.b64encode(ret['img'])
    return Response(content=b64_content, media_type="image/jpeg")

@app.get("/deliveryproof")
async def get_deliveryproof(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    # TODO :
    # TODO : CHeck if the resource is available according to auth_content.email
    # TODO :

    ret = GetDeliveryProof(str(req.query_params.get('id', '')))
    if ret and 'img' in ret and ret['img'] :
        b64_content = b'data:image/jpeg;base64,' + base64.b64encode(ret['img'])
        return Response(content=b64_content, media_type="image/jpeg")
    elif ret.get('info' , {}).get('content' , '') == 'Already paid' :
        res.status_code = ret['info']['code']
        return 'Already paid'
    else:
        res.status_code = 404

@app.put("/feedback/complaint/nondelivery")
async def put_feedback_complaint_nondelivery(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    ongoing_route = req.query_params.get('ongoing_route' , '')
    ret = PushFeedbackComplaintNondelivery(authed_email, ongoing_route)
    res.status_code = ret['code']
    return ret

@app.get("/messages")
async def get_messages(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    return GetMessages({
        'receiverEmail' : authed_email, #req.query_params.get('email', '') ,
        'senderEmail' : req.query_params.get('senderEmail', ''),
        'from_time' : req.query_params.get('from_time', 0),
        'to_time' : req.query_params.get('to_time', 0),
        'indices' : req.query_params.get('indices', []),
        'action' : req.query_params.get('action', '')
    })

@app.put("/delivery/accept")
async def put_delivery_accept(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    delivery_notif_id = req.query_params.get('id' , '')
    ret = PushFeedbackAcceptDelivery(authed_email, delivery_notif_id)
    res.status_code = ret['code']
    return ret

@app.post("/delivery/decline")
async def put_delivery_accept(req : Request, res : Response, reason : DeliveryRejectReason) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    ret = PushFeedbackRejectDelivery(
        email = authed_email, #req.query_params.get('email', '') ,
        notif_id = req.query_params.get('id', '') ,
        wrongAmount = reason.isWrongAmount ,
        wrongPrice = reason.wrongPrice ,
        wrongQuality = reason.badQuality
    )
    res.status_code = ret['code']
    return ret

@app.get("/delivery/history")
async def get_delivery_history(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    return GetAllCompletedDeliveryInfoForBuyer(authed_email)

@app.get("/delivery/history/adm")
async def get_delivery_history_adm(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    admindoc = get_db().insist_on_find_one_q('admins' , {'email' : authed_email})
    if not admindoc :
        res.status_code = 401
        return None

    return GetAllCompletedDeliveryInfoForBuyerAdm(authed_email)

@app.get("/delivery/receipt")
async def get_delivery_receipt(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    # TODO :
    # TODO : CHeck if the resource is available according to auth_content.email
    # TODO :

    id = req.query_params.get('id', '')
    ret = GetDeliveryReceipt(id)
    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

@app.get("/delivery/receipt/adm")
async def get_delivery_receipt(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    admindoc = get_db().insist_on_find_one_q('admins', {'email': authed_email})
    if not admindoc:
        res.status_code = 401
        return None

    ismva = req.query_params.get('ismva', True)
    id = req.query_params.get('id', '')
    ret = GetDeliveryReceiptAdm(id, ismva)
    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

@app.get("/sells/old")
async def get_sells_old(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email' , '')
    sells = GetCompletedSells(authed_email)
    return sells

@app.get("/sells/receipt")
async def get_sells_receipt(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    id = req.query_params.get('id', '')
    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email', '')
    ret = GetSellsReceipt(id, authed_email)

    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

@app.get("/sells/invoice")
async def get_sells_invoice(req : Request, res : Response) :

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER) :
        res.status_code = 401
        return None

    id = req.query_params.get('id', '')
    authed_email = auth_content.get('email', '')
    #email = req.query_params.get('email', '')
    ret = GetSellsInvoice(id, authed_email)

    if ret['info']['code'] != 200 :
        res.status_code = ret['info']['code']
        return ret['info']['content']
    return Response(content=ret['bytes'], media_type="application/pdf")

"""
#
#   Vipps Stuff Below :
#
"""
@app.get("/vippsuser")
async def get_vipps_user(req : Request, res : Response):

    access_token = auth.verify_vipps_id_token(req)

    DEBUG_USER = os.getenv('DEBUG_USER', '')
    if DEBUG_USER :
        dbgUserObj = GetUser(email=DEBUG_USER)
        phone_number = dbgUserObj.get('phone' , '')
    else:
        if not access_token:
            res.status_code = 401
            return None
        phone_number = req.query_params.get('num', '')

    db = get_db()
    already_token = db.insist_on_find_one_q('access_tokens' , {'num' : phone_number})
    new_token_doc : dict = {
        'num' : phone_number ,
        'access_token' : access_token ,
        'expires' : datetime.datetime.utcnow().timestamp() + 7200
    }
    if already_token :
        db.insist_on_replace_one('access_tokens' , already_token['_id'], new_token_doc)
    else:
        db.insist_on_insert_one('access_tokens' , new_token_doc)

    already_user = GetUser(phone = phone_number)
    if already_user and already_user['info']['ok'] == True:
        del already_user['info']
        return already_user
    else :
        return already_user['info']

@app.get("/vippspayment")
async def get_vipps_payemnt(req : Request, res : Response):
    """
    Get the payment details needed to initiate the Vipps ECOM procedure

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    notif_id = req.query_params.get('notification', '')
    payment_info = GetPaymentInfo(notif_id, auth_content.get('email' , ''))

    if auth.ALWAYS_LET_ME_IN :
        return payment_info
    elif auth_content['email'] == payment_info['paying_user_email'] :
        return payment_info
    else:
        res.status_code = 401
        return None

@app.get("/vippsecomkey")
async def get_vippsecomkey(req : Request, res : Response):
    """

    This is the most stupid thing ever xD. The Vipps-backend is not configured to respond to SPA's. It's an
    Azure-thing. But it works fine for Postman. And it also works fine here, from our own backend.
    Vipps are doing something wrong here, but we can easily bypass it like this.

    :param req:
    :param res:
    :return:
    """

    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    token = auth.vippsecomkey()
    return token


@app.post("/vippsorderid")
async def post_vippsorderid(req: Request, order : OrderRef, res: Response):
    """
    Receive the order-id info, meaning that the Vipps ecom procedure has initiated, and the client needs something to
    track

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    return UpdatePaymentInfo_vippsOrderId(order.orderId, order.vedbId)

@app.get("/paymentstatus")
async def get_payment_states(req : Request, order : OrderRef, res : Response) :
    """

    Retrieve information about the payment with the argument reference

    :param req:
    :param order:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER=DEBUG_USER):
        res.status_code = 401
        return None

    return {}


@app.put("/vippscancel")
async def put_vippscancel(req: Request, res: Response):
    """
    Receive the order-id info, meaning that the Vipps ecom procedure has initiated, and the client needs something to
    track

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    payid = req.query_params.get('payid', '')
    payment_info = GetPaymentInfo(payid)
    if not payment_info:
        res.status_code = 404
        return
    if payment_info['info']['code'] != 200 :
        res.status_code = payment_info['info']['code']
        return
    ret = UpdatePaymentInfo_paymentStatus('cancelled' , payment_info['mongodb_id'])
    res.status_code = ret['info']['code']
    return ret

@app.put("/company")
async def put_company(req: Request, res: Response):
    """

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    billname = req.query_params.get('billname', '')
    accountnum = req.query_params.get('accountnum', '')
    companyname = req.query_params.get('companyname', '')
    companynum = req.query_params.get('companynum', '')
    companyaddress = req.query_params.get('companyaddress', '')

    ret = UpdateCompany(auth_content['email'], auth_content['phone'], billname, accountnum, companyname, companynum, companyaddress)
    res.status_code = ret['info']['code']
    if res.status_code != 200 :
        return {'error' : ret['info']['content']}
    return ret

@app.get("/company")
async def get_company(req: Request, res: Response):
    """

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    companyname = req.query_params.get('companyname', '')
    companynum = req.query_params.get('companynum', '')

    ret = GetCompany(auth_content['email'], auth_content['phone'], companyname, companynum)
    res.status_code = ret['info']['code']
    if res.status_code != 200 :
        return {'error' : ret['info']['content']}
    return ret



@app.put("/batchsell")
async def put_batchsell(req: Request, res: Response):
    """

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    ret = UpdateBatchSellRequest(auth_content['email'], auth_content['phone'])
    res.status_code = ret['info']['code']
    if res.status_code != 200 :
        return {'error' : ret['info']['content']}
    return ret

@app.get("/batchsell")
async def get_batchsell(req: Request, res: Response):
    """

    :param req:
    :param res:
    :return:
    """
    auth_content = auth.decode_auth_header(req)

    DEBUG_USER = os.getenv('DEBUG_USER', None)
    if DEBUG_USER:
        DEBUG_USER = GetUser(email=DEBUG_USER)

    if not auth.let_me_in(auth_content, DEBUG_USER = DEBUG_USER):
        res.status_code = 401
        return None

    ret = GetBatchSellRequest(auth_content['email'], auth_content['phone'])
    res.status_code = ret['info']['code']
    if res.status_code != 200 :
        return {'error' : ret['info']['content']}
    return ret


if __name__ == "__main__":
    uvicorn.run('main:app', host=HOST, port=PORT)
