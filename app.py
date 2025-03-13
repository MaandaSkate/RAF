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
import pandas as pd
import uuid
import datetime
import gspread
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from streamlit_option_menu import option_menu

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

# Access specific sheet (App Activation Data)
activation_data_sheet = sheet.worksheet("AppActivationData")  # Adjust the sheet name as per your setup

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
        activation_id = st.text_input("ID", value=str(uuid.uuid4()), disabled=True)
        start_date = st.date_input("Start Date", value=datetime.datetime.now().date())
        start_time = st.time_input("Start Time", value=datetime.datetime.now().time())
    with col2:
        venue = st.text_input("Venue", value="Mieliepop Festival")
        activation_name = st.text_input("Activation Name", value="Mieliepop Festival")
        activation_brand = st.selectbox("Activation Brand", ["Sense Family", "Winston Family", "Camel Family"])
    
    st.markdown("### 🔥 Engagement Details")
    col3, col4 = st.columns(2)
    
    with col3:
        region = st.selectbox("Region", ["Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo", "Mpumalanga", "North West", "Northern Cape", "Western Cape"])
        smoked_camel_winston = st.radio("Have you smoked Camel/Winston ever?", ["Yes", "No"], key="smoked_camel_winston")
        if smoked_camel_winston == "Yes":
            recommend_score = st.slider("How likely are you to recommend us?", 0, 10)
    with col4:
        competitor_brand = st.selectbox("Competitor Brand", [
            "B&H RED", "B&H BLUE", "B&H BLUE SWITCH", "DUNHILL COURTLEIGH BLEND", "PETER STUYVESANT BLUE", "PETER STUYVESANT SILVER",
            "DUNHILL ECLIPSE DOUBLE PULSE 20's", "DUNHILL ECLIPSE DOUBLE PULSE 10's", "DUNHILL ECLIPSE BLUE SWITCH", "PETER STUYVESANT FILTER",
            "PALL MALL XL PULSE", "PALL MALL XL BOOST", "PALL MALL RED", "PALL MALL BLUE", "KENT SILVER", "MARLBORO BEYOND VISTA",
            "DUNHILL COURTLEIGH BLEND 10's", "MARLBORO BEYOND BLUE", "ROTHMANS FILTER BLUE", "ROTHMANS SPECIAL RED", "CHESTERFIELD COOL TASTE",
            "CHESTERFIELD TUNED BLUE", "CHESTERFIELD TUNED AQUA"
        ])
        jti_products = st.selectbox("JTI Products", [
            "CAMEL SENSO RED", "CAMEL SENSO BLUE", "CAMEL SENSO PLATINUM", "CAMEL ACTIVATE DOUBLE MINT & BERRY 20'S", "CAMEL ACTIVATE DOUBLE MINT & BERRY 10'S",
            "CAMEL ACTIVATE MINT", "WINSTON ORIGINAL RED", "WINSTON ORIGINAL BLUE", "WINSTON EXPAND PURPLE MIX", "WINSTON EXPAND ARCTIC COOL", "WINSTON JUST RED", "WINSTON JUST BLUE"
        ])
    
    did_sale = st.radio("Did you make a sale?", ["Yes", "No"], key="did_sale")
    
    if did_sale == "Yes":
        num_sales = st.number_input("Number of boxes sold", min_value=0)
    else:
        num_sales = None  # Keep the field hidden if "No" is selected
    
    capture_agency = st.selectbox("Capture Agency Name", ["Leestan Trading", "Purplerocket", "JR Promotions"])
    
    submitted = st.form_submit_button("Submit Activation Data")
    
    # Validation and Feedback
    if submitted:
        if not venue or not activation_name or not activation_brand:
            st.error("Please fill in all required fields: Venue, Activation Name, Activation Brand.")
        else:
            # Collect form data into a list
            form_data = [
                activation_id,
                start_date,
                start_time,
                venue,
                activation_name,
                activation_brand,
                region,
                smoked_camel_winston,
                recommend_score if smoked_camel_winston == "Yes" else None,
                competitor_brand,
                jti_products,
                did_sale,
                num_sales,
                capture_agency
            ]
            # Append data to Google Sheet
            append_to_sheet(form_data)
            st.success("Activation Data Submitted Successfully! 🚀")

