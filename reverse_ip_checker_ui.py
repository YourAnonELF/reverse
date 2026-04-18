import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from reverse_ip_checker import check_reverse_ip_domain, validate_ip


HTML_PAGE = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Reverse-IP Domain Checker</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 75ch; margin: 2rem auto; padding: 0 1rem; }
    form { display: grid; gap: .75rem; margin-bottom: 1rem; }
    input { padding: .5rem; font-size: 1rem; }
    button { padding: .6rem .9rem; cursor: pointer; }
    pre { background: #f5f5f5; padding: 1rem; border-radius: 6px; overflow: auto; }
    .error { color: #b00020; }
  </style>
</head>
<body>
  <h1>Reverse-IP Domain Checker</h1>
  <form id=\"checker-form\">
    <label>IP Address (required)
      <input id=\"ip\" name=\"ip\" placeholder=\"8.8.8.8\" required />
    </label>
    <label>Domain (optional)
      <input id=\"domain\" name=\"domain\" placeholder=\"example.com\" />
    </label>
    <button type=\"submit\">Check</button>
  </form>
  <p id=\"error\" class=\"error\"></p>
  <pre id=\"output\">Run a check to see results.</pre>

  <script>
    const form = document.getElementById('checker-form');
    const error = document.getElementById('error');
    const output = document.getElementById('output');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      error.textContent = '';
      output.textContent = 'Checking...';

      const ip = document.getElementById('ip').value.trim();
      const domain = document.getElementById('domain').value.trim();
      const params = new URLSearchParams({ ip });
      if (domain) params.set('domain', domain);

      try {
        const response = await fetch('/api/check?' + params.toString());
        const data = await response.json();
        if (!response.ok) {
          error.textContent = data.error || 'Request failed';
          output.textContent = 'No results.';
          return;
        }
        output.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        error.textContent = 'Failed to reach server';
        output.textContent = 'No results.';
      }
    });
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/check":
            query = parse_qs(parsed.query)
            ip = (query.get("ip") or [""])[0].strip()
            domain = (query.get("domain") or [""])[0].strip() or None

            try:
                validate_ip(ip)
            except ValueError:
                return self._send_json({"error": "Invalid IP address"}, status=400)

            result = check_reverse_ip_domain(ip, domain)
            return self._send_json(result)

        self._send_json({"error": f"Not found: {html.escape(parsed.path)}"}, status=404)

    def log_message(self, *_):
        """Suppress default HTTP request logging to keep console output clean."""
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reverse-IP domain checker (UI tool)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving Reverse-IP UI at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
