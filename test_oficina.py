from app import create_app
from flask import session
import traceback

app = create_app()

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['rol'] = 'OFICINA'
        
    try:
        response = client.get('/dashboard/oficina')
        print("Status:", response.status_code)
        if response.status_code == 500:
            print(response.data.decode('utf-8'))
    except Exception as e:
        traceback.print_exc()
