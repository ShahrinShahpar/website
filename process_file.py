import csv
import os
import random
import string
import sys
from flask import Flask,session
from db import get_db
import time  # import the time module

app = Flask(__name__)
app.config['RESULT_FOLDER'] = '/var/tmp/results'

file_id = int(sys.argv[1])
userid = int(sys.argv[2])

with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT filepath FROM files WHERE id = ?", (file_id,))
    file_path = cur.fetchone()[0]
    cur.execute("SELECT MAX(id) FROM jobs WHERE fileid = ?", (file_id,))
    job_id = cur.fetchone()[0]

    if job_id is not None:
        # Check if a file has already been generated for this job ID
        cur.execute("SELECT COUNT(*) FROM results WHERE job_id = ?", (job_id,))
        if cur.fetchone()[0] == 0:
            # Pause for 10 seconds before generating the file
            time.sleep(10)
            # Generate a random 1KB CSV file
            file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) + '.csv'
            #user_id = session['user_id']
            user_folder_path = os.path.join(app.config['RESULT_FOLDER'], str(userid))
            if not os.path.exists(user_folder_path):
                os.mkdir(user_folder_path)
            result_file_path = os.path.join(user_folder_path, file_name)
            with open(result_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for i in range(1000):
                    writer.writerow([random.randint(1, 1000), random.uniform(0, 1)])
            # Save the file path to the database
            cur.execute("INSERT INTO results (file_path, job_id) VALUES (?, ?)", (result_file_path, job_id))
            cur.execute("UPDATE jobs SET completed = 1 WHERE id = ?", (job_id,))
        db.commit()
        db.close()
