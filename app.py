import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import io
import os

# Google Drive API Setup
SERVICE_ACCOUNT_FILE = "service_account.json"  # Upload your service account JSON file
SCOPES = ['https://www.googleapis.com/auth/drive']

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=creds)

# Google Drive Folder ID (Replace with your actual folder ID)
FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID"

# Function to fetch CSV files from Google Drive folder
def load_data_from_drive():
    data = []
    query = f"'{FOLDER_ID}' in parents and mimeType='text/csv'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    for file in files:
        request = drive_service.files().get_media(fileId=file['id'])
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        file_stream.seek(0)
        df = pd.read_csv(file_stream)
        df["Company"] = file['name'].replace(".csv", "")  # Extract company name
        data.append(df)
    
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

# Load data (cache to optimize performance)
@st.cache_data
def get_data():
    return load_data_from_drive()

df = get_data()

# Streamlit UI with Improved Design
st.set_page_config(page_title="LeetCode Filter", layout="wide")
st.title("📌 LeetCode Question Filter")
st.markdown("### Find LeetCode problems by difficulty, topics, and companies")

# Filters (Better UI)
col1, col2, col3 = st.columns(3)
with col1:
    difficulties = st.multiselect("🎯 Select Difficulty", options=df["Difficulty"].unique())
with col2:
    topics = st.multiselect("📚 Select Topics", options=pd.unique(df["Topics"].str.split(",").sum()))
with col3:
    companies = st.multiselect("🏢 Select Company", options=df["Company"].unique())

# Apply filters
filtered_df = df.copy()
if difficulties:
    filtered_df = filtered_df[filtered_df["Difficulty"].isin(difficulties)]
if topics:
    filtered_df = filtered_df["Topics"].apply(lambda x: any(t in x for t in topics))
if companies:
    filtered_df = filtered_df[filtered_df["Company"].isin(companies)]

# Display results with better UI
st.write(f"### 🔍 Showing {len(filtered_df)} questions")
st.dataframe(
    filtered_df[["Title", "Difficulty", "Company", "Frequency", "Acceptance Rate", "Link", "Topics"]],
    height=500
)

st.markdown("---")
st.markdown("💡 **Tip:** Use the filters above to find specific problems easily.")
