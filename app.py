import os
import json
import pandas as pd
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Set Google Application Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Initialize Flask app
app = Flask(__name__)

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_NAME = os.getenv("FOLDER_NAME")

def get_drive_service():
    creds = Credentials.from_service_account_file(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_company_folders():
    """Fetches all company folders from 'company_leetcode'."""
    service = get_drive_service()
    query = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}'"
    
    results = service.files().list(q=query, fields="files(id)").execute()
    folder_id = results.get("files", [])[0]["id"] if results.get("files") else None

    if not folder_id:
        return []

    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    
    return results.get("files", [])

def get_csv_file(company_folder_id):
    """Fetches the CSV file (all.csv) inside a company folder."""
    service = get_drive_service()
    query = f"'{company_folder_id}' in parents and name='all.csv'"
    
    results = service.files().list(q=query, fields="files(id)").execute()
    file_id = results.get("files", [])[0]["id"] if results.get("files") else None
    
    if not file_id:
        return None
    
    file = service.files().get_media(fileId=file_id).execute()
    return pd.read_csv(pd.compat.StringIO(file.decode('utf-8')))

@app.route('/get_questions', methods=['GET'])
def get_questions():
    """Fetches and returns questions from the Google Drive folder with filtering."""
    company_folders = get_company_folders()
    data = []

    for folder in company_folders:
        folder_name = folder["name"]
        csv_data = get_csv_file(folder["id"])

        if csv_data is not None:
            csv_data["Company"] = folder_name  # Add company name to data
            data.append(csv_data)

    if not data:
        return jsonify({"error": "No data found"}), 404

    merged_data = pd.concat(data, ignore_index=True)

    # 🔹 Apply filters based on query parameters
    difficulty = request.args.get("difficulty")  # Easy, Medium, Hard
    topic = request.args.get("topic")  # DP, Graph, Arrays, etc.
    company = request.args.get("company")  # Google, Amazon, etc.
    sort_by = request.args.get("sort_by")  # Frequency, Acceptance Rate

    if difficulty:
        merged_data = merged_data[merged_data["Difficulty"].str.lower() == difficulty.lower()]
    
    if topic:
        merged_data = merged_data[merged_data["Topics"].str.contains(topic, case=False, na=False)]
    
    if company:
        merged_data = merged_data[merged_data["Company"].str.lower() == company.lower()]

    if sort_by == "Frequency":
        merged_data = merged_data.sort_values(by="Frequency", ascending=False)
    elif sort_by == "Acceptance Rate":
        merged_data = merged_data.sort_values(by="Acceptance Rate", ascending=False)

    return merged_data.to_json(orient="records")

@app.route('/')
def home():
    return jsonify({"message": "LeetCode API is running!"})

if __name__ == '__main__':
    app.run(debug=True)
