"""
LOCK & HIDE - Web Version
Steganography Tool using Flask
Fixed Version - No Garbage Characters
"""

import os
import base64
from io import BytesIO
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_file, session
import secrets

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(img):
    """Convert PIL Image to base64 string"""
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def encode_image(image_path, message, password):
    """Encode message into image - NO GARBAGE VERSION"""
    try:
        # Open image
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        
        # Format data: password + SEPARATOR + message + TERMINATOR
        SEPARATOR = '|||'
        TERMINATOR = '$$$END$$$'
        full_data = password + SEPARATOR + message + TERMINATOR
        
        # Convert to binary
        binary_data = ''.join(format(ord(char), '08b') for char in full_data)
        data_length = len(binary_data)
        
        # Check capacity
        max_bits = width * height * 3
        if data_length > max_bits:
            return None, f"Message too large for this image. Maximum capacity: {max_bits//8} characters."
        
        # Create a copy of image for encoding
        encoded_img = img.copy()
        pixels = encoded_img.load()
        
        # Encode the data
        bit_index = 0
        for y in range(height):
            for x in range(width):
                if bit_index >= data_length:
                    break
                
                r, g, b = pixels[x, y]
                
                # Encode in LSB (Least Significant Bit)
                if bit_index < data_length:
                    r = (r & 0xFE) | int(binary_data[bit_index])
                    bit_index += 1
                
                if bit_index < data_length:
                    g = (g & 0xFE) | int(binary_data[bit_index])
                    bit_index += 1
                
                if bit_index < data_length:
                    b = (b & 0xFE) | int(binary_data[bit_index])
                    bit_index += 1
                
                pixels[x, y] = (r, g, b)
        
        return encoded_img, None
        
    except Exception as e:
        return None, str(e)

def decode_image(image_path, password):
    """Decode message from image - NO GARBAGE VERSION"""
    try:
        # Open image
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        pixels = img.load()
        
        # Extract LSBs from all pixels
        binary_data = ""
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                binary_data += str(r & 1)
                binary_data += str(g & 1)
                binary_data += str(b & 1)
        
        # Convert binary to text, stop at terminator
        chars = []
        found_terminator = False
        
        for i in range(0, len(binary_data), 8):
            if i + 8 > len(binary_data):
                break
            
            # Get 8 bits (1 byte)
            byte = binary_data[i:i+8]
            try:
                # Convert binary to character
                char_code = int(byte, 2)
                char = chr(char_code)
                chars.append(char)
                
                # Check if we found the terminator
                current_text = ''.join(chars)
                if current_text.endswith('$$$END$$$'):
                    # Remove terminator
                    chars = chars[:-9]
                    found_terminator = True
                    break
                    
            except ValueError:
                # Skip invalid bytes
                continue
        
        if not found_terminator:
            return "No hidden message found or invalid image format.", False, None
        
        # Reconstruct the full text
        decoded_text = ''.join(chars)
        
        # Split into password and message
        if '|||' in decoded_text:
            parts = decoded_text.split('|||', 1)  # Split only on first occurrence
            if len(parts) == 2:
                stored_password, hidden_message = parts
                
                # Check password
                if stored_password == password:
                    return hidden_message, True, None
                else:
                    return "Wrong password!", False, None
        
        return "Invalid message format.", False, None
        
    except Exception as e:
        return None, False, str(e)

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/encode', methods=['GET', 'POST'])
def encode():
    """Encode page"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image selected'}), 400
        
        file = request.files['image']
        message = request.form.get('message', '').strip()
        password = request.form.get('password', '').strip()
        
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, BMP, or GIF.'}), 400
        
        if not message:
            return jsonify({'error': 'Please enter a secret message'}), 400
        
        if not password:
            return jsonify({'error': 'Please enter a password'}), 400
        
        try:
            # Save uploaded file
            filename = secrets.token_hex(8) + '.png'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Encode message
            encoded_img, error = encode_image(filepath, message, password)
            
            if error:
                os.remove(filepath)  # Clean up
                return jsonify({'error': error}), 400
            
            # Convert to base64 for preview
            encoded_b64 = image_to_base64(encoded_img)
            
            # Save encoded image
            encoded_filename = 'encoded_' + filename
            encoded_filepath = os.path.join(app.config['UPLOAD_FOLDER'], encoded_filename)
            encoded_img.save(encoded_filepath)
            
            # Store in session for download
            session['encoded_file'] = encoded_filename
            
            # Clean up original file
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'preview': encoded_b64,
                'filename': encoded_filename,
                'message': 'Message encoded successfully!'
            })
            
        except Exception as e:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    
    return render_template('encode.html')

@app.route('/decode', methods=['GET', 'POST'])
def decode():
    """Decode page"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image selected'}), 400
        
        file = request.files['image']
        password = request.form.get('password', '').strip()
        
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use PNG, JPG, JPEG, BMP, or GIF.'}), 400
        
        if not password:
            return jsonify({'error': 'Please enter the password'}), 400
        
        try:
            # Save uploaded file
            filename = secrets.token_hex(8) + '.png'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Decode message
            message, success, error = decode_image(filepath, password)
            
            # Clean up file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if error:
                return jsonify({'error': error}), 400
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'type': 'success'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message,
                    'type': 'error'
                })
            
        except Exception as e:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    
    return render_template('decode.html')

@app.route('/download/<filename>')
def download_file(filename):
    """Download encoded image"""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=f"secret_{filename}")
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup')
def cleanup():
    """Clean up uploaded files (optional)"""
    try:
        import glob
        import time
        files = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*'))
        deleted_count = 0
        for f in files:
            try:
                # Delete files older than 1 hour
                if os.path.getmtime(f) < time.time() - 3600:
                    os.remove(f)
                    deleted_count += 1
            except:
                pass
        return jsonify({'message': f'Cleanup completed. Deleted {deleted_count} old files.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File is too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    print("=" * 60)
    print("LOCK & HIDE - Steganography Web Application")
    print("=" * 60)
    print("Starting server...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Create uploads folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)