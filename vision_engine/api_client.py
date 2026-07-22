import queue
import threading
import requests


class AsyncAPIClient:
    """Non-blocking HTTP client for engine -> Django API calls."""

    def __init__(self, api_token=None):
        self.api_token = api_token
        self._queue = queue.Queue(maxsize=200)
        self._running = True
        self._worker = threading.Thread(target=self._process, daemon=True)
        self._worker.start()

    def _headers(self):
        headers = {}
        if self.api_token:
            headers["X-Engine-Token"] = self.api_token
        return headers

    def enqueue(self, url, payload):
        try:
            self._queue.put_nowait((url, payload))
        except queue.Full:
            pass

    def _process(self):
        while self._running:
            try:
                url, payload = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                response = requests.post(url, json=payload, headers=self._headers(), timeout=5)
                if response.status_code != 200:
                    print(f"API error {url}: {response.text}")
            except Exception as e:
                print(f"API request failed {url}: {e}")
            finally:
                self._queue.task_done()

    def stop(self):
        self._running = False
