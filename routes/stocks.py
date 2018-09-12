""" stocks """
from pprint import pformat
from flask import current_app as app, jsonify, request
from flask_login import current_user
from sqlalchemy.exc import InternalError

from domain.stocks import find_offerer_for_new_stock, soft_delete_stock
from models.api_errors import ApiErrors
from models.event import Event
from models.event_occurrence import EventOccurrence
from models.offer import Offer
from models.stock import Stock
from models.pc_object import PcObject
from models.thing import Thing
from models.user_offerer import RightsType
from models.venue import Venue
from repository import stock_queries
from repository.stock_queries import save_stock
from utils.human_ids import dehumanize
from utils.rest import ensure_current_user_has_rights, \
    expect_json_data, \
    handle_rest_get_list, \
    load_or_404, \
    login_or_api_key_required
from utils.search import LANGUAGE
from validation.stocks import check_offer_id_xor_event_occurrence_id_in_request

search_models = [
    # Order is important
    Thing,
    Venue,
    Event
]


def join_stocks(query):
    for search_model in search_models:
        if search_model == Event:
            query = query.outerjoin(EventOccurrence).join(Offer).outerjoin(search_model)
        else:
            query = query.join(Offer).outerjoin(search_model)
    return query


def query_stocks(ts_query):
    return or_(
        *[
            model.__ts_vector__.match(
                ts_query,
                postgresql_regconfig=LANGUAGE
            )
            for model in search_models
        ]
    )


@app.route('/stocks', methods=['GET'])
@login_or_api_key_required
def list_stocks():
    filters = request.args.copy()
    return handle_rest_get_list(Stock,
                                query=stock_queries.find_stocks_with_possible_filters(filters, current_user),
                                paginate=50)


@app.route('/stocks/<stock_id>',
           methods=['GET'],
           defaults={'mediation_id': None})
@app.route('/stocks/<stock_id>/<mediation_id>', methods=['GET'])
def get_stock(stock_id, mediation_id):
    filters = request.args.copy()
    query = stock_queries.find_stocks_with_possible_filters(filters, current_user).filter_by(id=dehumanize(stock_id))
    if stock_id == '0':
        stock = {'id': '0',
                 'thing': {'id': '0',
                           'mediations': [mediation]}}
        return jsonify(stock)
    else:
        stock = query.first_or_404()
        return jsonify(stock._asdict())


@app.route('/stocks', methods=['POST'])
@login_or_api_key_required
@expect_json_data
def create_stock():
    stock_dict = request.json
    check_offer_id_xor_event_occurrence_id_in_request(stock_dict)
    offer_id = dehumanize(stock_dict.get('offerId', None))
    event_occurrence_id = dehumanize(stock_dict.get('eventOccurrenceId', None))
    offerer = find_offerer_for_new_stock(offer_id, event_occurrence_id)
    ensure_current_user_has_rights(RightsType.editor, offerer.id)
    stock_json = request.json
    if event_occurrence_id:
        del(stock_json['offerId'])
    new_stock = Stock(from_dict=stock_json)
    stock_queries.save_stock(new_stock)
    return jsonify(new_stock._asdict()), 201


@app.route('/stocks/<stock_id>', methods=['PATCH'])
@login_or_api_key_required
@expect_json_data
def edit_stock(stock_id):
    updated_stock_dict = request.json
    query = Stock.queryNotSoftDeleted().filter_by(id=dehumanize(stock_id))
    stock = query.first_or_404()
    offerer_id = stock.resolvedOffer.venue.managingOffererId
    ensure_current_user_has_rights(RightsType.editor, offerer_id)
    stock.populateFromDict(updated_stock_dict)
    stock_queries.save_stock(stock)
    return jsonify(stock._asdict()), 200


@app.route('/stocks/<id>', methods=['DELETE'])
@login_or_api_key_required
def delete_stock(id):
    stock = load_or_404(Stock, id)
    offerer_id = stock.resolvedOffer.venue.managingOffererId
    ensure_current_user_has_rights(RightsType.editor,
                                   offerer_id)

    stock_and_bookings_to_save = soft_delete_stock(stock)

    PcObject.check_and_save(*stock_and_bookings_to_save)

    return jsonify(stock._asdict()), 200
