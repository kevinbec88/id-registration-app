#!/usr/bin/env python3
"""
Simple web server for the registration website.

This server handles:
 - Serving static files (CSS, images, JS) under /static/
 - Serving uploaded ID images under /uploads/
 - Displaying the registration form (index.html)
 - Processing form submissions and saving uploaded images
 - Storing registration info in a CSV file
 - Displaying an admin page listing registrations

The server uses only Python's standard library modules, so it can run
without installing any third‑party dependencies.
"""

import http.server
import socketserver
import os
import urllib.parse
import cgi
import csv
import shutil
import datetime
import uuid

# Define directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
DATABASE_FILE = os.path.join(BASE_DIR, 'registrations.csv')

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


class RegistrationHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler for the registration app."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Serve static files (CSS, images)
        if path.startswith('/static/'):
            self.serve_static(path)
            return
        # Serve uploaded files
        if path.startswith('/uploads/'):
            self.serve_upload(path)
            return
        # Home page (registration form)
        if path == '/' or path == '/index.html':
            # Check for error message in query params
            params = urllib.parse.parse_qs(parsed_path.query)
            error_msg = params.get('error', [''])[0]
            self.render_index(error_msg)
            return
        # Admin page
        if path == '/admin':
            self.render_admin()
            return
        # Unknown path -> 404
        self.send_error(404, "File Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/register':
            self.handle_registration()
        else:
            self.send_error(404, "File Not Found")

    # Utility functions
    def serve_static(self, path):
        """Serve static files from the static directory."""
        file_path = os.path.join(STATIC_DIR, path[len('/static/'):])
        if os.path.isdir(file_path):
            self.send_error(403, "Forbidden")
            return
        if not os.path.exists(file_path):
            self.send_error(404, "Not Found")
            return
        self.send_response(200)
        mime_type = self.guess_type(file_path)
        self.send_header('Content-Type', mime_type)
        self.end_headers()
        with open(file_path, 'rb') as f:
            shutil.copyfileobj(f, self.wfile)

    def serve_upload(self, path):
        """Serve uploaded files from the upload directory."""
        file_path = os.path.join(UPLOAD_DIR, path[len('/uploads/'):])
        if not os.path.exists(file_path):
            self.send_error(404, "Not Found")
            return
        self.send_response(200)
        mime_type = self.guess_type(file_path)
        self.send_header('Content-Type', mime_type)
        self.end_headers()
        with open(file_path, 'rb') as f:
            shutil.copyfileobj(f, self.wfile)

    def render_index(self, error_message=''):
        """Render the registration form with an optional error message."""
        template_path = os.path.join(TEMPLATE_DIR, 'index.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if error_message:
            error_html = f'<div class="flash-messages"><li>{cgi.escape(error_message)}</li></div>'
        else:
            error_html = ''
        content = content.replace('{error_message}', error_html)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def render_success(self, first_name, last_name):
        """Render the success page after registration."""
        template_path = os.path.join(TEMPLATE_DIR, 'success.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('{first_name}', cgi.escape(first_name))
        content = content.replace('{last_name}', cgi.escape(last_name))
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def render_admin(self):
        """Render the admin page listing all registrations."""
        entries = []
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    entries.append(row)
        # Build HTML table
        if entries:
            rows_html = [
                '<table class="admin-table">\n'
                '  <thead><tr><th>Timestamp</th><th>First Name</th><th>Last Name</th><th>ID Type</th><th>ID Front</th><th>ID Back</th></tr></thead>\n'
                '  <tbody>'
            ]
            for entry in entries:
                timestamp = cgi.escape(entry['timestamp'])
                first_name = cgi.escape(entry['first_name'])
                last_name = cgi.escape(entry['last_name'])
                id_type = cgi.escape(entry['id_type'])
                front = urllib.parse.quote(entry['front_filename'])
                back = urllib.parse.quote(entry['back_filename'])
                row = (
                    f'<tr>'
                    f'<td>{timestamp}</td>'
                    f'<td>{first_name}</td>'
                    f'<td>{last_name}</td>'
                    f'<td>{id_type}</td>'
                    f'<td><a href="/uploads/{front}" target="_blank">'
                    f'<img src="/uploads/{front}" alt="ID front" class="thumb"></a></td>'
                    f'<td><a href="/uploads/{back}" target="_blank">'
                    f'<img src="/uploads/{back}" alt="ID back" class="thumb"></a></td>'
                    f'</tr>'
                )
                rows_html.append(row)
            rows_html.append('  </tbody>\n</table>')
            table_html = '\n'.join(rows_html)
        else:
            table_html = '<p>No registrations yet.</p>'
        # Load template and insert table
        template_path = os.path.join(TEMPLATE_DIR, 'admin.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('{table_rows}', table_html)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def handle_registration(self):
        """Process form submission, validate inputs, save files, and record data."""
        content_type = self.headers.get('content-type')
        if not content_type:
            self.redirect_with_error('Missing Content-Type header.')
            return
        # Parse form data using cgi
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type},
        )
        # Retrieve fields
        first_name = form.getvalue('first_name', '').strip()
        last_name = form.getvalue('last_name', '').strip()
        id_type = form.getvalue('id_type', '').strip()
        # Basic validation
        if not first_name or not last_name or not id_type:
            self.redirect_with_error('Please complete all required fields.')
            return
        # Retrieve files
        front_file = form['id_front'] if 'id_front' in form else None
        back_file = form['id_back'] if 'id_back' in form else None
        # Validate files
        if not front_file or not front_file.filename:
            self.redirect_with_error('Please upload a valid front image file.')
            return
        if not back_file or not back_file.filename:
            self.redirect_with_error('Please upload a valid back image file.')
            return
        # Check file extensions
        def allowed(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}
        if not allowed(front_file.filename):
            self.redirect_with_error('Front image must be a PNG/JPG/JPEG/GIF file.')
            return
        if not allowed(back_file.filename):
            self.redirect_with_error('Back image must be a PNG/JPG/JPEG/GIF file.')
            return
        # Generate unique filenames
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        # Use uuid4 to further ensure uniqueness
        unique_id = uuid.uuid4().hex
        front_filename = f"{timestamp}_{unique_id}_front_{os.path.basename(front_file.filename)}"
        back_filename = f"{timestamp}_{unique_id}_back_{os.path.basename(back_file.filename)}"
        # Save files to UPLOAD_DIR
        front_path = os.path.join(UPLOAD_DIR, front_filename)
        back_path = os.path.join(UPLOAD_DIR, back_filename)
        try:
            with open(front_path, 'wb') as f:
                shutil.copyfileobj(front_file.file, f)
            with open(back_path, 'wb') as f:
                shutil.copyfileobj(back_file.file, f)
        except Exception as e:
            self.redirect_with_error('Failed to save uploaded files.')
            return
        # Record registration in CSV
        file_exists = os.path.exists(DATABASE_FILE)
        try:
            with open(DATABASE_FILE, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['timestamp', 'first_name', 'last_name', 'id_type', 'front_filename', 'back_filename'])
                writer.writerow([
                    datetime.datetime.now().isoformat(),
                    first_name,
                    last_name,
                    id_type,
                    front_filename,
                    back_filename
                ])
        except Exception as e:
            self.redirect_with_error('Failed to record registration data.')
            return
        # Render success page
        self.render_success(first_name, last_name)

    def redirect_with_error(self, message):
        """Redirect back to the index page with an error message."""
        # Encode the error in the query string
        encoded = urllib.parse.quote(message)
        self.send_response(303)
        self.send_header('Location', f'/?error={encoded}')
        self.end_headers()


def run(server_class=http.server.HTTPServer, handler_class=RegistrationHTTPRequestHandler, port=8000):
    """Run the HTTP server."""
    server_address = ('', port)
    with server_class(server_address, handler_class) as httpd:
        print(f"Serving on port {port}...")
        httpd.serve_forever()


if __name__ == '__main__':
    run()