import os

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

#ALLOWED_FOLDER =
ALLOWED_EXTENTIONS = {"txt", "pdf", "doc"}

app = Flask(__name__)

def file_upload(file_name):
    return '.' in file_name and file_name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENTIONS
@app.route('/')
def get_all_document():
    with get_db() as db:
        research_data = db.query(Research).all()

    document_info_list = [
        {
            'id': research.id,
            'title': research.title,
            'abstract': research.abstract,
            'file_name': research.file_name,
            'summary': research.abstract[:200] + '...' if research.abstract else research.summary,
        }
        for doc in research_data
    ]

    return research_list
