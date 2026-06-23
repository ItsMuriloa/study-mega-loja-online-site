from urllib.parse import parse_qsl, urlencode, urlparse

from backend.api import ApiHandler
from backend.database import init_db


class handler(ApiHandler):
    def prepare_path(self):
        init_db()
        parsed = urlparse(self.path)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        rewritten_path = query.pop("path", None)

        if rewritten_path is not None:
            path = f"/api/{rewritten_path}".rstrip("/")
            remaining_query = urlencode(query)
            self.path = f"{path}?{remaining_query}" if remaining_query else path

    def do_OPTIONS(self):
        self.prepare_path()
        super().do_OPTIONS()

    def do_GET(self):
        self.prepare_path()
        super().do_GET()

    def do_POST(self):
        self.prepare_path()
        super().do_POST()

    def do_PATCH(self):
        self.prepare_path()
        super().do_PATCH()
