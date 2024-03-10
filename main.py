from flask import Flask, request, jsonify, render_template
import os
import PyPDF2
import json
from openai import OpenAI
from uuid import uuid4
from dotenv import load_dotenv
from typing import Optional
from contextlib import contextmanager
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, Column, String, Text, inspect
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from chardet.universaldetector import UniversalDetector


#load api key
load_dotenv()
OPENAI_API_KEY = os.getenv("API_KEY")
client = OpenAI(api_key = OPENAI_API_KEY)

#decleare base
Base = declarative_base()

#creating a database
class Document(Base):     #changed title
    __tablename__ = 'Nurovant_i'  # Replace with your actual table name
    id: str = Column(String, primary_key=True)
    title: Optional[str] = Column(String)
    abstract: Optional[str] = Column(Text)
    file_name: str = Column(String)
    summary: Optional[str] = Column(Text)

    def to_dict(self):
        """
        Converts the Research object to a dictionary, as requested.
        """
        return {
            'id': self.id,
            'title': self.title,
            'abstract': self.abstract,
            'file_name': self.file_name,
            'summary': self.summary,
        }


class Feedback(Base):
    __tablename__ = 'feedbacks_tbl'
    id: str = Column(String, primary_key=True)
    question_asked: str = Column(String)
    answer: Optional[str] = Column(Text)
    bullet_points: Optional[str] = Column(String)
    test_question: str = Column(String)

    # def __init__(self, question_asked, answer, bullet_points, test_question):
    #     self.question_asked = question_asked
    #     self.answer = answer
    #     self.bullet_points = json.dumps(bullet_points)
    #     self.test_question = test_question

engine = create_engine('sqlite:///database.sqlite')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    db = SessionLocal() #changed from sessionlocal
    try:
        yield db
    finally:
        db.close()

app = Flask(__name__)


UPLOAD_FOLDER = os.path.join(os.getcwd(), 'documents/uploads')
ALLOWED_EXTENTIONS = {"txt", "pdf", "doc"}

def file_upload(file_name):
    return '.' in file_name and file_name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENTIONS

@app.route('/')
#def index():
#    return render_template('index.html')
def get_all_document():
    with get_db() as db:
        Document_data = db.query(Document).all()

    document_info_list = [
        {
            'id': Document_data.id,
            'title': Document_data.title,
            'abstract': Document_data.abstract,
            'file_name': Document_data.file_name,
            'summary': Document_data.abstract[:200] + '...' if Document_data.abstract else Document_data.summary,
        }
        for doc in Document_data
    ]

    return document_info_list

@app.route('/document/<id>')
def view_document(id):
    with get_db() as db:
        document = db.query(Document).filter(Document.id == id).first()
        if document is None:
            return jsonify({'status': 'No document data found for '+id}), 404
        return jsonify(document.to_dict())


@app.route('/document')
def list_document():
    document_data = get_all_document()
    if document_data is None:
        return jsonify({'status': 'No document data found'}), 404
    return jsonify(document_data)


@app.route('/uploads', methods=["GET", "POST"])
def upload_file():
    if 'document_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['document_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file_upload(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        # Parse data based on file type
        if filename.endswith('txt'):
            import re
            with open(os.path.join(UPLOAD_FOLDER, filename), 'r') as f:
                lines = f.readlines()
                title = lines[0].strip()
                abstract = '\n'.join(lines[1:])
        elif filename.endswith(('pdf')):
            with open(os.path.join(UPLOAD_FOLDER, filename), 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                title = pdf_reader.metadata['/Title']
                abstract = pdf_reader.pages[0].extract_text()

                #title = pdf_reader.getDocumentInfo().title
                #abstract = pdf_reader.pages[0].extractText()  # Assuming you still want the first page
                #abstract = pdf_reader.getPage(1).extractText()
        else:
            title = None
            abstract = None
        file_path = os.path.join(UPLOAD_FOLDER, filename)


        # Create summary


        with open(file_path, 'r', encoding='latin-1') as f:
            file_contents = f.read()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You: Summarize the following document:"},
                {"role": "user", "content": file_contents}
            ],
            max_tokens=100,
            stop=None,
            temperature=0.5,
        )

        summary = response.choices[0].message.content.strip()
        doc_id = str(uuid4())

        with get_db() as db:
            new_document = Document(id=doc_id, title=title, abstract=abstract, file_name=filename, summary=summary)
            db.add(new_document)
            db.commit()

        return jsonify({'message': 'File uploaded and summarized successfully', 'data': {'document_id': doc_id}}), 201
    else:
        return jsonify({'error': 'Unsupported file format'}), 400

def validate_request(data):
    return data and data.get('document_id') and data.get('question')
def get_document(document_id):
    with get_db() as db:
        return db.query(Document).filter(Document.id == document_id).first()
def ask_openai(gotten_doc, question):
    # call OpenAI API
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": f"You: {question} in this document, also when returning the response it is highly important for it to be in a valid json syntax `the answer to the question asked, A list of bullet points emphasizing key details in the answer to improve understanding, A generated question to evaluate if the user understood the answer provided`"},
            {"role": "user", "content": gotten_doc.abstract}
        ],
        max_tokens=300,
        stop=None,
        temperature=0.5,
        )
def save_feedback_txt(data: String):
    """
      Saves the feedback response to a text file named "feedback.txt".

      Args:
          data (dict): The dictionary containing the feedback response information.
      """
    with open("documents/feedback.txt", "w") as f:
        f.write(data)

    print("Feedback saved to feedback.txt")

def save_feedback(id, feedback, question):
    with get_db() as db:
        db.add(Feedback(
            id=id,
            question_asked=question,
            bullet_points=feedback[1],
            test_question=feedback[2],
            answer=feedback[0]
        ))
        db.commit()

def read_feedback_file():
    with open(os.path.join('documents/', 'feedback.txt'), 'r') as f:
        lines = f.readlines()
        answer = lines[0].strip()
        bullet_points = '\n'.join(lines[1:])
        question = '\n'.join(lines[2:])

    print(answer)
    print("answer above")
    print(bullet_points)
    print("bullet points above")
    print(question)
    print("question above")
@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    if not validate_request(data):
        return jsonify({'error': 'Missing required document or question'}), 400

    document_id = data['document_id']
    question = data['question']

    gotten_doc = get_document(document_id)
    if not gotten_doc:
        return jsonify({'error': f'No research found for {document_id}'}), 404

    try:
        response = ask_openai(gotten_doc, question)
        feedback = response.choices[0].message.content

        save_feedback_txt(feedback)

        with open(os.path.join('documents/', 'feedback.txt'), 'r') as f:
            lines = f.readlines()
            answer = lines[0].strip()
            bullet_points = '\n'.join(lines[1:])
            question = '\n'.join(lines[2:])

        print(answer)
        print(bullet_points)
        print(question)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': 'Question submitted successfully',
        'feedback': feedback
    })

if __name__ == "__main__":
    app.run(debug= True, port= 9090)