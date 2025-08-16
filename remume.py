import os
import re
import pdfplumber
import psycopg2
from flask import Flask, request, jsonify
import spacy
from spacy.matcher import PhraseMatcher

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

SKILLS_LIST = ["python", "java", "machine learning", "data analysis", "sql", "flask", "django"]

matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
patterns = [nlp(skill) for skill in SKILLS_LIST]
matcher.add("SKILLS", patterns)
DB_PARAMS = {
    'dbname': 'your_db_name',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'host': 'localhost',
    'port': 5432
}

def get_db_connection():
    conn = psycopg2.connect(**DB_PARAMS)
    return conn

def extract_text_from_pdf(pdf_path):
    text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + '\n'
    return text

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else None

def extract_phone(text):
    match = re.search(r'(\+?\d{1,3})?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}', text)
    return match.group(0) if match else None

def extract_name(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            return ent.text
    return None

def extract_skills(text):
    doc = nlp(text)
    matches = matcher(doc)
    return list(set([doc[start:end].text.lower() for _, start, end in matches]))

def extract_education(text):
    degrees = ['Bachelor', 'Master', 'B.Sc', 'M.Sc', 'PhD', 'Doctorate']
    education = []
    lines = text.split('\n')
    for line in lines:
        for degree in degrees:
            if degree.lower() in line.lower():
                education.append(line.strip())
                break
    return education

def insert_candidate(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO candidates (name, email, phone) VALUES (%s, %s, %s) RETURNING id
    """, (data['name'], data['email'], data['phone']))
    candidate_id = cur.fetchone()[0]

    skill_ids = []
    for skill in data['skills']:
        cur.execute("SELECT id FROM skills WHERE name = %s", (skill,))
        res = cur.fetchone()
        if res:
            skill_id = res[0]
        else:
            cur.execute("INSERT INTO skills (name) VALUES (%s) RETURNING id", (skill,))
            skill_id = cur.fetchone()[0]
        skill_ids.append(skill_id)
        cur.execute("""
            INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (candidate_id, skill_id))
    for edu_line in data['education']:
        degree = edu_line
        institution = None
        year = None
        cur.execute("""
            INSERT INTO education (candidate_id, degree, institution, year)
            VALUES (%s, %s, %s, %s)
        """, (candidate_id, degree, institution, year))
    
    conn.commit()
    cur.close()
    conn.close()
    return candidate_id

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filepath = os.path.join('temp', file.filename)
    os.makedirs('temp', exist_ok=True)
    file.save(filepath)
    text = extract_text_from_pdf(filepath)
    candidate_data = {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'education': extract_education(text)
    }
    
    candidate_id = insert_candidate(candidate_data)

    os.remove(filepath)
    
    return jsonify({'message': 'Resume parsed and stored', 'candidate_id': candidate_id, 'data': candidate_data})

if __name__ == '__main__':
    app.run(debug=True)
