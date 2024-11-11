from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS
from jeweler_scraper import scrape_jewelers_for_state, INDIAN_STATES
import threading
import pandas as pd
from queue import Queue
from datetime import datetime, timedelta
from queue import Queue, Empty
import json
import os
from countryinfo import CountryInfo
import gzip
import shutil
from threading import Lock
import time

# Add at the top with other imports
UPLOAD_FOLDER = 'downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create folder if it doesn't exist
app = Flask(__name__)
CORS(app)

# Serve static files from 'static' directory
app.static_folder = 'static'

event_queues = {}
session_queues = {}
session_locks = {}
queue_cleanup_times = {}
QUEUE_TIMEOUT = 300  # 5 minutes

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape():
    data = request.json
    location = data.get('location')
    search = data.get('search')
    session_id = data.get('session_id')
    
    if not all([location, search, session_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    if session_id not in event_queues:
        event_queues[session_id] = Queue()
    
    def send_message(message):
        if session_id in event_queues:
            event_queues[session_id].put(message)
    
    thread = threading.Thread(
        target=lambda: scrape_jewelers_for_state(location, search, send_message)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/api/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<session_id>')
def stream(session_id):
    def generate():
        if session_id not in event_queues:
            event_queues[session_id] = Queue()
            
        while True:
            try:
                message = event_queues[session_id].get(timeout=1)
                
                if message == "DONE":
                    break
                    
                if isinstance(message, dict):
                    data = json.dumps(message)
                else:
                    data = json.dumps({"message": str(message)})
                
                yield f"data: {data}\n\n"
                
            except Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            except Exception as e:
                print(f"Stream error: {str(e)}")
                break
                
    return Response(generate(), mimetype='text/event-stream')

from pycountry import countries, subdivisions

@app.route('/api/locations', methods=['GET'])
def get_locations():
    # Top 100 countries and their major cities
    LOCATIONS = {
        "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
        "United Kingdom": ["London", "Manchester", "Birmingham", "Liverpool", "Glasgow"],
        "India": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"],
        # Add more as needed
    }
    
    country = request.args.get('country')
    if not country:
        return jsonify({'countries': sorted(LOCATIONS.keys())})
    
    cities = LOCATIONS.get(country, [])
    return jsonify({'cities': sorted(cities)})

@app.route('/api/pause', methods=['POST'])
def pause_scraping():
    return jsonify({'status': 'paused'})

@app.route('/api/stop', methods=['POST'])
def stop_scraping():
    return jsonify({'status': 'stopped'})

def cleanup_old_queues():
    current_time = time.time()
    to_delete = []
    for session_id, last_access in queue_cleanup_times.items():
        if current_time - last_access > QUEUE_TIMEOUT:
            to_delete.append(session_id)
    
    for session_id in to_delete:
        if session_id in session_queues:
            del session_queues[session_id]
            del queue_cleanup_times[session_id]
            if session_id in session_locks:
                del session_locks[session_id]

@app.before_request
def before_request():
    cleanup_old_queues()

@app.route('/api/downloads')
def list_downloads():
    try:
        files = [f for f in os.listdir(UPLOAD_FOLDER) 
                if f.endswith('.csv') and os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
        return jsonify(sorted(files, key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-current', methods=['POST'])
def export_current():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        if not files:
            return jsonify({'error': 'No data available'}), 404
            
        latest_file = max([os.path.join(UPLOAD_FOLDER, f) for f in files], key=os.path.getmtime)
        
        return send_file(
            latest_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=os.path.basename(latest_file)
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 