import streamlit as st
import gspread
from google.oauth2 import service_account
import uuid
import datetime
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe

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

# Open the Google Sheet
sheet = client.open_by_url(SHEET_URL)

# Access specific sheet (App Activation Data)
activation_data_sheet = sheet.worksheet("AppActivationData")

# Function to append data to Google Sheets
def append_to_sheet(data):
    activation_data_sheet.append_row(data)

# Streamlit UI setup
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stButton>button {border-radius: 12px; background-color: #4CAF50; color: white; font-size: 16px; padding: 10px 24px;}
        .stTextInput>div>div>input {border-radius: 10px; border: 1px solid #ccc; padding: 10px;}
    </style>
""", unsafe_allow_html=True)

# App Activation Data Form
st.markdown("## 📲 App Activation Data Form")

with st.form("app_activation_form"):
    col1, col2 = st.columns(2)
    
    # Inputs
    with col1:
        activation_id = str(uuid.uuid4())  # Convert UUID to string
        start_date = datetime.datetime.now().date()  # datetime.date
        start_time = datetime.datetime.now().time()  # datetime.time
    with col2:
        venue = st.text_input("Venue", value="Mieliepop Festival")
        activation_name = st.text_input("Activation Name", value="Mieliepop Festival")
        activation_brand = st.selectbox("Activation Brand", ["Sense Family", "Winston Family", "Camel Family"])
    
    st.markdown("### 🔥 Engagement Details")
    col3, col4 = st.columns(2)
    
    with col3:
        region = st.selectbox("Region", [
            "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
            "Mpumalanga", "North West", "Northern Cape", "Western Cape"
        ])
    with col4:
        competitor_brand = st.selectbox("Competitor Brand", [





