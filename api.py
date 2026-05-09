import requests
from re import search
from typing import Any, Dict, List

class NPMClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None
        self.login()

    def login(self) -> str:
        url = f"{self.base_url}/api/tokens"
        r = self.session.post(url, json={"identity": self.username, "secret": self.password}, timeout=self.timeout)
        r.raise_for_status()
        j = r.json()
        token = j.get('token') or j.get('data', {}).get('token')
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.session.headers.pop("Cookie", None)
            return token
        set_cookie = r.headers.get('Set-Cookie', '')
        cookies = search(r'token=([^;]+)', set_cookie)
        if cookies:
            cookie_token = cookies.group(1)
            self.cookie = f"token={cookie_token}; __Host-Http-token={cookie_token}"
            self.session.headers.update({"Cookie": self.cookie})
            self.session.headers.pop("Authorization", None)
            return self.cookie
        raise RuntimeError(f'Authentication failed. Failed to obtain token from NPM.')

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]):
        url = f"{self.base_url}{path}"
        r = self.session.post(url, json=payload, timeout=self.timeout)
        # do not always call raise_for_status here to surface json error messages
        try:
            r.raise_for_status()
            return r.json()
        except Exception:
            return r.text or r.json()

    def _put(self, path: str, payload: Dict[str, Any]):
        url = f"{self.base_url}{path}"
        r = self.session.put(url, json=payload, timeout=self.timeout)
        try:
            r.raise_for_status()
            return r.json()
        except Exception:
            return r.text or r.json()

    def get_proxy_hosts(self) -> List[Dict[str, Any]]:
        # API may return object with {data: []} or an array directly. Normalize.
        raw = self._get('/api/nginx/proxy-hosts')
        if isinstance(raw, dict) and 'data' in raw:
            return raw['data']
        if isinstance(raw, list):
            return raw
        # Some versions return { 'items': [...] }
        if isinstance(raw, dict):
            for k in ('items','hosts'):
                if k in raw and isinstance(raw[k], list):
                    return raw[k]
        raise RuntimeError('Unexpected response for proxy-hosts: %r' % raw)

    def create_proxy_host(self, payload: Dict[str, Any]):
        return self._post('/api/nginx/proxy-hosts', payload)

    def update_proxy_host(self, host_id: int, payload: Dict[str, Any]):
        return self._put(f'/api/nginx/proxy-hosts/{host_id}', payload)

    def delete_proxy_host(self, host_id: int):
        url = f"{self.base_url}/api/nginx/proxy-hosts/{host_id}"
        r = self.session.delete(url, timeout=self.timeout)
        r.raise_for_status()
        return r.text
