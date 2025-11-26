from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import json
import os
import uuid
import logging
import shutil
from logging.handlers import RotatingFileHandler
from src.charts import generate_charts_for_sightings, generate_charts_for_reportings, generate_charts
from src.pdf_generator import create_pdf_report
from src.config import config

app = Flask(__name__)

# Enable CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "max_age": 3600
    }
})

# Get the project root directory (parent of src)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load configuration
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Update paths to be relative to project root
app.config['UPLOAD_FOLDER'] = os.path.join(PROJECT_ROOT, app.config['UPLOAD_FOLDER'])
app.config['OUTPUT_FOLDER'] = os.path.join(PROJECT_ROOT, app.config['OUTPUT_FOLDER'])

# Configure logging for production
if not app.debug:
    logs_dir = os.path.join(PROJECT_ROOT, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'submission-reports.log'), 
        maxBytes=10240000, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Flask PDF application startup')

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return jsonify({"message": "SERVER IS RUNNING"})


@app.route('/api/v1/generate-reports/sightings', methods=['POST'])
def generate_sightings_report():
    """Generate PDF report for sightings data"""
    return _generate_report('sightings')


@app.route('/api/v1/generate-reports/reportings', methods=['POST'])
def generate_reportings_report():
    """Generate PDF report for reportings data"""
    return _generate_report('reportings')


def _generate_report(report_type):
    """Internal function to generate reports for both sightings and reportings"""
    chart_files = []
    pdf_path = None
    
    try:
        # Clean output directory before generating new report
        try:
            if os.path.exists(app.config['OUTPUT_FOLDER']):
                for filename in os.listdir(app.config['OUTPUT_FOLDER']):
                    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        app.logger.warning(f'Failed to delete {file_path}: {str(e)}')
                app.logger.info('Output directory cleaned')
        except Exception as e:
            app.logger.warning(f'Error cleaning output directory: {str(e)}')
        
        # Get JSON data from request
        if request.is_json:
            data = request.get_json()
            if data is None:
                return jsonify({'error': 'Invalid JSON data'}), 400
        else:
            file = request.files.get('file')
            if not file:
                return jsonify({'error': 'No data provided'}), 400
            
            try:
                data = json.load(file)
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
        
        # Validate data structure
        if not isinstance(data, dict) and not isinstance(data, list):
            return jsonify({'error': 'Data must be a JSON object or array'}), 400
        
        # Extract the data array - handle both 'data' and 'result' keys
        if isinstance(data, dict):
            if 'result' in data:
                observations = data['result']
            elif 'data' in data:
                observations = data['data']
            else:
                observations = [data]
        else:
            observations = data if isinstance(data, list) else [data]
        
        # Validate observations
        if not observations:
            return jsonify({'error': 'No observations found in data'}), 400
        
        if not isinstance(observations, list):
            return jsonify({'error': 'Observations must be an array'}), 400
        
        if len(observations) > 10000:
            return jsonify({'error': 'Too many observations. Maximum 10,000 allowed'}), 400
        
        # Generate charts based on report type
        try:
            if report_type == 'reportings':
                chart_files, summary_data = generate_charts_for_reportings(observations, app.config['UPLOAD_FOLDER'])
            else:
                chart_files, summary_data = generate_charts_for_sightings(observations, app.config['UPLOAD_FOLDER'])
        except Exception as e:
            return jsonify({'error': f'Chart generation failed: {str(e)}'}), 500
        
        if not chart_files:
            return jsonify({'error': 'No charts generated. Please check your data contains valid fields'}), 400
        
        # Create PDF with unique UUID filename
        report_uuid = str(uuid.uuid4())
        pdf_filename = f'{report_uuid}.pdf'
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
        
        try:
            create_pdf_report(chart_files, pdf_path, observations, summary_data, report_type)
        except Exception as e:
            return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
        
        # Verify PDF was created
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF file was not created'}), 500
        
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
    
    except Exception as e:
        app.logger.error(f'Unexpected error in generate_report: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred. Please try again later'}), 500
    
    finally:
        # Clean up chart images in finally block to ensure cleanup happens
        for chart_file in chart_files:
            try:
                if os.path.exists(chart_file):
                    os.remove(chart_file)
            except Exception as e:
                app.logger.warning(f'Failed to delete chart file {chart_file}: {str(e)}')

if __name__ == '__main__':
    # Use environment variables for production
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    app.run(debug=debug_mode, host=host, port=port)
