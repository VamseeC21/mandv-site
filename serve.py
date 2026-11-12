#!/usr/bin/env python3
"""Local static server with HTTP Range support so video seeking works."""
import argparse
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class RangeRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if path.endswith("/"):
            self.send_error(404, "File not found")
            return None
        try:
            file = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        fs = os.fstat(file.fileno())
        size = fs.st_size
        ctype = self.guess_type(path)
        last_mod = self.date_time_string(fs.st_mtime)
        self.range = None

        match = re.match(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        if match:
            start = int(match.group(1)) if match.group(1) else None
            end = int(match.group(2)) if match.group(2) else None
            if start is None and end is not None:
                start = max(size - end, 0)
                end = size - 1
            elif start is not None and end is None:
                end = size - 1
            if start is None or end is None or start > end or start >= size:
                file.close()
                self.send_error(416, "Requested Range Not Satisfiable")
                return None
            end = min(end, size - 1)
            self.range = (start, end)
            file.seek(start)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(size))

        self.send_header("Content-Type", ctype)
        self.send_header("Last-Modified", last_mod)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Connection", "close")
        self.end_headers()
        return file

    def copyfile(self, source, outputfile):
        if not self.range:
            super().copyfile(source, outputfile)
            return
        remaining = self.range[1] - self.range[0] + 1
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    os.chdir(ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), RangeRequestHandler)
    print(f"Serving {ROOT} at http://127.0.0.1:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
