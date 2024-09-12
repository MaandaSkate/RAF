import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import os
import tempfile
#from googleapiclient.http import MediaFileUpload
#from googleapiclient.discovery import build
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

def generate_pdf_content(first_responder_info, report_data):
    # Helper function to get an image URL or a placeholder if not provided
    def get_image_url(driver_info, key):
        return driver_info.get(key, "path/to/placeholder_image.jpg")  # Path to a placeholder image if no image is provided

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

    return html_content


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
    st.title("Accident Report")

    # Editable accident report fields
    case_number = st.text_input("Case Number", "123456")
    accident_date = st.date_input("Accident Date")
    num_vehicles = st.number_input("Number of Vehicles", min_value=1, max_value=10)
    road_name = st.text_input("Road Name", "Unknown Road")
    accident_time = st.time_input("Accident Time")
    police_station = st.text_input("Police Station", "Unknown Police Station")
    speed_limit = st.number_input("Speed Limit", min_value=10, max_value=200)
    weather = st.selectbox("Weather", ["Clear", "Rainy", "Foggy", "Snowy"])
    road_condition = st.selectbox("Road Condition", ["Good", "Wet", "Icy"])

    # Driver information
    driver_a_name = st.text_input("Driver A Name", "Unknown")
    driver_a_id = st.text_input("Driver A ID", "0000000000")
    driver_a_injuries = st.text_input("Driver A Injuries", "None")
    driver_b_name = st.text_input("Driver B Name", "Unknown")
    driver_b_id = st.text_input("Driver B ID", "0000000000")
    driver_b_injuries = st.text_input("Driver B Injuries", "None")

    # Driver A's license image
    driver_a_license_image = st.file_uploader("Upload Driver A's License Image", type=['jpg', 'png'])
    driver_a_license_url = None
    if driver_a_license_image:
        driver_a_license_url = upload_file_to_drive(driver_a_license_image, "driver_a_license.jpg")

    # Driver B's license image
    driver_b_license_image = st.file_uploader("Upload Driver B's License Image", type=['jpg', 'png'])
    driver_b_license_url = None
    if driver_b_license_image:
        driver_b_license_url = upload_file_to_drive(driver_b_license_image, "driver_b_license.jpg")

    # Accident images upload
    st.subheader("Accident Images")
    accident_images = st.file_uploader("Upload accident scene photos (max 20)", type=['jpg', 'png'], accept_multiple_files=True)
    accident_image_urls = []
    if accident_images:
        for i, image in enumerate(accident_images):
            image_url = upload_file_to_drive(image, f"accident_image_{i}.jpg")
            accident_image_urls.append(image_url)

    # Accident video upload
    st.subheader("Accident Video")
    accident_video = st.file_uploader("Upload accident video (max 5 min)", type=['mp4'])
    accident_video_url = None
    if accident_video:
        accident_video_url = upload_file_to_drive(accident_video, "accident_video.mp4")

    # Accident voice notes upload
    st.subheader("Voice Notes/Statements")
    voice_notes = st.file_uploader("Upload voice notes (max 5 min each)", type=['mp3'], accept_multiple_files=True)
    voice_note_urls = []
    if voice_notes:
        for i, note in enumerate(voice_notes):
            note_url = upload_file_to_drive(note, f"voice_note_{i}.mp3")
            voice_note_urls.append(note_url)

    # Convert date and time to string
    accident_date_str = accident_date.strftime("%Y-%m-%d")  # Convert to YYYY-MM-DD format
    accident_time_str = accident_time.strftime("%H:%M")  # Convert to HH:MM format

    if st.button("Save Report"):
        # Save to Google Sheets
        accident_report_sheet.append_row([
            case_number, accident_date_str, num_vehicles, road_name, accident_time_str,
            police_station, speed_limit, weather, road_condition,
            driver_a_name, driver_a_id, driver_a_injuries, driver_a_license_url,
            driver_b_name, driver_b_id, driver_b_injuries, driver_b_license_url,
            ', '.join(accident_image_urls), accident_video_url, ', '.join(voice_note_urls)
        ])
        st.success("Accident report saved!")


# Function to fetch all reports and display them in a table



def view_reports():
    st.title("View All Reports")

    # Fetch all report data from Google Sheets
    report_data = accident_report_sheet.get_all_records()
    df = pd.DataFrame(report_data)

    # Check column names
    st.write("Available Columns:", df.columns.tolist())

    # Convert all values in the relevant columns to strings to avoid the .str accessor issue
    df['case_number'] = df['case_number'].astype(str)
    df['driver_a_id'] = df['driver_a_id'].astype(str)
    df['driver_b_id'] = df['driver_b_id'].astype(str)

    # Search and filter bar
    search_term = st.text_input("Search by Case Number or Driver ID")

    if search_term:
        # Perform case-insensitive search by converting everything to strings
        df = df[(df['case_number'].str.contains(search_term, case=False, na=False)) |
                (df['driver_a_id'].str.contains(search_term, case=False, na=False)) |
                (df['driver_b_id'].str.contains(search_term, case=False, na=False))]

    # Display the filtered or all reports in a table
    st.write("All Reports", df)

    # Select a report to edit or generate PDF
    selected_report = st.selectbox("Select a report to edit or generate PDF", df['case_number'])

    if selected_report:
        # Fetch the selected report data
        report_to_edit = df[df['case_number'] == selected_report].iloc[0].to_dict()

        # Call the editing function to edit the report and pass the df as the second argument
        edit_report(report_to_edit, df)


def edit_report(report_data, df):
    st.subheader("Edit Report")

    # Form fields for editing the report
    case_number = st.text_input("Case Number", report_data['case_number'])
    accident_date = st.date_input("Accident Date", pd.to_datetime(report_data['accident_date']))
    num_vehicles = st.number_input("Number of Vehicles", min_value=1, max_value=10, value=int(report_data['num_vehicles']))
    road_name = st.text_input("Road Name", report_data['road_name'])
    accident_time = st.time_input("Accident Time", pd.to_datetime(report_data['accident_time']).time())
    police_station = st.text_input("Police Station", report_data['police_station'])
    speed_limit = st.number_input("Speed Limit", min_value=10, max_value=200, value=int(report_data['speed_limit']))
    weather = st.selectbox("Weather", ["Clear", "Rainy", "Foggy", "Snowy"], index=["Clear", "Rainy", "Foggy", "Snowy"].index(report_data['weather']))
    road_condition = st.selectbox("Road Condition", ["Good", "Wet", "Icy"], index=["Good", "Wet", "Icy"].index(report_data['road_condition']))

    driver_a_name = st.text_input("Driver A Name", report_data['driver_a_name'])
    driver_a_id = st.text_input("Driver A ID", report_data['driver_a_id'])
    driver_a_injuries = st.text_input("Driver A Injuries", report_data['driver_a_injuries'])

    driver_b_name = st.text_input("Driver B Name", report_data['driver_b_name'])
    driver_b_id = st.text_input("Driver B ID", report_data['driver_b_id'])
    driver_b_injuries = st.text_input("Driver B Injuries", report_data['driver_b_injuries'])

    # Save updated report
    if st.button("Save Changes"):
        # Convert the accident_date and time to strings
        accident_date_str = accident_date.strftime("%Y-%m-%d")
        accident_time_str = accident_time.strftime("%H:%M")

        # Find the row index to update
        matching_rows = df[df['case_number'] == case_number]
        if matching_rows.empty:
            st.error(f"No report found with Case Number: {case_number}")
        else:
            row_index = matching_rows.index[0] + 2  # Adjust for headers
            accident_report_sheet.update(f'A{row_index}', [[
                case_number,
                accident_date_str,
                num_vehicles,
                road_name,
                accident_time_str,
                police_station,
                speed_limit,
                weather,
                road_condition,
                driver_a_name,
                driver_a_id,
                driver_a_injuries,
                driver_b_name,
                driver_b_id,
                driver_b_injuries
            ]])

            st.success("Report updated successfully!")

    # Generate PDF of the report
    if st.button("Generate PDF"):
        # Ensure accident_date_str is initialized
        accident_date_str = accident_date.strftime("%Y-%m-%d")
        accident_time_str = accident_time.strftime("%H:%M")

        report_data = {
            'Accident Case Number': case_number,
            'Accident Date': accident_date_str,
            'Number of Vehicles': num_vehicles,
            'Accident Time': accident_time_str,
            'Road Name': road_name,
            'Police Station': police_station,
            'Speed Limit': speed_limit,
            'Weather': weather,
            'Road Condition': road_condition,
            'Driver A': {'Name': driver_a_name, 'ID': driver_a_id, 'Injuries': driver_a_injuries},
            'Driver B': {'Name': driver_b_name, 'ID': driver_b_id, 'Injuries': driver_b_injuries}
        }

        first_responder_info = {}  # Provide first responder information if available

        # Generate the PDF
        pdf_path = generate_and_download_pdf(first_responder_info, report_data)

        with open(pdf_path, "rb") as file:
            st.download_button("Download Report PDF", data=file, file_name=f"report_{case_number}.pdf")

def generate_and_download_pdf(first_responder_info, report_data):
    file_name = "accident_report.pdf"
    pdf_path = create_pdf(first_responder_info, report_data, file_name)
    return pdf_path

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

def collaboration_sharing():
    st.title('Collaboration and Sharing')

    st.write('Invite collaborators to your project')
    emails = st.text_area('Enter email addresses separated by commas')

    if st.button('Send Invitations'):
        st.success(f'Invitations sent to: {emails}')



# Main app with navigation
def main():
    st.sidebar.title("Navigation")

    # Updated navigation tab with icons
    option = st.sidebar.radio(
        "Select Page",
        ["📄 Accident Report", "📊 View Reports", "🆘 Emergency Assistance Dashboard", "📉 Accident Data Dashboard", "👥 Collaboration and Sharing"]
    )

    if option == "📄 Accident Report":
        accident_report_page()
    elif option == "📊 View Reports":
        view_reports()
    elif option == "🆘 Emergency Assistance Dashboard":
        emergency_assistance_dashboard()
    elif option == "📉 Accident Data Dashboard":
        accident_data_dashboard()
    elif option == "👥 Collaboration and Sharing":
        collaboration_sharing()

if __name__ == "__main__":
    main()
