import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import os
import tempfile
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
import pandas as pd
import mimetypes
import folium
from streamlit_folium import folium_static
from fpdf import FPDF
import datetime
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import base64
import requests
import plotly.express as px

# Configuration for Google Sheets API
SERVICE_ACCOUNT_FILE = st.secrets["gcp_service_account_file"]
SHEET_URL = st.secrets["sheet_url"]
GMAIL_USER = st.secrets["gmail_user"]
GMAIL_PASSWORD = st.secrets["gmail_password"]

# Google Sheets authorization
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL)
user_data_sheet = sheet.worksheet("Users")
accident_report_sheet = sheet.worksheet("AccidentReports")

# Google Drive setup
drive_service = build('drive', 'v3', credentials=creds)

def upload_file_to_drive(uploaded_file, filename, folder_id=None):
    """Uploads a file to Google Drive and returns the file's public URL."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_file.flush()
        tmp_file_path = tmp_file.name

    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(tmp_file_path, mimetype=mimetypes.guess_type(filename)[0])
    uploaded_file_drive = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    drive_service.permissions().create(fileId=uploaded_file_drive['id'], body={'role': 'reader', 'type': 'anyone'}).execute()
    file_url = f"https://drive.google.com/uc?id={uploaded_file_drive['id']}"
    os.remove(tmp_file_path)

    return file_url

# Helper Functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, subject, content):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        st.error(f"Error sending email: {e}")

# Pages
def accident_report_page():
    st.title("Accident Report")
    case_number = st.text_input("Case Number", "123456")
    accident_date = st.date_input("Accident Date")
    num_vehicles = st.number_input("Number of Vehicles", min_value=1, max_value=10)
    road_name = st.text_input("Road Name", "Unknown Road")
    accident_time = st.time_input("Accident Time")
    police_station = st.text_input("Police Station", "Unknown Police Station")
    speed_limit = st.number_input("Speed Limit", min_value=10, max_value=200)
    weather = st.selectbox("Weather", ["Clear", "Rainy", "Foggy", "Snowy"])
    road_condition = st.selectbox("Road Condition", ["Good", "Wet", "Icy"])
    driver_a_name = st.text_input("Driver A Name", "Unknown")
    driver_a_id = st.text_input("Driver A ID", "0000000000")
    driver_a_injuries = st.text_input("Driver A Injuries", "None")
    driver_b_name = st.text_input("Driver B Name", "Unknown")
    driver_b_id = st.text_input("Driver B ID", "0000000000")
    driver_b_injuries = st.text_input("Driver B Injuries", "None")

    # Uploads
    driver_a_license_image = st.file_uploader("Upload Driver A's License Image", type=['jpg', 'png'])
    driver_a_license_url = upload_file_to_drive(driver_a_license_image, "driver_a_license.jpg") if driver_a_license_image else None
    driver_b_license_image = st.file_uploader("Upload Driver B's License Image", type=['jpg', 'png'])
    driver_b_license_url = upload_file_to_drive(driver_b_license_image, "driver_b_license.jpg") if driver_b_license_image else None
    accident_images = st.file_uploader("Upload accident scene photos", type=['jpg', 'png'], accept_multiple_files=True)
    accident_image_urls = [upload_file_to_drive(image, f"accident_image_{i}.jpg") for i, image in enumerate(accident_images)] if accident_images else []
    accident_video = st.file_uploader("Upload accident video", type=['mp4'])
    accident_video_url = upload_file_to_drive(accident_video, "accident_video.mp4") if accident_video else None

    if st.button("Save Report"):
        accident_report_sheet.append_row([case_number, accident_date.strftime("%Y-%m-%d"), num_vehicles, road_name, accident_time.strftime("%H:%M"), police_station, speed_limit, weather, road_condition, driver_a_name, driver_a_id, driver_a_injuries, driver_a_license_url, driver_b_name, driver_b_id, driver_b_injuries, driver_b_license_url, ', '.join(accident_image_urls), accident_video_url])
        st.success("Accident report saved!")

# Main app with navigation
def main():
    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Select Page", ["📄 Accident Report"])
    if option == "📄 Accident Report":
        accident_report_page()

if __name__ == "__main__":
    main()
