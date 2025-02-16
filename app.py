import os
import cv2
import plotly
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
import plotly.express as px
import plotly.io as pio
import numpy as np
from PIL import Image, ImageOps
import json
from skimage import measure
from flask_session import Session

import kuka.converter

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure server-side session storage
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def index():
    if 'krl_script' not in session:
        session['krl_script'] = ""
    if 'preprocessing_options' not in session:
        session['preprocessing_options'] = {
            'blur_intensity': 9,
            'threshold_block_size': 7,
            'threshold_C': 4
        }
    return render_template('index.html', krl_script=session['krl_script'], preprocessing_options=session['preprocessing_options'])

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.endswith('.png'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        # Reset session variables related to the plot
        session.pop('contours', None)
        session.pop('history', None)
        session.pop('redo_stack', None)
        session.pop("fig", None)

        process_image(file_path)
        return redirect(url_for('index'))
    return 'Invalid file format. Please upload a PNG file.'

@app.route('/update_preprocessing', methods=['POST'])
def update_preprocessing():
    session['preprocessing_options'] = {
        'blur_intensity': int(request.form.get('blur_intensity')),
        'threshold_block_size': int(request.form.get('threshold_block_size')),
        'threshold_C': int(request.form.get('threshold_C'))
    }
    return redirect(url_for('index'))

def smooth_contour(contour, window_size=5):
    if len(contour) < window_size:
        return contour

    kernel = np.ones(window_size) / window_size
    pad = window_size // 2

    padded_x = np.pad(contour[:, 0], pad_width=pad, mode='edge')
    padded_y = np.pad(contour[:, 1], pad_width=pad, mode='edge')

    smoothed_x = np.convolve(padded_x, kernel, mode='valid')
    smoothed_y = np.convolve(padded_y, kernel, mode='valid')

    return np.stack((smoothed_x, smoothed_y), axis=-1)

def process_image(image_path):
    image = Image.open(image_path).convert("RGBA")
    image = ImageOps.expand(image, border=20)
    image = image.rotate(180)

    white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
    pil_image = Image.alpha_composite(white_bg, image)

    image_np = np.array(pil_image)
    image_grayscale = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    image_blur = cv2.medianBlur(image_grayscale, session['preprocessing_options']['blur_intensity'])
    image_edges = cv2.adaptiveThreshold(
        image_blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=session['preprocessing_options']['threshold_block_size'],
        C=session['preprocessing_options']['threshold_C']
    )

    raw_contours = measure.find_contours(image_edges.astype(float), level=0.9)
    point_arrays = []
    for contour in raw_contours:
        points = np.fliplr(contour)
        if len(points) < 20:
            continue
        if np.sum((points[1:, 0] - points[:-1, 0]) * (points[1:, 1] + points[:-1, 1])) >= 0:
            continue
        points_smoothed = smooth_contour(points)
        point_arrays.append(points_smoothed.tolist())  # Convert to list

    session['contours'] = point_arrays
    if 'history' not in session:
        session['history'] = []
    session['history'].append((point_arrays.copy(), session['preprocessing_options'].copy()))
    session['redo_stack'] = []

@app.route('/plot', methods=['GET'])
def plot():
    if 'fig' in session:
        fig = plotly.io.from_json(session['fig'])
    else:
        fig = px.line()

        for idx, contour in enumerate(session.get('contours', [])):
            contour = np.array(contour)
            fig.add_scatter(x=contour[:, 0], y=contour[:, 1], mode='lines', name=f"Contour {idx + 1}")

        session['fig'] = fig.to_json()

    plot_html = pio.to_html(fig, full_html=False, div_id="myDiv")
    return plot_html

@app.route('/update_fig', methods=['POST'])
def update_fig():

    print("IT WORKS")
    fig_json = request.json.get('fig')
    session['fig'] = fig_json
    return '', 204

@app.route('/convert', methods=['POST'])
def convert():
    fig = plotly.io.from_json(session["fig"])
    visible_contours_idx = []
    for trace in fig['data']:
        if trace["mode"] == "lines":
            if "Contour" not in trace['name']:
                continue
            if 'visible' not in trace or trace['visible'] != 'legendonly':
                try:
                    contour_index = int(trace['name'].split(' ')[1]) - 1
                    visible_contours_idx.append(contour_index)
                except (IndexError, ValueError) as e:
                    print(f"Error processing trace name: {trace['name']}, error: {e}")

    # Get the contours that are currently visible
    visible_contours = [np.array(session['contours'][idx]) for idx in visible_contours_idx]

    krl_script = kuka.converter.generate_krl_script(visible_contours, save=False)
    session['krl_script'] = "\n".join(krl_script)

    return redirect(url_for('index'))

@app.route('/update_krl', methods=['POST'])
def update_krl():
    session['krl_script'] = request.form['krl_script']
    return '', 204

@app.route('/download_krl')
def download_krl():
    from io import BytesIO

    output = BytesIO()
    output.write(session['krl_script'].encode('utf-8'))
    output.seek(0)

    return send_file(output, as_attachment=True, download_name="draw.src", mimetype="text/plain")

@app.route('/undo', methods=['POST'])
def undo():
    if 'history' in session and session['history']:
        if 'redo_stack' not in session:
            session['redo_stack'] = []
        session['redo_stack'].append((session['contours'].copy(), session['preprocessing_options'].copy()))
        session['contours'], session['preprocessing_options'] = session['history'].pop()
    return redirect(url_for('index'))

@app.route('/redo', methods=['POST'])
def redo():
    if 'redo_stack' in session and session['redo_stack']:
        if 'history' not in session:
            session['history'] = []
        session['history'].append((session['contours'].copy(), session['preprocessing_options'].copy()))
        session['contours'], session['preprocessing_options'] = session['redo_stack'].pop()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)