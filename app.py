import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import uuid

# --- GOOGLE SHEETS AUTH FIX ---
# Try loading credentials from environment variable (for Streamlit Cloud)
if "GOOGLE_SHEETS_CREDENTIALS" in os.environ:
    creds_dict = json.loads(os.environ["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
else:
    # Local authentication - Ensure the JSON file exists
    json_path = "your_credentials.json"  # Replace with the actual path if needed
    if not os.path.exists(json_path):
        st.error("Authentication failed: Credentials file not found.")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])

# Connect to Google Sheets
client = gspread.authorize(creds)
try:
    sheet = client.open("Your_Google_Sheet_Name")  # Make sure this is correct
    activation_data_sheet = sheet.worksheet("AppActivationData")  # Adjust to match your sheet name
except gspread.exceptions.SpreadsheetNotFound:
    st.error("Google Sheet not found. Check the sheet name.")
    st.stop()
except gspread.exceptions.WorksheetNotFound:
    st.error("Worksheet 'AppActivationData' not found. Ensure it exists.")
    st.stop()

# --- UI DESIGN ---  
st.set_page_config(layout="centered", page_title="JTI Activation Form", page_icon="📋")

# Add JTI Logo at the top-right corner
st.markdown(
    """
    <style>
        .logo-container {
            position: absolute;
            top: 10px;
            right: 10px;
        }
        img {
            width: 120px;
        }
        @media (max-width: 768px) {
            img {
                width: 80px;
            }
        }
    </style>
    <div class="logo-container">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Japan_Tobacco_International_logo.svg/2560px-Japan_Tobacco_International_logo.svg.png">
    </div>
    """,
    unsafe_allow_html=True
)

st.title("JTI Activation Data Entry")

# --- FORM INPUTS ---
with st.form("activation_form"):
    activation_id = str(uuid.uuid4())
    start_date = st.date_input("Start Date")
    start_time = st.time_input("Start Time")
    venue = st.text_input("Venue")
    activation_name = st.text_input("Activation Name")
    activation_brand = st.text_input("Activation Brand")
    region = st.text_input("Region")
    
    competitor_brand = st.selectbox(
        "Competitor Brand",
        ['B&H RED', 'B&H BLUE', 'B&H BLUE SWITCH', 'DUNHILL COURTLEIGH BLEND',
         'PETER STUYVESANT BLUE', 'PETER STUYVESANT SILVER', 'DUNHILL ECLIPSE DOUBLE PULSE 20\'s',
         'DUNHILL ECLIPSE DOUBLE PULSE 10\'s', 'DUNHILL ECLIPSE BLUE SWITCH', 'PETER STUYVESANT FILTER',
         'PALL MALL XL PULSE', 'PALL MALL XL BOOST', 'PALL MALL RED', 'PALL MALL BLUE', 'KENT SILVER',
         'MARLBORO BEYOND VISTA', 'DUNHILL COURTLEIGH BLEND 10\'s', 'MARLBORO BEYOND BLUE',
         'ROTHMANS FILTER BLUE', 'ROTHMANS SPECIAL RED', 'CHESTERFIELD COOL TASTE',
         'CHESTERFIELD TUNED BLUE', 'CHESTERFIELD TUNED AQUA']
    )

    jti_products = st.text_input("JTI Products")

    sale_made = st.radio("Did you make a sale?", ["Yes", "No"], key="sale_made")

    num_boxes_sold = None
    if sale_made == "Yes":
        num_boxes_sold = st.number_input("Number of Boxes Sold", min_value=0, step=1)

    agency_name = st.text_input("Capture Agency Name")

    submit_button = st.form_submit_button("Submit")

# --- FORM SUBMISSION ---
if submit_button:
    form_data = [
        activation_id, str(start_date), str(start_time), venue, activation_name,
        activation_brand, region, competitor_brand, jti_products, sale_made,
        num_boxes_sold if sale_made == "Yes" else "", agency_name
    ]

    activation_data_sheet.append_row(form_data, value_input_option="USER_ENTERED")

    st.success("Data successfully submitted!")





