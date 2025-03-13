import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid

def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Your Google Sheet Name")  # Replace with your sheet name
    return sheet.worksheet("AppActivationData")

def append_to_sheet(data):
    activation_data_sheet = get_google_sheet()
    activation_data_sheet.append_row(data)

def main():
    st.title("Activation Data Form")

    activation_id = str(uuid.uuid4())
    start_date = st.date_input("Start Date", datetime.today())
    start_time = st.time_input("Start Time", datetime.now().time())
    venue = st.text_input("Venue")
    activation_name = st.text_input("Activation Name")
    activation_brand = st.text_input("Activation Brand")
    region = st.text_input("Region")
    competitor_brand = st.selectbox("Competitor Brand", [
        'B&H RED', 'B&H BLUE', 'B&H BLUE SWITCH', 'DUNHILL COURTLEIGH BLEND', 
        'PETER STUYVESANT BLUE', 'PETER STUYVESANT SILVER', 'DUNHILL ECLIPSE DOUBLE PULSE 20\'s', 
        'DUNHILL ECLIPSE DOUBLE PULSE 10\'s', 'DUNHILL ECLIPSE BLUE SWITCH', 'PETER STUYVESANT FILTER', 
        'PALL MALL XL PULSE', 'PALL MALL XL BOOST', 'PALL MALL RED', 'PALL MALL BLUE', 'KENT SILVER', 
        'MARLBORO BEYOND VISTA', 'DUNHILL COURTLEIGH BLEND 10\'s', 'MARLBORO BEYOND BLUE', 
        'ROTHMANS FILTER BLUE', 'ROTHMANS SPECIAL RED', 'CHESTERFIELD COOL TASTE', 
        'CHESTERFIELD TUNED BLUE', 'CHESTERFIELD TUNED AQUA'
    ])
    jti_products = st.text_input("JTI Products")
    made_sale = st.radio("Did you make a sale?", ["Yes", "No"], key="made_sale")
    num_boxes_sold = st.number_input("Number of Boxes Sold", min_value=0, step=1) if made_sale == "Yes" else ""
    agency_name = st.text_input("Capture Agency Name")
    
    if st.button("Submit"):
        form_data = [
            activation_id, start_date.strftime("%Y-%m-%d"), start_time.strftime("%H:%M:%S"), venue, activation_name, 
            activation_brand, region, competitor_brand, jti_products, made_sale, num_boxes_sold, agency_name
        ]
        append_to_sheet(form_data)
        st.success("Data submitted successfully!")

if __name__ == "__main__":
    main()



