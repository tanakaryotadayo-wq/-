import argparse
import json
import logging
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        modified_body = body
        if body:
            try:
                data = json.loads(body.decode('utf-8'))

                if isinstance(data, dict):
                    if 'systemInstruction' not in data:
                        data['systemInstruction'] = {}
                    if 'parts' not in data['systemInstruction']:
                        data['systemInstruction']['parts'] = []

                    if isinstance(data['systemInstruction']['parts'], list):
                        data['systemInstruction']['parts'].append({
                            "text": "\n\n[COMPLIANCE OVERRIDE]: 絶対に日本語で応答・思考・ツール出力を行え。You must execute, think, and output tools entirely in Japanese."
                        })
                        modified_body = json.dumps(data).encode('utf-8')
                        logging.info("Injected compliance override into systemInstruction.parts")
            except json.JSONDecodeError:
                logging.warning("Failed to decode JSON payload")
            except Exception as e:
                logging.error(f"Error modifying payload: {e}")

        upstream_url = self.server.upstream + self.path

        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ['host', 'content-length']:
                headers[key] = value

        headers['Content-Length'] = str(len(modified_body))

        req = urllib.request.Request(upstream_url, data=modified_body, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            logging.error(f"Error forwarding request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

    def do_GET(self):
        self.forward_request('GET')

    def do_PUT(self):
        self.forward_request('PUT')

    def do_DELETE(self):
        self.forward_request('DELETE')

    def do_PATCH(self):
        self.forward_request('PATCH')

    def forward_request(self, method):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        upstream_url = self.server.upstream + self.path

        headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ['host']:
                headers[key] = value

        req = urllib.request.Request(upstream_url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for key, value in e.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            logging.error(f"Error forwarding request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

def run(port, upstream):
    server_address = ('', port)
    httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)
    httpd.upstream = upstream.rstrip('/')
    logging.info(f"Starting proxy on port {port}, upstream: {httpd.upstream}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping proxy")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Neural Override Proxy for Gemini API')
    parser.add_argument('--port', type=int, default=18008, help='Port to run the proxy on')
    parser.add_argument('--upstream', type=str, default='https://generativelanguage.googleapis.com', help='Upstream URL to forward requests to')

    args = parser.parse_args()
    run(args.port, args.upstream)
