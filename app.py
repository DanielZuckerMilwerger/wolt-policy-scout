import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import google.generativeai as genai
import feedparser

# ==========================================
# 1. אבטחה ומפתחות API (Streamlit Secrets)
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
else:
    st.warning("Warning: Gemini API Key is missing in Secrets.")
    model = None

# ==========================================
# 2. עיצוב ומיתוג סופר-וולטי (Custom CSS)
# ==========================================
st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide", page_icon="🛵")

st.markdown("""
    <style>
    /* עיצוב כללי ויישור לעברית */
    .stApp { direction: rtl; text-align: right; background-color: #ffffff; color: #202125; }
    
    /* כותרות בצבע תכלת וולט רשמי */
    h1, h2, h3 { color: #00c2e8 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800; text-align: right; }
    
    /* עיצוב כרטיסיות המידע של וולט */
    .wolt-card {
        background-color: #f3fafd;
        border-right: 6px solid #00c2e8;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: right;
    }
    .wolt-card h4 { color: #00c2e8 !important; margin-top: 0; font-size: 18px; text-align: right; }
    .wolt-card p { font-size: 15px; color: #202125; line-height: 1.6; text-align: right; }
    
    /* כפתורים ולינקים */
    a { color: #00c2e8 !important; text-decoration: none; font-weight: bold; }
    a:hover { text-decoration: underline; }
    
    /* יישור שדות קלט */
    .stTextInput, .stFileUploader { direction: rtl; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# שימוש בלינק ישיר יציב וחופשי שלא נחסם וללא בעיות RTL של קוד וקטורי
st.markdown("""
    <div style="direction: rtl; text-align: right; width: 100%;">
        <img src="https://unpkg.com/@simple-icons/simple-icons@v11/icons/wolt.svg" style="width: 140px; filter: invert(53%) sepia(93%) saturate(1904%) hue-rotate(159deg) brightness(97%) contrast(105%); margin-bottom: 10px;">
    </div>
""", unsafe_allow_html=True)

# מבנה כותרות מיושר פיקס לימין
st.markdown("""
    <div style="direction: rtl; text-align: right; width: 100%; margin-top: 5px;">
        <h1 style="margin: 0; padding: 0; color: #00c2e8; font-size: 42px;">Public Policy Scout</h1>
        <p style="margin: 5px 0 0 0; color: #808080; font-size: 18px; font-weight: 500;">מערכת ארגונית חכמה לניטור סיכונים והזדמיויות רגולטוריות בישראל</p>
    </div>
    <hr style="border: 0; height: 2px; background: #00c2e8; margin-bottom: 30px; margin-top: 20px;">
""", unsafe_allow_html=True)

# ==========================================
# 3. מנגנון בקרת כניסה (הגנת סיסמה)
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.write("### 🔒 כניסה מאובטחת לעובדי וולט")
        password = st.text_input("אנא הכנס סיסמת גישה:", type="password")
        if password == "WoltPolicy2026":
            st.session_state["authenticated"] = True
            st.rerun()
        elif password:
            st.error("⚠️ סיסמה שגויה. הגישה חסומה.")
        return False
    return True

if check_password():

    # ==========================================
    # 4. הגדרות ופילטרים (מילות מפתח)
    # ==========================================
    KEYWORDS = [
        "שליחים", "עצמאיים", "שליחים עצמאיים", "פלטפורמות דיגיטליות", 
        "דו גלגלי", "כלי רכב קלים", "חלטורה", "גיג אקונומי", "מזון", "משלוחים", "פארם", "תרופות"
    ]
    
    KEYWORDS_EN = [
        "couriers", "riders", "delivery", "wolt", "gig economy", 
        "freelancers", "self-employed", "independent contractors", "food delivery", "pharmacy delivery"
    ]
    
    NEGATIVE_KEYWORDS = ["כלבת", "נשכו", "תנים", "כלב", "חתול", "אושפז", "ננשך"]
    
    PRIORITY_COMMITTEES = ["ועדת הכלכלה", "ועדת הכספים", "ועדת העבודה והרווחה"]

    # ==========================================
    # 5. מוח ה-AI (Gemini)
    # ==========================================
    def analyze_with_gemini(source, category, title, text_content=""):
        if not model:
            return "ניתוח ה-AI אינו זמין מכיוון שמפתח ה-API לא הוגדר ב-Secrets."
            
        prompt = f"""
        אתה מנהל מדיניות ציבורית בכיר ויועץ רגולטורי של חברת וולט (Wolt) ישראל.
        להלן פרסום/ידיעה חדשה מהרשת או מהממשלה:
        מקור: {source} ({category})
        כותרת/נושא: {title}
        תוכן נוסף (אם יש): {text_content[:500]}
        
        נתח את הפרסום בקצרצר (עד 3 שורות). קבע האם יש כאן סיכון או הזדמנות למודל של וולט.
        תשובתך חייבת להיות בעברית, מקצועית וממוקדת למנהלים בחברה.
        """
        try:
            response = model.generate_content(prompt)
            return response.text
        except:
            return "לא ניתן לייצר ניתוח AI כרגע."

    # ==========================================
    # 6. צינורות מקורות המידע (Data Pipelines)
    # ==========================================
    
    def fetch_knesset_data():
        url = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Agenda"
        params = {
            '$filter': "StartDate ge datetime'" + datetime.now().strftime('%Y-%m-%dT00:00:00') + "'",
            '$orderby': "StartDate asc",
            '$format': "json"
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                events = []
                for item in response.json().get('value', []):
                    title = item.get('CommitteeSessionName', '') or item.get('Subject', '') or ''
                    committee = item.get('CommitteeName', 'ועדה כללית')
                    
                    if any(word in title for word in KEYWORDS):
                        events.append({
                            "מקור": "🏛️ כנסת ישראל",
                            "קטגוריה": committee,
                            "כותרת": title,
                            "תאריך": datetime.strptime(item['StartDate'], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M'),
                            "עדיפות": "🔥 גבוהה" if committee in PRIORITY_COMMITTEES else "🔵 רגילה",
                            "קישור": "https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgendas.aspx"
                        })
                return events
            return []
        except:
            return []

    def fetch_tazkirim_data():
        resource_id = "9207e37d-b6bd-4df5-91db-fc539dfbbf76"
        url = "https://data.gov.il/api/3/action/datastore_search"
        params = {'resource_id': resource_id, 'limit': 40, 'sort': 'PublishDate desc'}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                records = response.json().get('result', {}).get('records', [])
                tazkirim = []
                for item in records:
                    title = item.get('TazkirName', '') or item.get('Subject', '') or ''
                    ministry = item.get('PublishingMinistry', 'משרד ממשלתי')
                    publish_date = item.get('PublishDate', '')
                    
                    if any(word in title for word in KEYWORDS):
                        tazkirim.append({
                            "מקור": "📜 מאגר החקיקה (תזכירים)",
                            "קטגוריה": ministry,
                            "כותרת": title,
                            "תאריך": publish_date[:10] if publish_date else "לא צוין",
                            "עדיפות": "🔥 גבוהה",
                            "קישור": "https://www.tazkirim.gov.il/"
                        })
                return tazkirim
            return []
        except:
            return []

    def fetch_news_data():
        config_list = [
            ("Davar", "https://www.davar1.co.il/feed/"),
            ("Calcalist", "https://www.calcalist.co.il/GeneralRSS/0,16154,L-8,00.xml"),
            ("Globes", "
