import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template, abort
from werkzeug.utils import secure_filename
import magic
from PIL import Image
import uuid
import ipaddress
from config import ALLOWED_IPS, FILE_ACCESS_ENABLED

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_filename(original_filename):
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = str(uuid.uuid4())[:8]
    date_prefix = datetime.now().strftime('%Y%m%d')
    return f"{date_prefix}_{unique_id}.{ext}"

def create_thumbnail(filepath, filename):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        thumb_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails')
        os.makedirs(thumb_dir, exist_ok=True)
        
        with Image.open(filepath) as img:
            img.thumbnail((200, 200))
            thumb_path = os.path.join(thumb_dir, filename)
            img.save(thumb_path)
            return True
    return False

def is_ip_allowed(ip):
    if not FILE_ACCESS_ENABLED:
        return True
    
    client_ip = ipaddress.ip_address(ip)
    
    for allowed_ip in ALLOWED_IPS:
        try:
            # Check if it's a CIDR range
            if '/' in allowed_ip:
                network = ipaddress.ip_network(allowed_ip, strict=False)
                if client_ip in network:
                    return True
            # Check if it's a single IP
            else:
                if client_ip == ipaddress.ip_address(allowed_ip):
                    return True
        except ValueError:
            # Skip invalid IP addresses or ranges
            continue
    
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    client_ip = request.remote_addr
    if not is_ip_allowed(client_ip):
        app.logger.warning(f"Access denied for IP: {client_ip}")
        abort(403, description=f"Access denied. Your IP {client_ip} is not whitelisted.") 
    
    if file and allowed_file(file.filename):
        filename = generate_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create thumbnail if it's an image
        has_thumbnail = create_thumbnail(filepath, filename)
        
        file_url = request.host_url.rstrip('/') + '/files/' + filename
        return jsonify({
            'success': True,
            'url': file_url,
            'filename': filename,
            'has_thumbnail': has_thumbnail
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/files/<filename>')
def serve_file(filename):
    client_ip = request.remote_addr
    
    if not is_ip_allowed(client_ip):
        app.logger.warning(f"Access denied for IP: {client_ip} trying to access file: {filename}")
        abort(403, description="Access denied. Your IP is not whitelisted.")
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    client_ip = request.remote_addr
    
    if not is_ip_allowed(client_ip):
        app.logger.warning(f"Access denied for IP: {client_ip} trying to access thumbnail: {filename}")
        abort(403, description="Access denied. Your IP is not whitelisted.")
    
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8888) 