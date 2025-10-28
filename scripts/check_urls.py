import requests
urls=['http://127.0.0.1:8000/','http://127.0.0.1:8000/sponsor/','http://127.0.0.1:8000/dashboard/']
for u in urls:
    try:
        r=requests.get(u, allow_redirects=True, timeout=5)
        print(u, r.status_code, len(r.text))
    except Exception as e:
        print(u, 'ERROR', e)
