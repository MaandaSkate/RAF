import streamlit as st
import gspread
from google.oauth2 import service_account
import uuid
import datetime

# Authenticate using secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)

# Authorize Google Sheets
client = gspread.authorize(credentials)

# Open the Google Sheet
SHEET_URL = st.secrets["sheets"]["SHEET_URL"]
sheet = client.open_by_url(SHEET_URL)

# Access specific sheet (App Activation Data)
activation_data_sheet = sheet.worksheet("AppActivationData")

# Function to append data to Google Sheets
def append_to_sheet(data):
    activation_data_sheet.append_row(data)

# Custom styling for UI
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stButton>button {
            border-radius: 12px; background-color: #4CAF50; color: white; 
            font-size: 16px; padding: 10px 24px;
        }
        .stTextInput>div>div>input {
            border-radius: 10px; border: 1px solid #ccc; padding: 10px;
        }
        .stSelectbox>div {
            border-radius: 10px; padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# App Activation Data Form
st.markdown("## 📲 App Activation Data Form")

with st.form("app_activation_form"):
    col1, col2 = st.columns(2)
    
    # Inputs
    with col1:
        activation_id = str(uuid.uuid4())
        start_date = datetime.datetime.now().date()
        start_time = datetime.datetime.now().time()

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
        competitor_brand_options = [
            "B&H RED", "B&H BLUE", "B&H BLUE SWITCH", "DUNHILL COURTLEIGH BLEND",
            "PETER STUYVESANT BLUE", "PETER STUYVESANT SILVER", "DUNHILL ECLIPSE DOUBLE PULSE 20's",
            "DUNHILL ECLIPSE DOUBLE PULSE 10's", "DUNHILL ECLIPSE BLUE SWITCH", "PETER STUYVESANT FILTER",
            "PALL MALL XL PULSE", "PALL MALL XL BOOST", "PALL MALL RED", "PALL MALL BLUE",
            "KENT SILVER", "MARLBORO BEYOND VISTA", "DUNHILL COURTLEIGH BLEND 10's",
            "MARLBORO BEYOND BLUE", "ROTHMANS FILTER BLUE", "ROTHMANS SPECIAL RED",
            "CHESTERFIELD COOL TASTE", "CHESTERFIELD TUNED BLUE", "CHESTERFIELD TUNED AQUA"
        ]
        competitor_brand = st.selectbox("Competitor Brand", competitor_brand_options)

    jti_products = st.selectbox("JTI Products", [
        "CAMEL SENSO RED", "CAMEL SENSO BLUE", "CAMEL SENSO PLATINUM",
        "CAMEL ACTIVATE DOUBLE MINT & BERRY 20'S", "CAMEL ACTIVATE DOUBLE MINT & BERRY 10'S",
        "CAMEL ACTIVATE MINT", "WINSTON ORIGINAL RED", "WINSTON ORIGINAL BLUE",
        "WINSTON EXPAND PURPLE MIX", "WINSTON EXPAND ARCTIC COOL",
        "WINSTON JUST RED", "WINSTON JUST BLUE"
    ])

    did_sale = st.radio("Did you make a sale?", ["Yes", "No"], key="did_sale")
    num_sales = st.number_input("Number of boxes sold", min_value=0) if did_sale == "Yes" else 0

    capture_agency = st.selectbox("Capture Agency Name", ["Leestan Trading", "Purplerocket", "JR Promotions"])

    submitted = st.form_submit_button("Submit Activation Data")

    if submitted:
        if not venue or not activation_name or not activation_brand:
            st.error("Please fill in all required fields: Venue, Activation Name, Activation Brand.")
        else:
            form_data = [
                str(activation_id), start_date.strftime("%Y-%m-%d"), start_time.strftime("%H:%M:%S"),
                venue, activation_name, activation_brand, region, competitor_brand,
                jti_products, did_sale, num_sales, capture_agency
            ]

            append_to_sheet(form_data)
            st.success("Activation Data Submitted Successfully! 🚀")








