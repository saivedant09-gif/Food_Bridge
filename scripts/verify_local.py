"""Verify local APIs. --write-demo also writes clearly labelled workflow/demo records."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:8000'


def call(path, method='GET', body=None, expected=200):
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=payload, method=method,
                                     headers={'Content-Type': 'application/json'} if payload else {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status, data = response.status, json.load(response)
    except urllib.error.HTTPError as response:
        status, data = response.code, json.load(response)
    assert status == expected, f'{method} {path}: expected {expected}, got {status}: {data}'
    return data


def verify(write_demo=False):
    assert call('/health')['status'] == 'ready'
    users = call('/users')
    donor = next(user for user in users if user['role'] == 'DONOR')
    ngo = next(user for user in users if user['role'] == 'NGO')
    assert all(user['role'] == 'DONOR' for user in call('/users?role=DONOR'))
    assert all(user['role'] == 'NGO' for user in call('/users?role=NGO'))
    food = call('/food')
    requests = call('/requests')
    assert 'reviews' in call('/reviews')
    call('/requests', 'POST', {'food_id': 0, 'ngo_id': ngo['user_id'], 'requested_quantity': -1}, expected=422)
    print(f'PASS: both databases, {len(users)} users, {len(food)} food listings, {len(requests)} requests, reviews, validation', flush=True)
    if not write_demo:
        return
    now = datetime.now().replace(microsecond=0)
    label = 'Local workflow check ' + now.strftime('%Y%m%d-%H%M%S')
    food_body = {'donor_id': donor['user_id'], 'food_name': label, 'quantity': 20,
                 'unit': 'portions', 'prepared_at': now.isoformat(),
                 'pickup_deadline': (now + timedelta(days=7)).isoformat()}
    call('/food', 'POST', {**food_body, 'donor_id': ngo['user_id']}, expected=400)
    call('/food', 'POST', {**food_body, 'quantity': 0.001}, expected=422)
    food_id = call('/food', 'POST', food_body, expected=201)['food_id']
    def stock():
        return next(item for item in call('/food') if item['food_id'] == food_id)
    def request(amount):
        return call('/requests', 'POST', {'food_id': food_id, 'ngo_id': ngo['user_id'], 'requested_quantity': amount}, expected=201)['request_id']
    request_id = request(6)
    assert call(f'/requests/{request_id}/approve','PUT')['remaining_quantity'] == 14
    call(f'/requests/{request_id}/approve','PUT',expected=400)
    call(f'/requests/{request_id}/collect','POST',{'collected_quantity': 7},expected=400)
    result = call(f'/requests/{request_id}/collect','POST',{'collected_quantity': 4,'notes':'Local verification: partial pickup'},expected=201)
    assert result['released_quantity'] == 2 and stock()['available_quantity'] == 16
    call(f'/requests/{request_id}/collect','POST',{'collected_quantity': 1},expected=400)
    rejected = request(5)
    assert call(f'/requests/{rejected}/reject','PUT')['status'] == 'REJECTED'
    assert stock()['available_quantity'] == 16
    call('/requests','POST',{'food_id':food_id,'ngo_id':ngo['user_id'],'requested_quantity':17},expected=400)
    completed = request(16)
    assert call(f'/requests/{completed}/approve','PUT')['remaining_quantity'] == 0
    assert stock()['status'] == 'RESERVED'
    call(f'/requests/{completed}/collect','POST',{'collected_quantity':16,'notes':'Local verification: final pickup'},expected=201)
    assert stock()['status'] == 'COMPLETED' and stock()['available_quantity'] == 0
    print('PASS: publish, request, approve, partial collection/stock release, rejection, final collection, duplicate and quantity errors', flush=True)
    review = call('/reviews','POST',{'food_id':food_id,'food_name':label,'reviewer_ngo':ngo['name'],
                 'rating':5,'feedback':'Local end-to-end verification: donation collected and stock accounting confirmed.',
                 'quantity_received':4,'review_date':now.date().isoformat()})
    assert any(item['food_name'] == label for item in call(f'/reviews/{food_id}')['reviews'])
    call('/reviews','POST',{'food_id':food_id,'food_name':label,'reviewer_ngo':ngo['name'],
         'rating':6,'feedback':'Invalid rating','quantity_received':1,'review_date':now.date().isoformat()},expected=422)
    print('PASS: MongoDB review write, filter, and rating validation', flush=True)
    expired = next((item for item in food if item['status']=='AVAILABLE' and datetime.fromisoformat(item['pickup_deadline']) <= now),None)
    if expired:
        call('/requests','POST',{'food_id':expired['food_id'],'ngo_id':ngo['user_id'],'requested_quantity':1},expected=400)
        print('PASS: expired food cannot be requested', flush=True)
    live = call('/food','POST',{**food_body,'food_name':'Vegetable rice (local demo)','quantity':24},expected=201)
    record = {'workflow_food_id':food_id,'request_ids':[request_id,rejected,completed],
              'review_id':review['review_id'],'available_demo_food_id':live['food_id'],'verified_at':now.isoformat()}
    output=Path(__file__).resolve().parents[1]/'.local'/'verification.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(f'PASS: created clearly labelled available local demo food #{live["food_id"]}; verification IDs saved under .local/', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-demo', action='store_true')
    verify(parser.parse_args().write_demo)
