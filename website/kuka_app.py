import os
from io import BytesIO
from pathlib import Path

import plotly
from flask import render_template, request, redirect, url_for, send_file, session, Blueprint, current_app
import plotly.express as px
import plotly.io as pio
import numpy as np

import kuka.converter
from website.image_stuff.image_conversion import process_image

kuka_app = Blueprint('kuka_app', __name__, template_folder=Path(__file__).parent.joinpath("templates"))


@kuka_app.route('/')
def index():
    if 'krl_script' not in session:
        session['krl_script'] = ""
    if 'preprocessing_options' not in session:
        session['preprocessing_options'] = {
            'blur_intensity': 9,
            'threshold_block_size': 7,
            'threshold_C': 4
        }
    if 'history' not in session:
        session['history'] = []
    if 'convert_options' not in session:
        session['convert_options'] = {
            "x": 210.0,       # Default scale X
            "y": 297.0,       # Default scale Y
            "border": 20.0,    # Default border
            "mode": "preserve",    # Default aspect mode
            "preset_size": "a4",   # Default to A4
            "base": 3,      # Default base id
            "tool": 3,      # Default tool id
        }
    return render_template(
        'index.html',
        krl_script=session['krl_script'],
        preprocessing_options=session['preprocessing_options'],
        convert_options=session['convert_options']
    )

@kuka_app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and file.filename.lower().endswith(('.png', '.jpeg')):
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        # Reset session variables related to the plot
        session.pop('redo_stack', None)
        session.pop("fig", None)

        points = process_image(file_path,
                      session['preprocessing_options']['blur_intensity'],
                      session['preprocessing_options']['threshold_block_size'],
                      session['preprocessing_options']['threshold_C'])

        session['contours'] = points
        session['history'].append((points.copy(), session['preprocessing_options'].copy()))
        session['redo_stack'] = []

        return redirect(url_for('kuka_app.index'))
    return 'Invalid file format. Please upload a PNG or JPEG file.'

@kuka_app.route('/update_preprocessing', methods=['POST'])
def update_preprocessing():
    update_values()
    return redirect(url_for('kuka_app.index'))

@kuka_app.route('/plot', methods=['GET'])
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

@kuka_app.route('/update_fig', methods=['POST'])
def update_fig():
    session['fig'] = request.json.get('fig')
    return '', 204

@kuka_app.route('/convert', methods=['POST'])
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

    update_values()
    scale_x = session['convert_options']['x']
    scale_y = session['convert_options']['y']
    border = session['convert_options']['border']
    mode = session['convert_options']['mode']
    base = session['convert_options']['base']
    tool = session['convert_options']['tool']

    krl_script = kuka.converter.generate_krl_script(visible_contours, save=False, scale=np.array([scale_x, scale_y]),
                                                    border=np.array([border, border]), mode=mode, base_id=base,
                                                    tool_id=tool)
    session['krl_script'] = "\n".join(krl_script)
    return redirect(url_for('kuka_app.index'))

@kuka_app.route('/update_krl', methods=['POST'])
def update_krl():
    session['krl_script'] = request.form['krl_script']
    return '', 204

@kuka_app.route('/download_krl')
def download_krl():
    output = BytesIO()
    output.write(session['krl_script'].encode('utf-8'))
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="draw.src", mimetype="text/plain")

@kuka_app.route('/undo', methods=['POST'])
def undo():
    if 'history' in session and session['history']:
        if 'redo_stack' not in session:
            session['redo_stack'] = []
        session['redo_stack'].append((session['contours'].copy(), session['preprocessing_options'].copy(),
                                      session["convert_options"].copy()))
        session['contours'], session['preprocessing_options'], session["convert_options"] = session['history'].pop()
    return redirect(url_for('kuka_app.index'))

@kuka_app.route('/redo', methods=['POST'])
def redo():
    if 'redo_stack' in session and session['redo_stack']:
        if 'history' not in session:
            session['history'] = []
        session['history'].append((session['contours'].copy(), session['preprocessing_options'].copy(),
                                   session["convert_options"].copy()))
        session['contours'], session['preprocessing_options'], session["convert_options"] = session['redo_stack'].pop()
    return redirect(url_for('kuka_app.index'))

def update_values():
    session['preprocessing_options'] = {
        'blur_intensity': int(request.form.get('blur_intensity', 9)),
        'threshold_block_size': int(request.form.get('threshold_block_size', 7)),
        'threshold_C': int(request.form.get('threshold_C', 4))
    }

    session["convert_options"] = {
        "x": float(request.form.get("scale_x", 210.0)),
        "y": float(request.form.get("scale_y", 297.0)),
        "border": float(request.form.get("border", 0)),
        "mode": request.form.get("aspect_mode", "preserve"),
        "preset_size": request.form.get("preset_size", "a4"),
        "base": request.form.get("base", 3),
        "tool": request.form.get("tool", 3),
    }

