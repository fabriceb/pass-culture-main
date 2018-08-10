import secrets
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from models import PcObject
from pprint import pprint

from models.offerer import Offerer
from models.user import User
from models.user_offerer import UserOfferer, RightsType
from tests.conftest import clean_database
from utils.test_utils import API_URL, req, req_with_auth, create_thing_offer, create_user, create_offerer, create_venue, \
    create_stock_with_thing_offer, create_recommendation, create_deposit, create_booking

BASE_DATA = {
              'email': 'toto@btmx.fr',
              'publicName': 'Toto',
              'password': 'toto12345678',
              'contact_ok': 'true'
            }

BASE_DATA_PRO = {
                  'email': 'toto_pro@btmx.fr',
                  'publicName': 'Toto Pro',
                  'password': 'toto12345678',
                  'contact_ok': 'true',
                  'siren': '349974931',
                  'address': '12 boulevard de Pesaro',
                  'postalCode': '92000',
                  'city': 'Nanterre',
                  'name': 'Crédit Coopératif'
                }


def assert_signup_error(data, err_field):
    r_signup = req.post(API_URL + '/users/signup',
                                  json=data)
    assert r_signup.status_code == 400
    error = r_signup.json()
    pprint(error)
    assert err_field in error


@pytest.mark.standalone
@clean_database
def test_signup_should_not_work_without_email(app):
    # Given
    data = BASE_DATA.copy()
    del(data['email'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'email' in error

@pytest.mark.standalone
@clean_database
def test_signup_should_not_work_with_invalid_email(app):
    # Given
    data = BASE_DATA.copy()
    data['email'] = 'toto'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'email' in error


@pytest.mark.standalone
def test_signup_should_not_work_without_publicName():
    # Given
    data = BASE_DATA.copy()
    del(data['publicName'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'publicName' in error


@pytest.mark.standalone
def test_signup_should_not_work_with_publicName_too_short():
    # Given
    data = BASE_DATA.copy()
    data['publicName'] = 't'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'publicName' in error


@pytest.mark.standalone
def test_signup_should_not_work_with_publicName_too_long():
    # Given
    data = BASE_DATA.copy()
    data['publicName'] = 'x'*32

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'publicName' in error


@pytest.mark.standalone
def test_signup_should_not_work_without_password():
    # Given
    data = BASE_DATA.copy()
    del(data['password'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'password' in error


@pytest.mark.standalone
def test_signup_should_not_work_with_invalid_password():
    # Given
    data = BASE_DATA.copy()
    data['password'] = 'short'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'password' in error


@pytest.mark.standalone
def test_signup_should_not_work_without_contact_ok():
    data = BASE_DATA.copy()
    del(data['contact_ok'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'contact_ok' in error


@pytest.mark.standalone
def test_signup_should_not_work_with_invalid_contact_ok():
    data = BASE_DATA.copy()
    data['contact_ok'] = 't'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'contact_ok' in error


@pytest.mark.standalone
@clean_database
def test_signup(app):
    r_signup = req.post(API_URL + '/users/signup',
                        json=BASE_DATA)
    assert r_signup.status_code == 201
    assert 'Set-Cookie' in r_signup.headers


@pytest.mark.standalone
@clean_database
def test_signup_should_not_work_again_with_same_email(app):
    req.post(API_URL + '/users/signup',
                        json=BASE_DATA)

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=BASE_DATA)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'email' in error



@pytest.mark.standalone
def test_get_profile_should_work_only_when_logged_in():
    r = req.get(API_URL + '/users/current')
    assert r.status_code == 401


#def test_14_get_profile_should_not_work_if_account_is_not_validated():
#    r = req_with_auth(email='toto@btmx.fr',
#                      password='toto12345678')\
#                    .get(API_URL + '/users/current')
#    assert r.status_code == 401
#    assert 'pas validé' in r.json()['identifier']


#def test_15_should_not_be_able_to_validate_user_with_wrong_token():
#    r = req_with_auth(email='toto@btmx.fr',
#                      password='toto12345678')\
#                 .get(API_URL + '/validate?modelNames=User&token=123')
#    assert r.status_code == 404


#def test_16_should_be_able_to_validate_user(app):
#    token = User.query\
#                .filter(User.validationToken != None)\
#                .first().validationToken
#    r = req_with_auth().get(API_URL + '/validate?modelNames=User&token='+token)
#    assert r.status_code == 202


@pytest.mark.standalone
@clean_database
def test_get_profile_should_return_the_users_profile_without_password_hash(app):
    user = create_user(email='toto@btmx.fr', public_name='Toto', departement_code='93', password='toto12345678')
    user.save()
    r = req_with_auth(email='toto@btmx.fr',
                      password='toto12345678')\
                 .get(API_URL + '/users/current')
    user_json = r.json()
    print(user_json)
    assert r.status_code == 200
    assert user_json['email'] == 'toto@btmx.fr'
    assert 'password' not in user_json


@pytest.mark.standalone
@clean_database
@patch('connectors.google_spreadsheet.get_authorized_emails_and_dept_codes')
def test_signup_should_not_work_for_user_not_in_exp_spreadsheet(get_authorized_emails_and_dept_codes, app):
    # Given
    get_authorized_emails_and_dept_codes.return_value = (['toto@email.com', 'other@email.com'], ['93', '93'])
    data = BASE_DATA.copy()
    data['email'] = 'unknown@unknown.com'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'email' in error

#TODO
#def test_19_pro_signup_should_not_work_with_invalid_siren():
#    data = BASE_DATA_PRO.copy()
#    data['siren'] = '123456789'
#    assert_signup_error(data, 'siren')


@pytest.mark.standalone
@clean_database
def test_pro_signup_should_not_work_without_offerer_name(app):
    # Given
    data = BASE_DATA_PRO.copy()
    del(data['name'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'name' in error


@pytest.mark.standalone
def test_pro_signup_should_not_work_without_offerer_address():
    data = BASE_DATA_PRO.copy()
    del(data['address'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    print(r_signup.json())
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'address' in error


@pytest.mark.standalone
def test_pro_signup_should_not_work_without_offerer_city():
    data = BASE_DATA_PRO.copy()
    del(data['city'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    print(r_signup.json())
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'city' in error


@pytest.mark.standalone
def test_pro_signup_should_not_work_without_offerer_postal_code():
    data = BASE_DATA_PRO.copy()
    del(data['postalCode'])

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    print(r_signup.json())
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'postalCode' in error


@pytest.mark.standalone
def test_pro_signup_should_not_work_with_invalid_offerer_postal_code():
    data = BASE_DATA_PRO.copy()
    data['postalCode'] = '111'

    # When
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)

    # Then
    print(r_signup.json())
    assert r_signup.status_code == 400
    error = r_signup.json()
    assert 'postalCode' in error


@pytest.mark.standalone
@clean_database
def test_pro_signup_should_create_user_offerer_and_userOfferer(app):
    r_signup = req.post(API_URL + '/users/signup',
                        json=BASE_DATA_PRO)
    assert r_signup.status_code == 201
    assert 'Set-Cookie' in r_signup.headers
    user = User.query\
                         .filter_by(email='toto_pro@btmx.fr')\
                         .first()
    assert user is not None
    offerer = Offerer.query\
                               .filter_by(siren='349974931')\
                               .first()
    assert offerer is not None
    assert offerer.validationToken is not None
    user_offerer = UserOfferer.query\
                                        .filter_by(user=user,
                                                   offerer=offerer)\
                                        .first()
    assert user_offerer is not None
    assert user_offerer.validationToken is None
    assert user_offerer.rights == RightsType.admin


@clean_database
@pytest.mark.standalone
def test_should_not_be_able_to_validate_offerer_with_wrong_token(app):
    user = create_user(email='toto@btmx.fr', public_name='Toto', departement_code='93', password='toto12345678')
    user.save()
    user.validationToken = secrets.token_urlsafe(20)
    r = req_with_auth(email='toto_pro@btmx.fr',
                      password='toto12345678')\
                 .get(API_URL + '/validate?modelNames=Offerer&token=123')
    assert r.status_code == 404


@clean_database
@pytest.mark.standalone
def test_validate_offerer(app):
    # Given
    offerer_token = secrets.token_urlsafe(20)
    offerer = create_offerer('349974931', '12 boulevard de Pesaro', 'Nanterre', '92000', 'Crédit Coopératif',
                             validation_token=offerer_token)
    offerer.save()
    offerer_id = offerer.id
    del(offerer)

    token = Offerer.query\
                             .filter_by(id=offerer_id)\
                             .first().validationToken

    print('token', token)
    print('offerer_token', offerer_token)

    # When
    r = req.get(API_URL + '/validate?modelNames=Offerer&token='+token)

    # Then
    assert r.status_code == 202
    offerer = Offerer.query\
                               .filter_by(id=offerer_id)\
                               .first()
    assert offerer.isValidated


@clean_database
@pytest.mark.standalone
def test_pro_signup_with_existing_offerer(app):
    "should create user and userOfferer"
    json_offerer = {
            "name": "Test Offerer",
            "siren": "349974931",
            "address": "Test adresse",
            "postalCode": "75000",
            "city": "Paris"
    }
    offerer = Offerer(from_dict=json_offerer)
    offerer.save()


    data = BASE_DATA_PRO.copy()
    r_signup = req.post(API_URL + '/users/signup',
                        json=data)
    assert r_signup.status_code == 201
    assert 'Set-Cookie' in r_signup.headers
    user = User.query\
                         .filter_by(email='toto_pro@btmx.fr')\
                         .first()
    assert user is not None
    offerer = Offerer.query\
                               .filter_by(siren='349974931')\
                               .first()
    assert offerer is not None
    user_offerer = UserOfferer.query\
                                        .filter_by(user=user,
                                                   offerer=offerer)\
                                        .first()
    assert user_offerer is not None
    assert user_offerer.validationToken is not None
    assert user_offerer.rights == RightsType.editor


@clean_database
@pytest.mark.standalone
def test_user_should_have_its_wallet_balance(app):
    # Given
    user = create_user(email='wallet_test@email.com', public_name='Test', departement_code='93', password='testpsswd')
    PcObject.check_and_save(user)

    offerer = create_offerer('999199987', '2 Test adress', 'Test city', '93000', 'Test offerer')
    PcObject.check_and_save(offerer)

    venue = create_venue(offerer)
    PcObject.check_and_save(venue)

    thing_offer = create_thing_offer()
    stock = create_stock_with_thing_offer(offerer, venue, thing_offer, price=5)
    PcObject.check_and_save(stock)

    recommendation = create_recommendation(thing_offer, user)
    PcObject.check_and_save(recommendation)

    deposit_1_date = datetime.utcnow() - timedelta(minutes=2)
    deposit_1 = create_deposit(user, deposit_1_date, amount=10)
    PcObject.check_and_save(deposit_1)

    deposit_2_date = datetime.utcnow() - timedelta(minutes=2)
    deposit_2 = create_deposit(user, deposit_2_date, amount=10)
    PcObject.check_and_save(deposit_2)

    booking = create_booking(user, stock, recommendation, quantity=1)
    PcObject.check_and_save(booking)

    r_create = req_with_auth('wallet_test@email.com', 'testpsswd').get(API_URL + '/users/current')

    # when
    wallet_balance = r_create.json()['wallet_balance']

    #Then
    assert wallet_balance == 15


@pytest.mark.standalone
def test_user_with_isAdmin_true_and_canBookFreeOffers_raises_error():
    # Given
    user_json = {
        'email': 'pctest.isAdmin.canBook@btmx.fr',
        'publicName': 'IsAdmin CanBook',
        'password': 'toto12345678',
        'contact_ok': 'true',
        'isAdmin': True,
        'canBookFreeOffers': True
    }

    # When
    r_signup = req.post(API_URL + '/users/signup',
                                  json=user_json)

    # Then
    assert r_signup.status_code == 400
    error = r_signup.json()
    pprint(error)
    assert error == {'canBookFreeOffers': ['Admin ne peut pas booker']}


@clean_database
@pytest.mark.standalone
def test_user_wallet_should_be_30_if_sum_deposit_50_and_one_booking_quantity_2_amount_10(app):
    # Given
    user = create_user(email='wallet_2_bookings_test@email.com', public_name='Test', departement_code='93', password='testpsswd')
    PcObject.check_and_save(user)

    offerer = create_offerer('999199987', '2 Test adress', 'Test city', '93000', 'Test offerer')
    PcObject.check_and_save(offerer)

    venue = create_venue(offerer)
    PcObject.check_and_save(venue)

    thing_offer = create_thing_offer()
    stock = create_stock_with_thing_offer(offerer, venue, thing_offer, price=10)
    PcObject.check_and_save(stock)

    recommendation = create_recommendation(thing_offer, user)
    PcObject.check_and_save(recommendation)

    deposit_date = datetime.utcnow() - timedelta(minutes=2)
    deposit = create_deposit(user, deposit_date, amount=50)
    PcObject.check_and_save(deposit)

    booking = create_booking(user, stock, recommendation, quantity=2)
    PcObject.check_and_save(booking)

    # When
    r_create = req_with_auth('wallet_2_bookings_test@email.com', 'testpsswd').get(API_URL + '/users/current')

    # Then
    wallet_balance = r_create.json()['wallet_balance']
    assert wallet_balance == 30