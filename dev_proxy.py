from flask import Flask, request, jsonify, send_from_directory
import requests
import os

# --- Configuration ---
# The URL where your actual API is running (live instance)
LIVE_API_URL = "http://weather.cubelime.com" 
PROXY_PORT = 5005 # Port for the local dev proxy server

app = Flask(__name__, static_folder='app/static')

@app.after_request
def add_cors_headers(response):
    """Adds permissive CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/')
def serve_spa():
    """Serves the main SPA index.html file."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:subpath>')
def serve_static(subpath):
    """Serves static assets (CSS, JS) from the app/static directory."""
    # Check if it's a known API endpoint first
    if subpath.startswith('api/'):
        return proxy_request(subpath[4:]) # Strip 'api/' prefix for internal routing logic
    
    # Otherwise, treat it as a static file request
    return send_from_directory(app.static_folder, subpath)

@app.route('/api/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_request(subpath):
    """Proxy endpoint for all API calls to the live server."""
    full_url = f"{LIVE_API_URL}/api/{subpath}"
    method = request.method

    # Handle preflight OPTIONS requests first
    if method == 'OPTIONS':
        return jsonify(), 200

    try:
        # Prepare data payload for the upstream API
        data = request.get_json(silent=True) or {}
        params = dict(request.args)

        # Forward the request to the actual target API
        upstream = requests.request(
            method, 
            full_url, 
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }, 
            data=data, 
            params=params
        )

        # Return just the body and status — don't proxy raw upstream headers
        # (they can contain Transfer-Encoding, Content-Encoding, etc. that
        #  conflict with Flask's own response handling)
        return upstream.content, upstream.status_code, {'Content-Type': 'application/json'}

    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Could not connect to the live API at {LIVE_API_URL}. Is it running?"}), 503, {'Content-Type': 'application/json'}
    except Exception as e:
        print(f"Proxy Error: {e}")
        return jsonify({"error": f"An unexpected error occurred in the proxy: {str(e)}"}), 500, {'Content-Type': 'application/json'}

if __name__ == '__main__':
    # This block allows running the script directly for testing
    print("--- Starting Development Proxy ---")
    print(f"Proxy listening on http://localhost:{PROXY_PORT}")
    print(f"Serving SPA from: {os.path.abspath('app/static')}")
    print(f"Forwarding API requests to: {LIVE_API_URL}")
    app.run(host='0.0.0.0', port=PROXY_PORT, debug=True)