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
    service = get_drive_service()
    folder_name = os.getenv("FOLDER_NAME")
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    
    try:
        results = []
        page_token = None
        while True:
            response = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
            results.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        # Get the ID of the main folder
        if results:
            main_folder_id = results[0]['id']
            # List all subfolders within the main folder
            subfolder_query = f"'{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            subfolders = []
            page_token = None
            while True:
                response = service.files().list(q=subfolder_query, fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
                subfolders.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
            return subfolders
    except Exception as e:
        print("Google API Error:", str(e))
    
    return []  # Return an empty list if no folders are found

import io

def get_csv_file(company_folder_id, file_name):
    """Fetches the specified CSV file inside a company folder."""
    service = get_drive_service()
    query = f"'{company_folder_id}' in parents"
    
    try:
        results = []
        page_token = None
        while True:
            response = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
            results.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        
        # Check if the CSV file exists in the folder
        for file in results:
            if file['name'] == file_name:
                file_id = file['id']
                file_content = service.files().get_media(fileId=file_id).execute()
                return pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        
        return None
    except Exception as e:
        print("Google API Error:", str(e))
        return None

@app.route('/get_questions', methods=['GET'])
def get_questions():
    """Fetches and returns questions from the Google Drive folder with filtering."""
    company_folders = get_company_folders()
    data = []

    file_name = request.args.get("file_name", "5. All.csv")  # Default to '5. All.csv' if not specified
    company_filter = request.args.get("company")  # Google, Amazon, etc.
    difficulty = request.args.get("difficulty")  # Easy, Medium, Hard
    topic = request.args.get("topic")  # DP, Graph, Arrays, etc.
    sort_by = request.args.get("sort_by")  # Frequency, Acceptance Rate

    for folder in company_folders:
        folder_name = folder["name"]
        if company_filter and folder_name.lower() != company_filter.lower():
            continue

        csv_data = get_csv_file(folder["id"], file_name)

        if csv_data is not None:
            csv_data["Company"] = folder_name  # Add company name to data
            data.append(csv_data)

    if not data:
        return jsonify({"error": "No data found"}), 404

    merged_data = pd.concat(data, ignore_index=True)

    # Apply filters based on query parameters
    if difficulty:
        merged_data = merged_data[merged_data["Difficulty"].str.lower() == difficulty.lower()]
    
    if topic:
        merged_data = merged_data[merged_data["Topics"].str.contains(topic, case=False, na=False)]
    
    if sort_by == "Frequency":
        merged_data = merged_data.sort_values(by="Frequency", ascending=False)
    elif sort_by == "Acceptance Rate":
        merged_data = merged_data.sort_values(by="Acceptance Rate", ascending=False)

    if merged_data.empty:
        return jsonify({"error": "No data found"}), 404

    return merged_data.to_json(orient="records")

@app.route('/list_files', methods=['GET'])
def list_files():
    """Lists all files in the specified Google Drive folder."""
    company_folders = get_company_folders()
    data = []

    for folder in company_folders:
        folder_name = folder["name"]
        service = get_drive_service()
        query = f"'{folder['id']}' in parents"
        
        try:
            results = []
            page_token = None
            while True:
                response = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageToken=page_token).execute()
                results.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
            
            # List all files in the folder
            for file in results:
                data.append({"name": file['name'], "id": file['id']})
        except Exception as e:
            print("Google API Error:", str(e))
    
    return jsonify(data)

@app.route('/')
def home():
    return jsonify({"message": "LeetCode API is running!"})

if __name__ == '__main__':
    app.run(debug=True)
