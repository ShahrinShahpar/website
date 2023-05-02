import random
import string
import os
import csv
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, g, redirect, url_for, session, flash, send_file, abort, after_this_request
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from db import get_db, create_db
from functools import wraps
import sqlite3
import subprocess


app = Flask(__name__)
app.secret_key = 'secret_key'
app.config['UPLOAD_FOLDER'] = '/var/tmp/uploads'

# #download
# @app.route('/download/<path:filename>')
# def download_file(filename):
#     path = '/path/to/your/file/' + filename
#     return send_file(result['file_path'], as_attachment=True)


#split for job

@app.template_filter('split')
def split_filter(value, sep):
    return str(value).split(sep)

# Define a decorator to check if the user is authenticate

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
    return wrapper

def create_database():
    with app.app_context():
        create_db()

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('upload'))
    return render_template('signup.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        # userid = request.form['userid']
        password = request.form['password']
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='sha256')
        
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE email=?', (email,))
        if cur.fetchone():
            db.close()
            return redirect(url_for('signup'))
        
        # Insert new user into database
        cur.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
        db.commit()
        db.close()
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # userid = request.form['userid']
        email = request.form['email']
        password = request.form['password']

        # Fetch the user's hashed password from your database
        db = get_db()
        cur = db.execute('SELECT * FROM users WHERE email = ?', (email,))
        user_tuple = cur.fetchone()

        if user_tuple is not None:
            # Convert the tuple to a dictionary
            user = {
                'user_id': user_tuple[0],
                'email': user_tuple[1],
                'password': user_tuple[2]
            }
            
            # Check if the password is correct
            if user and check_password_hash(user['password'], password):
                # Log the user in and redirect to the dashboard
                session['user_id'] = user['user_id']
                flash('You have been logged in!', 'success')
                return redirect(url_for('upload'))
            else:
                # Show an error message if the login was unsuccessful
                flash('Login unsuccessful. Please check your email, user id or password.', 'danger')
                return redirect(url_for('login'))
        else:
            # Show an error message if the user does not exist
            flash('User does not exist. Please check your email, user id or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


#uploading
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        # Retrieve the platform data from the database
        db = get_db()
        cur = db.cursor()
        cur.execute('SELECT name FROM options')
        data = cur.fetchall()
        db.close()
        # Pass the platform data to the upload.html template
        return render_template('upload.html', options=data)
    
    elif request.method == 'POST':

        file = request.files['file']
        if file:
            userid = session['user_id']
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(userid))
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)
            platform = request.form['mydropdown']
            no_of_tests = request.form['no_of_tests']
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{timestamp}-{filename}"

            file.save(os.path.join(user_folder, filename))
            filepath = os.path.join(user_folder, filename)
            with app.app_context():  # Added code
                db = get_db()
                cur = db.cursor()
                cur.execute("INSERT INTO files (filename, filepath) VALUES (?, ?)", (filename, filepath))
                file_id = cur.lastrowid 
                cur.execute('INSERT INTO jobs (fileid, userid, platform, no_of_tests, completed) VALUES (?, ?, ?, ?, ?)', (file_id, userid, platform, no_of_tests, 0))
                job_id = cur.lastrowid
                db.commit()
                db.close()

                # Process the file using a subprocess
                subprocess.Popen(["python", "process_file.py", str(file_id), str(userid)])

            # Show a flash message indicating that the file was uploaded successfully
            flash(f"File '{file.filename}' uploaded successfully")
            return redirect(url_for('upload'))
        else:
            with app.app_context():  # Added code
                db = get_db()
                cur = db.cursor()
                cur.execute("SELECT DISTINCT platform FROM jobs")
                options = cur.fetchall()
                db.close()
            return render_template('upload.html', options=options)
        
#viewing files
@app.route('/jobs')
@login_required
def show_jobs():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    userid = session['user_id']
    
    db = get_db()
    db.row_factory = sqlite3.Row
    
    cur = db.cursor()
    cur.execute("SELECT jobs.*, files.filename FROM jobs JOIN files ON jobs.fileid=files.id WHERE jobs.userid = ?", (userid,))
    rows = cur.fetchall()
    
    db.close()
    
    return render_template('jobs.html', rows=rows)

#view result
@app.route('/jobs/<int:job_id>/results')
@login_required
def view_results(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.row_factory = sqlite3.Row
    
    cur = db.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cur.fetchone()
    
    cur.execute("SELECT * FROM results WHERE job_id = ?", (job_id,))
    results = cur.fetchall()
    
    db.close()
    
    return render_template('results.html', job=job, results=results)


#download file
@app.route('/jobs/<int:job_id>/download')
@login_required
def download_results(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.row_factory = sqlite3.Row
    
    cur = db.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cur.fetchone()
    
    cur.execute("SELECT * FROM results WHERE job_id = ?", (job_id,))
    result = cur.fetchone()
    
    db.close()

    if result is not None:
        file_name = result['file_path'].split("/")[-1] # extract file name
        response = send_file(result['file_path'], as_attachment=True)
        response.headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
    else:
        abort(404)

#download image
@app.route('/download_image/<int:job_id>')
@login_required
def download_image(job_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    db.row_factory = sqlite3.Row
    
    cur = db.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cur.fetchone()
    cur.execute("SELECT * FROM results WHERE job_id = ?", (job_id,))
    result = cur.fetchone()
    db.close()
    image_name = "13.png"
    filename = result['file_path'].split("/")[-1].split('.')[0] + '.png'
    image_path = os.path.join('/var/tmp/results', image_name)
    return send_file(image_path, as_attachment=True, download_name=filename)

#logout
        
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    @after_this_request
    def add_header(response):
        response.cache_control.no_store = True
        return response
    return redirect(url_for('index'))  

# @app.route('/')
# def index():
#     return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)