import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import os
import tempfile
from googleapiclient.http import MediaFileUpload
import pdfkit
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
from streamlit_option_menu import option_menu
import plotly.express as px
from streamlit_folium import st_folium
import time

# Hide Streamlit style elements
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""


# Access secret values from the secrets store
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

# Define the scopes for accessing Google Sheets and Google Drive
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = credentials.with_scopes(scope)

# Authorize Google Sheets access
client = gspread.authorize(credentials)

# Get the Google Sheets URL from secrets
SHEET_URL = st.secrets["sheets"]["SHEET_URL"]

# Open the Google Sheets using the URL from secrets
sheet = client.open_by_url(SHEET_URL)

# Access specific sheets (worksheets)
user_data_sheet = sheet.worksheet("Users")  # User data sheet
accident_report_sheet = sheet.worksheet("AccidentReports")  # Accident report sheet
injury_assessment_sheet = sheet.worksheet("InjuryAssessment")  # Injury assessment sheet
raf_1_sheet = sheet.worksheet("Claims")  # Claim sheet
supplier_claim_sheet = sheet.worksheet("SupplierClaims")  # Supplier claim sheet


# Access Gmail credentials
gmail_user = st.secrets["gmail"]["GMAIL_USER"]
gmail_password = st.secrets["gmail"]["GMAIL_PASSWORD"]



# Google Drive setup
drive_service = build('drive', 'v3', credentials=credentials)




def upload_file_to_drive(uploaded_file, filename, folder_id=None):
    """Uploads a file to Google Drive and returns the file's public URL."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        # Write the uploaded file's contents to the temporary file
        tmp_file.write(uploaded_file.getbuffer())
        tmp_file.flush()
        tmp_file_path = tmp_file.name

    # Set up file metadata for Google Drive
    file_metadata = {'name': filename}
    if folder_id:
        file_metadata['parents'] = ["1nRWfZjqe-f6GO24uxayYMQYR0rr6RG7U"]  # Optional: specify folder

    # Create a MediaFileUpload object using the temporary file path
    media = MediaFileUpload(tmp_file_path, mimetype=mimetypes.guess_type(filename)[0])

    # Upload the file to Google Drive
    uploaded_file_drive = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Make the file public
    drive_service.permissions().create(fileId=uploaded_file_drive['id'], body={'role': 'reader', 'type': 'anyone'}).execute()

    # Get the public file URL
    file_url = f"https://drive.google.com/uc?id={uploaded_file_drive['id']}"

    # Clean up temporary file
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

def generate_pdf_content(first_responder_info, report_data, report_type):
    # Helper function to get an image URL or a placeholder if not provided
    def get_image_url(driver_info, key):
        return driver_info.get(key, "path/to/placeholder_image.jpg")  # Path to a placeholder image if no image is provided

    # Dynamic content based on the report type
    if report_type == "Accident Report":
        html_content = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
            <h1>Accident Report</h1>
            <h2>First Responder Information</h2>
            <p><strong>Officer Name:</strong> {first_responder_info.get('Officer Name', 'N/A')}</p>
            <p><strong>Role:</strong> {first_responder_info.get('Role', 'N/A')}</p>
            <p><strong>Department:</strong> {first_responder_info.get('Department', 'N/A')}</p>

            <h2>Accident Report Summary</h2>
            <p><strong>Case Number:</strong> {report_data.get('Accident Case Number', 'N/A')}</p>
            <p><strong>Accident Date:</strong> {report_data.get('Accident Date', 'N/A')}</p>
            <p><strong>Number of Vehicles:</strong> {report_data.get('Number of Vehicles', 'N/A')}</p>
            <p><strong>Accident Time:</strong> {report_data.get('Accident Time', 'N/A')}</p>
            <p><strong>Road Name:</strong> {report_data.get('Road Name', 'N/A')}</p>
            <p><strong>Police Station:</strong> {report_data.get('Police Station', 'N/A')}</p>
            <p><strong>Speed Limit:</strong> {report_data.get('Speed Limit', 'N/A')}</p>
            <p><strong>Weather:</strong> {report_data.get('Weather', 'N/A')}</p>
            <p><strong>Road Condition:</strong> {report_data.get('Road Condition', 'N/A')}</p>

            <h2>Driver Information</h2>
            <h3>Driver A</h3>
            <p><strong>Name:</strong> {report_data.get('Driver A', {}).get('Name', 'N/A')}</p>
            <p><strong>ID:</strong> {report_data.get('Driver A', {}).get('ID', 'N/A')}</p>
            <p><strong>Injuries:</strong> {report_data.get('Driver A', {}).get('Injuries', 'N/A')}</p>
            <img src="{get_image_url(report_data.get('Driver A', {}), 'License Image')}" width="200px" />

            <h3>Driver B</h3>
            <p><strong>Name:</strong> {report_data.get('Driver B', {}).get('Name', 'N/A')}</p>
            <p><strong>ID:</strong> {report_data.get('Driver B', {}).get('ID', 'N/A')}</p>
            <p><strong>Injuries:</strong> {report_data.get('Driver B', {}).get('Injuries', 'N/A')}</p>
            <img src="{get_image_url(report_data.get('Driver B', {}), 'License Image')}" width="200px" />

            <h2>Accident Photos</h2>
            {''.join(f'<img src="{img_url}" width="300px" />' for img_url in report_data.get('Accident Images', []))}
        </body>
        </html>
        """

    elif report_type == "Serious Injury Assessment Report":
        html_content = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
            <h1>Serious Injury Assessment Report</h1>
            <h2>Patient Information</h2>
            <p><strong>Patient Name:</strong> {report_data.get('Patient Name', 'N/A')}</p>
            <p><strong>Assessment Date:</strong> {report_data.get('Assessment Date', 'N/A')}</p>
            <p><strong>Injury Description:</strong> {report_data.get('Injury Description', 'N/A')}</p>
            <p><strong>Severity:</strong> {report_data.get('Injury Severity', 'N/A')}</p>

            <h2>Medical Details</h2>
            <p><strong>Treatment Given:</strong> {report_data.get('Medical Treatment', 'N/A')}</p>
            <p><strong>Current Symptoms:</strong> {report_data.get('Current Symptoms', 'N/A')}</p>
            <p><strong>Diagnosis:</strong> {report_data.get('Diagnosis', 'N/A')}</p>
            <p><strong>Clinical Studies:</strong> {report_data.get('Clinical Studies', 'N/A')}</p>
        </body>
        </html>
        """

    elif report_type == "RAF 1 Form":
        html_content = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
            <h1>RAF 1 Form</h1>
            <h2>Claimant Information</h2>
            <p><strong>Claimant Name:</strong> {report_data.get('Claimant Name', 'N/A')}</p>
            <p><strong>Claimant ID:</strong> {report_data.get('Claimant ID', 'N/A')}</p>
            <p><strong>Claim Date:</strong> {report_data.get('Claim Date', 'N/A')}</p>
            <p><strong>Description:</strong> {report_data.get('Claim Description', 'N/A')}</p>

            <h2>Additional Details</h2>
            <p><strong>Date of Birth:</strong> {report_data.get('Claimant DOB', 'N/A')}</p>
            <p><strong>Residential Address:</strong> {report_data.get('Claimant Residential Address', 'N/A')}</p>
            <p><strong>Postal Address:</strong> {report_data.get('Claimant Postal Address', 'N/A')}</p>
            <p><strong>Email:</strong> {report_data.get('Claimant Email', 'N/A')}</p>
        </body>
        </html>
        """

    elif report_type == "SUPPLIER CLAIM FORM":
        html_content = f"""
        <html>
        <head><style>body {{ font-family: Arial; }}</style></head>
        <body>
            <h1>Supplier Claim Form</h1>
            <h2>Supplier Information</h2>
            <p><strong>Supplier Name:</strong> {report_data.get('Supplier Name', 'N/A')}</p>
            <p><strong>Practice Number:</strong> {report_data.get('Practice Number', 'N/A')}</p>
            <p><strong>Tax Reference Number:</strong> {report_data.get('Tax Reference Number', 'N/A')}</p>

            <h2>Claim Information</h2>
            <p><strong>Claim for Emergency Treatment:</strong> {report_data.get('Claim for Emergency Treatment', 'N/A')}</p>
            <p><strong>Total Amount Claimed:</strong> {report_data.get('Total Amount Claimed', 'N/A')}</p>
        </body>
        </html>
        """

    else:
        html_content = "<p>Report type not recognized</p>"

    return html_content



def create_pdf_from_html(html_content, file_name):
    # Convert HTML to PDF using pdfkit or another library
    pdf_path = f"/path/to/save/{file_name}"
    pdfkit.from_string(html_content, pdf_path)  # Save the PDF to the desired path
    return pdf_path


def create_pdf(first_responder_info, report_data, file_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Accident Report", ln=True, align='C')
    pdf.ln(10)

    # First Responder Information
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="First Responder Information", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Officer Name: {first_responder_info.get('Officer Name', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Role: {first_responder_info.get('Role', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Department: {first_responder_info.get('Department', 'N/A')}", ln=True)
    pdf.ln(10)
    # Accident Report Summary
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Accident Report Summary", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Case Number: {report_data.get('Accident Case Number', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Accident Date: {report_data.get('Accident Date', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Number of Vehicles: {report_data.get('Number of Vehicles', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Accident Time: {report_data.get('Accident Time', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Road Name: {report_data.get('Road Name', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Police Station: {report_data.get('Police Station', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Speed Limit: {report_data.get('Speed Limit', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Weather: {report_data.get('Weather', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Road Condition: {report_data.get('Road Condition', 'N/A')}", ln=True)
    pdf.ln(10)

    # Driver Information
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Driver Information", ln=True)
    pdf.set_font("Arial", 'B', 12)

    # Driver A
    pdf.cell(200, 10, txt="Driver A", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Name: {report_data.get('Driver A', {}).get('Name', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"ID: {report_data.get('Driver A', {}).get('ID', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Injuries: {report_data.get('Driver A', {}).get('Injuries', 'N/A')}", ln=True)
    # Add image
    driver_a_license_image_url = report_data.get('Driver A', {}).get('License Image')
    if driver_a_license_image_url:
        img_path = download_image(driver_a_license_image_url)
        pdf.image(img_path, x=10, y=pdf.get_y(), w=100)
    pdf.ln(10)

    # Driver B
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Driver B", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Name: {report_data.get('Driver B', {}).get('Name', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"ID: {report_data.get('Driver B', {}).get('ID', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Injuries: {report_data.get('Driver B', {}).get('Injuries', 'N/A')}", ln=True)
    # Add image
    driver_b_license_image_url = report_data.get('Driver B', {}).get('License Image')
    if driver_b_license_image_url:
        img_path = download_image(driver_b_license_image_url)
        pdf.image(img_path, x=10, y=pdf.get_y(), w=100)
    pdf.ln(10)

    # Accident Photos
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Accident Photos", ln=True)
    pdf.set_font("Arial", size=12)

    for img_url in report_data.get('Accident Images', []):
        img_path = download_image(img_url)
        pdf.image(img_path, x=10, y=pdf.get_y(), w=180)
        pdf.ln(100)  # Adjust spacing for images

    # Save PDF
    pdf_output_path = os.path.join(tempfile.gettempdir(), file_name)
    pdf.output(pdf_output_path)

    return pdf_output_path

def download_image(image_url):
    """Downloads an image from a URL and returns the local file path."""
    response = requests.get(image_url)
    if response.status_code == 200:
        img_path = os.path.join(tempfile.gettempdir(), os.path.basename(image_url))
        with open(img_path, 'wb') as img_file:
            img_file.write(response.content)
        return img_path
    else:
        st.error(f"Error downloading image from URL: {image_url}")
        return None




# Pages
def accident_report_page():
    st.title("Accident Management System")

    # Helper function for driver information to reduce redundancy
    def driver_info_section(driver_label):
        st.markdown(f"### {driver_label} Information")
        driver_name = st.text_input(f"{driver_label} Name", "Unknown")
        driver_id = st.text_input(f"{driver_label} ID", "0000000000")
        driver_injuries = st.text_input(f"{driver_label} Injuries", "None")
        driver_license_number = st.text_input(f"{driver_label} License Number")
        driver_license_date_issued = st.date_input(f"{driver_label} License Date Issued")
        driver_license_endorsements = st.text_input(f"{driver_label} License Endorsements (if any)")
        driver_physical_mental_defects = st.text_input(f"{driver_label} Physical/Mental Defects (if any)")
        driver_residential_address = st.text_input(f"{driver_label} Residential Address")
        driver_work_address = st.text_input(f"{driver_label} Work Address")
        driver_employment_status = st.radio(f"{driver_label} Employment Status", ["Yes", "No"])
        driver_company = st.text_input(f"{driver_label} Company of Employment") if driver_employment_status == "Yes" else "N/A"
        driver_medical_aid = st.radio(f"{driver_label} Medical Aid", ["Yes", "No"])
        driver_medical_aid_company = st.text_input(f"{driver_label} Medical Aid Company Name") if driver_medical_aid == "Yes" else "N/A"
        driver_car_insurance = st.radio(f"{driver_label} Car Insurance", ["Yes", "No"])
        driver_insurance_company = st.text_input(f"{driver_label} Insurance Company Name") if driver_car_insurance == "Yes" else "N/A"
        driver_under_influence = st.radio(f"{driver_label} Under the Influence", ["Yes", "No"])

        # Upload driver's license image
        driver_license_image = st.file_uploader(f"Upload {driver_label}'s License Image", type=['jpg', 'png'])
        driver_license_url = upload_file_to_drive(driver_license_image, f"{driver_label.lower()}_license.jpg") if driver_license_image else None

        return [driver_name, driver_id, driver_injuries, driver_license_number, driver_license_date_issued,
                driver_license_endorsements, driver_physical_mental_defects, driver_residential_address,
                driver_work_address, driver_employment_status, driver_company, driver_medical_aid,
                driver_medical_aid_company, driver_car_insurance, driver_insurance_company,
                driver_under_influence, driver_license_url]

    # Create subtabs for different report types
    tabs = st.tabs(["Accident Report", "Serious Injury Assessment Report", "RAF 1 Form", "SUPPLIER CLAIM FORM"])

    # Accident Report Tab
    with tabs[0]:
        st.subheader("Accident Report")

        # Accident information fields with validation
        case_number = st.text_input("Case Number", "123456")
        if not case_number:
            st.error("Case Number is required!")

        accident_date = st.date_input("Accident Date")
        if not accident_date:
            st.error("Accident Date is required!")

        road_name = st.text_input("Road Name", "Unknown Road")
        accident_time = st.time_input("Accident Time")
        police_station = st.text_input("Police Station", "Unknown Police Station")
        police_reference_number = st.text_input("Police Reference Number")
        speed_limit = st.number_input("Speed Limit", min_value=10, max_value=200)
        weather = st.selectbox("Weather", ["Clear", "Rainy", "Foggy", "Snowy"])
        road_condition = st.selectbox("Road Condition", ["Good", "Wet", "Icy"])

        # Vehicle Information (Dynamically adding vehicles)
        st.markdown("### Vehicles Involved")
        num_vehicles = st.number_input("Number of Vehicles", min_value=1, step=1)
        vehicle_info = []
        for i in range(num_vehicles):
            with st.expander(f"Vehicle {i+1} Details", expanded=True):
                vehicle_info.append([
                    st.text_input(f"Vehicle {i+1} Registration Number"),
                    st.text_input(f"Vehicle {i+1} Make"),
                    st.text_input(f"Vehicle {i+1} Model"),
                    st.text_input(f"Vehicle {i+1} Year"),
                    st.text_input(f"Vehicle {i+1} Color")
                ])

        # Reuse the driver info helper function for Driver A and Driver B
        driver_a_info = driver_info_section("Driver A")
        driver_b_info = driver_info_section("Driver B")

        # Witness Information (Dynamically adding witnesses)
        st.markdown("### Witness Information")
        num_witnesses = st.number_input("Number of Witnesses", min_value=0, step=1, value=0)
        witness_info = []
        for i in range(num_witnesses):
            with st.expander(f"Witness {i+1} Details", expanded=True):
                witness_info.append([
                    st.text_input(f"Witness {i+1} Name"),
                    st.text_input(f"Witness {i+1} ID"),
                    st.text_input(f"Witness {i+1} Contact Details (Phone, Email, etc.)")
                ])

        # File upload section for accident images, videos, and voice notes
        st.markdown("### File Uploads")
        accident_images = st.file_uploader("Upload accident scene photos (max 20)", type=['jpg', 'png'], accept_multiple_files=True)
        accident_image_urls = [upload_file_to_drive(image, f"accident_image_{i}.jpg") for i, image in enumerate(accident_images)] if accident_images else []

        accident_video = st.file_uploader("Upload accident video (max 5 min)", type=['mp4'])
        accident_video_url = upload_file_to_drive(accident_video, "accident_video.mp4") if accident_video else None

        voice_notes = st.file_uploader("Upload voice notes (max 5 min each)", type=['mp3'], accept_multiple_files=True)
        voice_note_urls = [upload_file_to_drive(note, f"voice_note_{i}.mp3") for i, note in enumerate(voice_notes)] if voice_notes else []

        # Form Validation: Ensure required fields are not empty
        if st.button("Save Report"):
          if not case_number or not accident_date:
              st.error("Please fill in all required fields!")
          else:
              try:
                  # Append the row to the accident_report_sheet
                  accident_report_sheet.append_row([
                      case_number, 
                      accident_date.strftime("%Y-%m-%d"),  # Format accident date
                      num_vehicles, 
                      road_name, 
                      accident_time.strftime("%H:%M"),  # Format accident time
                      police_station, 
                      police_reference_number, 
                      speed_limit, 
                      weather, 
                      road_condition, 
                      ', '.join([str(v) for v in vehicle_info]),  # Vehicle Information
                      ', '.join(map(str, driver_a_info)),  # Driver A Info
                      ', '.join(map(str, driver_b_info)),  # Driver B Info
                      ', '.join([str(w) for w in witness_info]),  # Witness Information
                      ', '.join(accident_image_urls),  # Accident Image URLs (Join list into string)
                      accident_video_url if accident_video_url else 'N/A',  # Handle missing video URL
                      ', '.join(voice_note_urls)  # Voice Note URLs (Join list into string)
                  ])
                  st.success("Accident report saved successfully!")
              except Exception as e:
                  st.error(f"Error saving accident report: {e}")


    # Serious Injury Assessment Report Tab
    with tabs[1]:
        st.subheader("Serious Injury Assessment Report")

        # Add input fields specific to the Serious Injury Assessment Report
        patient_name = st.text_input("Patient Name")
        patient_id = st.text_input("Patient ID")
        claim_number = st.text_input("Claim Number (if available)")
        contact_number = st.text_input("Contact Number")
        assessment_date = st.date_input("Assessment Date")
        accident_date = st.date_input("Date of Accident")
        medical_practitioner_name = st.text_input("Medical Practitioner Name")
        practitioner_hpcsa_bhf = st.text_input("Practice Number (HPCSA and/or BHF)")
        practitioner_contact = st.text_input("Medical Practitioner Contact Number")
        practitioner_email = st.text_input("Medical Practitioner Email")

        # Injury Details
        injury_description = st.text_area("Injury Description")
        injury_severity = st.selectbox("Injury Severity", ["Mild", "Moderate", "Severe"])

        # Additional Assessment Fields
        treatment_given = st.text_area("Medical Treatment Rendered (from date of accident to present)")
        current_symptoms = st.text_area("Current Symptoms and Complaints")
        diagnosis = st.text_area("Diagnosis")
        clinical_studies = st.text_area("Clinical Studies (X-rays, MRI, etc.)")
        medical_history = st.text_area("Medical History")
        personal_history = st.text_area("Social and Personal History")
        educational_occupational_history = st.text_area("Educational and Occupational History")
        has_reached_mmi = st.selectbox("Has the Patient Reached Maximum Medical Improvement (MMI)?", ["Yes", "No"])

        # Save the report to Google Sheets
        if st.button("Save Serious Injury Report"):
            report_data = [
                patient_name, patient_id, claim_number, contact_number, assessment_date.strftime("%Y-%m-%d"),
                accident_date.strftime("%Y-%m-%d"), medical_practitioner_name, practitioner_hpcsa_bhf, practitioner_contact,
                practitioner_email, injury_description, injury_severity, treatment_given, current_symptoms,
                diagnosis, clinical_studies, medical_history, personal_history, educational_occupational_history,
                has_reached_mmi
            ]
            try:
                injury_assessment_sheet.append_row(report_data)
                st.success("Serious Injury Assessment Report saved successfully!")
            except Exception as e:
                st.error(f"Error saving report: {e}")

    # RAF 1 Form Tab
    with tabs[2]:
        st.subheader("RAF 1 Form")

        # Add fields relevant to RAF 1 Form (similar to Serious Injury Form)
        form_fields = [
            "Claimant Name", "Claimant ID", "Claim Number", "Date of Birth", "Residential Address", "Postal Address",
            "Phone Number", "Email Address", "Occupation", "Employer Name", "Employer Address"
        ]
        raf_1_data = [st.text_input(field) for field in form_fields]

        # Save the form to Google Sheets
        if st.button("Save RAF 1 Form"):
            try:
                raf_1_sheet.append_row(raf_1_data)
                st.success("RAF 1 Form saved successfully!")
            except Exception as e:
                st.error(f"Error saving RAF 1 Form: {e}")

    # Supplier Claim Form Tab
    with tabs[3]:
        st.subheader("SUPPLIER CLAIM FORM")

        # Add fields relevant to Supplier Claim Form
        supplier_name = st.text_input("Supplier Name")
        supplier_contact = st.text_input("Supplier Contact Number")
        supplier_email = st.text_input("Supplier Email Address")
        claim_amount = st.number_input("Claim Amount", min_value=0.0)
        claim_description = st.text_area("Claim Description")

        # Save the form to Google Sheets
        if st.button("Save Supplier Claim"):
            supplier_claim_data = [supplier_name, supplier_contact, supplier_email, claim_amount, claim_description]
            try:
                supplier_claim_sheet.append_row(supplier_claim_data)
                st.success("Supplier Claim saved successfully!")
            except Exception as e:
                st.error(f"Error saving Supplier Claim: {e}")






# Global report_type_map
report_type_map = {
    "Accident Report": [
        'case_number', 
        'accident_date', 
        'num_vehicles', 
        'road_name', 
        'accident_time', 
        'police_station', 
        'police_reference_number', 
        'speed_limit', 
        'weather', 
        'road_condition', 
        'vehicle_info',  # New field for vehicle information
        'driver_a_info',  # New field for Driver A information
        'driver_b_info',  # New field for Driver B information
        'witness_info',  # New field for witness information
        'accident_image_urls',  # Field for image URLs
        'accident_video_url',  # Field for accident video URL
        'voice_note_urls'  # Field for voice note URLs
    ],
    "Serious Injury Assessment Report": [
        'patient_name', 
        'assessment_date', 
        'injury_description', 
        'injury_severity', 
        'treatment_given', 
        'current_symptoms', 
        'diagnosis', 
        'clinical_studies'
    ],
    "RAF 1 Form": [
        'claimant_name', 
        'claimant_id', 
        'claim_date', 
        'claim_description', 
        'claimant_dob', 
        'claimant_residential_address', 
        'claimant_postal_address', 
        'claimant_email'
    ],
    "SUPPLIER CLAIM FORM": [
        'supplier_name', 
        'practice_number', 
        'tax_reference_number', 
        'supplier_physical_address', 
        'supplier_email', 
        'claim_for_emergency_treatment', 
        'total_amount_claimed'
    ]
}


def view_reports():
    st.title("View All Reports")

    # Create tabs for report types
    selected_tab = st.selectbox("Select Report Type", ["Accident Report", "Serious Injury Assessment Report", "RAF 1 Form", "SUPPLIER CLAIM FORM"])

    # Get headers for selected report type
    expected_headers = report_type_map.get(selected_tab, [])
    report_data = None  # Initialize report_data to None

    try:
        # Fetch report data from corresponding Google Sheets based on selected tab
        if selected_tab == "Accident Report":
            report_data = accident_report_sheet.get_all_records()
        elif selected_tab == "Serious Injury Assessment Report":
            report_data = injury_assessment_sheet.get_all_records()
        elif selected_tab == "RAF 1 Form":
            report_data = raf_1_sheet.get_all_records()
        elif selected_tab == "SUPPLIER CLAIM FORM":
            report_data = supplier_claim_sheet.get_all_records()

        if report_data:
            df = pd.DataFrame(report_data)

            # Check if DataFrame contains any data
            if df.empty:
                st.warning(f"No {selected_tab} data found.")
                return  # Exit early if no data found

            # Convert specific columns to strings to avoid type issues
            for col in ['case_number', 'driver_a_id', 'driver_b_id', 'num_vehicles']:
                if col in df.columns:
                    df[col] = df[col].astype(str)

            # Ensure the expected headers are present in the DataFrame
            if expected_headers and expected_headers[0] in df.columns:
                search_column = expected_headers[0]
                search_term = st.text_input(f"Search by {search_column}")

                # Filter DataFrame based on the search term
                if search_term:
                    df = df[df[search_column].astype(str).str.contains(search_term, case=False, na=False)]

                # Display the data
                st.write(f"All {selected_tab}s", df)

                # Allow user to select a specific report to edit
                if not df.empty:
                    selected_report = st.selectbox(f"Select a {selected_tab} to edit", df[search_column].astype(str))
                    
                    if selected_report:
                        # Ensure there is a matching row for the selected report
                        report_to_edit = df[df[search_column] == selected_report]

                        if not report_to_edit.empty:
                            report_to_edit = report_to_edit.iloc[0].to_dict()
                            edit_report(report_to_edit, df, selected_tab)
                        else:
                            st.warning(f"No matching {selected_tab} found for the selected report.")
                else:
                    st.warning(f"No {selected_tab} data found after filtering.")
            else:
                st.warning(f"Expected column '{expected_headers[0]}' not found in the data.")
        else:
            st.warning(f"No {selected_tab} data found.")

    except TypeError as te:
        st.error(f"TypeError encountered: {te}")
    except Exception as e:
        st.error(f"Error fetching reports: {e}")








def edit_report(report_data, df, report_type):
    st.subheader(f"Edit {report_type}")

    # Editing form for Accident Report
    if report_type == "Accident Report":
        case_number = st.text_input("Case Number", report_data['case_number'])
        accident_date = st.date_input("Accident Date", pd.to_datetime(report_data['accident_date']))
        num_vehicles = st.number_input("Number of Vehicles", min_value=1, max_value=10, value=int(report_data['num_vehicles']))
        # Add the rest of the fields here...

    # Save changes button
    if st.button("Save Changes"):
        # Update the Google Sheets (your logic here)
        st.success(f"{report_type} updated successfully!")

    # PDF Generation
    if st.button("Generate PDF"):
        pdf_path = generate_and_download_pdf(report_data, report_type)
        with open(pdf_path, "rb") as file:
            st.download_button(f"Download {report_type} PDF", data=file, file_name=pdf_path)

def generate_and_download_pdf(report_data, report_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"{report_type} Report", ln=True, align='C')
    for key, value in report_data.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)

    pdf_output = f"{report_type}_report.pdf"
    pdf.output(pdf_output)
    return pdf_output









def emergency_assistance_dashboard():
    st.title("Emergency Assistance Dashboard")

    st.subheader("Emergency Services")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button('🚑 Call Ambulance'):
            st.write("[Click here to call an ambulance](tel:+911)")

    with col2:
        if st.button('🚓 Call Police'):
            st.write("[Click here to call the police](tel:+10111)")

    with col3:
        if st.button('🚗 Call Car Crash Service'):
            st.write("[Click here to call car crash services](tel:+0800-123-456)")




def accident_data_dashboard():
    st.title('Accident Data Dashboard')


    # Sample data with 5 static locations
    data = pd.DataFrame({
        'Location': ['Location 1', 'Location 2', 'Location 3', 'Location 4', 'Location 5'],
        'Accidents': [10, 15, 7, 5, 20],
        'Severity': [2.5, 3.0, 1.8, 2.0, 4.5],
        'Latitude': [-33.918861, -34.418861, -33.928861, -33.948861, -34.128861],
        'Longitude': [18.423300, 19.423300, 18.533300, 18.623300, 19.223300]
    })


    # Simulate the user's current location
    def simulate_geolocation():
        return -33.918861, 18.423300


    current_lat, current_lon = simulate_geolocation()
    st.write(f"Simulated current location is: ({current_lat}, {current_lon})")


    # Interactive Folium map centered on the user's location
    m = folium.Map(location=[current_lat, current_lon], zoom_start=10)


    # Adding markers for static accident locations
    for i, row in data.iterrows():
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"Location: {row['Location']}\nAccidents: {row['Accidents']}\nSeverity: {row['Severity']}",
        ).add_to(m)


    # Display the interactive map
    st_folium(m, width=725)


    # Filter data based on user selection
    severity_filter = st.slider('Select Severity', min_value=1.0, max_value=5.0, step=0.1)
    filtered_data = data[data['Severity'] >= severity_filter]


    # Bar chart visualization for filtered data
    fig = px.bar(filtered_data, x='Location', y='Accidents', color='Severity', title='Accidents by Location')
    st.plotly_chart(fig)

def get_case_numbers():
    """
    Fetches the case numbers from the AccidentReports worksheet in Google Sheets.

    Returns:
        A list of case numbers.
    """
    try:
        # Fetch all records from the "AccidentReports" sheet
        report_data = accident_report_sheet.get_all_records()

        # Ensure case-insensitive column handling, check if "case number" or "Case Number" exists
        if report_data and "Case Number" in report_data[0]:
            case_number = [report["Case Number"] for report in report_data if report["Case Number"]]
        elif "case_number" in report_data[0]:
            case_number = [report["case_number"] for report in report_data if report["case_number"]]
        else:
            case_number = []

        return case_number

    except Exception as e:
        st.error(f"Error fetching case numbers: {e}")
        return []



def collaboration_sharing():
    st.title('Collaboration and Sharing')

    # Subtabs for Medical Report, SAP Report, and Invite Collaborators
    tab1, tab2, tab3 = st.tabs(["Medical Report Form", "SAP Report Form", "Invite Collaborators"])

    # Medical Report Form tab
    with tab1:
        st.header("Medical Report Form")

        # Input fields for Medical Report
        hospital_name = st.text_input("Name of Hospital")
        doctor_name = st.text_input("Name of Doctor")
        hospital_location = st.text_input("Location of Hospital")
        case_number_link = st.selectbox("Link to Case Number", ["Select a case"] + get_case_numbers(), key="medical_case_number_link")  # Unique key
        medical_report_date = st.date_input("Date", value=datetime.date.today(), key="medical_report_date")  # Unique key for date
        medical_report_upload = st.file_uploader("Upload Medical Report", type=["pdf", "docx"], key="medical_report_upload")

        if st.button("Submit Medical Report", key="submit_medical_report"):
            # Save Medical Report data to Google Sheets
            medical_report_data = [hospital_name, doctor_name, hospital_location, case_number_link, str(medical_report_date)]
            if medical_report_upload is not None:
                file_url = upload_file_to_drive(medical_report_upload, f"medical_report_{hospital_name}.pdf")
                medical_report_data.append(file_url)
            else:
                medical_report_data.append("No document uploaded")

            # Append medical report data to Google Sheets (create a new worksheet for medical reports if needed)
            medical_report_sheet = sheet.worksheet("MedicalReports")
            medical_report_sheet.append_row(medical_report_data)

            st.success("Medical report submitted successfully!")

    # SAP Report Form tab
    with tab2:
        st.header("SAP Report Form")

        # Input fields for SAP Report
        police_station_name = st.text_input("Name of Police Station")
        officer_name = st.text_input("Name of Officer")
        police_station_location = st.text_input("Location of Police Station")
        case_number_link = st.selectbox("Link to Case Number", ["Select a case"] + get_case_numbers(), key="sap_case_number_link")  # Unique key
        sap_report_date = st.date_input("Date", value=datetime.date.today(), key="sap_report_date")  # Unique key for date
        sap_report_upload = st.file_uploader("Upload SAP Report", type=["pdf", "docx"], key="sap_report_upload")

        if st.button("Submit SAP Report", key="submit_sap_report"):
            # Save SAP Report data to Google Sheets
            sap_report_data = [police_station_name, officer_name, police_station_location, case_number_link, str(sap_report_date)]
            if sap_report_upload is not None:
                file_url = upload_file_to_drive(sap_report_upload, f"sap_report_{police_station_name}.pdf")
                sap_report_data.append(file_url)
            else:
                sap_report_data.append("No document uploaded")

            # Append SAP report data to Google Sheets (create a new worksheet for SAP reports if needed)
            sap_report_sheet = sheet.worksheet("SAPReports")
            sap_report_sheet.append_row(sap_report_data)

            st.success("SAP report submitted successfully!")

    # Invite Collaborators tab
    with tab3:
        st.header("Invite Collaborators")

        # Existing invite collaborators section
        emails = st.text_area('Enter email addresses separated by commas')
        subject = st.text_input("Subject")
        document_upload = st.file_uploader("Upload Document", type=["pdf", "docx", "xlsx"], key="collaborator_document_upload")
        case_number_link = st.selectbox("Link to Case Number", ["Select a case"] + get_case_numbers(), key="collaborators_case_number_link")  # Unique key

        if st.button('Send Invitations', key="send_invitations"):
            # Logic to send invitations (email function, link document and case number, etc.)
            if document_upload is not None:
                file_url = upload_file_to_drive(document_upload, f"collaboration_document_{subject}.pdf")
            else:
                file_url = "No document uploaded"

            # Send the email with the document
            content = f"Subject: {subject}\nLinked Case Number: {case_number_link}\nDocument: {file_url}"
            for email in emails.split(","):
                send_email(email.strip(), subject, content)

            st.success(f'Invitations sent to: {emails}')



# Main app with navigation


def main():
    # Sidebar menu with icons
    with st.sidebar:
        selected = option_menu(
            menu_title="Accident Management System",  # Title for the sidebar menu
            options=["Accident Report", "View Reports", "Emergency Assistance", "Accident Data", "Collaboration and Sharing"],
            icons=["file-text", "bar-chart", "phone", "activity", "people"],
            menu_icon="cast",  # Icon for the menu
            default_index=0,
        )

    # Handle the selected menu option
    if selected == "Accident Report":
        accident_report_page()
    elif selected == "View Reports":
        view_reports()
    elif selected == "Emergency Assistance":
        emergency_assistance_dashboard()
    elif selected == "Accident Data":
        accident_data_dashboard()
    elif selected == "Collaboration and Sharing":
        collaboration_sharing()

if __name__ == "__main__":
    main()
