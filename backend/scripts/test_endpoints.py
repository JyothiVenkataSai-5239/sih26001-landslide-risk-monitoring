import urllib.request
import json

BASE = 'http://127.0.0.1:8000'
paths = [
    '/health',
    '/api/risk/coarse',
    '/api/risk/fine',
    '/api/forecast',
    '/api/hotspots',
    '/api/alerts',
]

def fetch(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            status = r.getcode()
            body = r.read(4000).decode('utf-8')
            try:
                parsed = json.loads(body)
                snippet = json.dumps(parsed if isinstance(parsed, dict) else (parsed[:5] if isinstance(parsed, list) else parsed), indent=2)[:800]
            except Exception:
                snippet = body[:800]
            return status, snippet
    except urllib.error.HTTPError as e:
        try:
            body = e.read(4000).decode('utf-8')
        except Exception:
            body = ''
        return e.code, body[:800]
    except Exception as e:
        return None, str(e)


if __name__ == '__main__':
    for p in paths:
        st, sn = fetch(p)
        print('PATH:', p)
        print('STATUS:', st)
        print('SNIPPET:')
        print(sn)
        print('-' * 80)

    # Filters
    filters = [
        '/api/risk/coarse?risk_tier=HIGH',
        '/api/forecast?forecast_horizon=+24h',
        '/api/alerts?alert_severity=VERY%20HIGH'
    ]
    for p in filters:
        st, sn = fetch(p)
        print('FILTER PATH:', p)
        print('STATUS:', st)
        print('SNIPPET:')
        print(sn)
        print('-' * 80)
