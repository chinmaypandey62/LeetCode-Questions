import os
import json
from flask import Flask, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load credentials from environment variable
service_account_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# Initialize Google Drive API
drive_service = build("drive", "v3", credentials=credentials)

# Function to get folder ID by name
def get_folder_id(folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get("files", [])
    return folders[0]["id"] if folders else None

# Function to list company folders inside 'company_leetcode'
def get_company_folders(parent_folder_id):
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

# Function to get all.csv inside each company folder
def get_csv_files(company_folders):
    data = {}
    for folder in company_folders:
        company_name = folder["name"]
        folder_id = folder["id"]
        query = f"'{folder_id}' in parents and name='all.csv' and mimeType='text/csv'"
        result = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = result.get("files", [])
        if files:
            data[company_name] = {
                "file_id": files[0]["id"],
                "file_name": files[0]["name"],
                "link": files[0]["webViewLink"]
            }
    return data

@app.route("/")
def home():
    return "Google Drive API Connected Securely! 🔒"

@app.route("/fetch_questions", methods=["GET"])
def fetch_questions():
    try:
        # Get parent folder ID
        parent_folder_id = get_folder_id("company_leetcode")
        if not parent_folder_id:
            return jsonify({"error": "Folder 'company_leetcode' not found"}), 404

        # Get company folders
        company_folders = get_company_folders(parent_folder_id)
        if not company_folders:
            return jsonify({"message": "No company folders found"}), 404

        # Get CSV files
        data = get_csv_files(company_folders)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
