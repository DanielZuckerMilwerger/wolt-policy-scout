import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import feedparser

# ==========================================
# 1. הגדרות גלובליות יציבות
# ==========================================
KEYWORDS = [
    "שליחים", "עצמאיים", "שליחים עצמאיים", "פלטפורמות דיגיטליות", 
    "דו גלגלי", "כלי רכב קלים", "חלטורה", "גיג אקונומי", "מזון", "משלוחים", "פארם", "תרופות",
    "עסקים קטנים", "עסקים בינוניים", "עובדים זרים", "מבקשי מקלט", "הקצאת", "תחרות"
]

KEYWORDS_EN = [
    "couriers", "riders", "delivery", "wolt", "gig economy", 
    "freelancers", "self-employed", "independent contractors", "food delivery", "pharmacy delivery",
    "small business", "medium business", "foreign workers", "asylum seekers"
]

NEGATIVE_KEYWORDS = ["כלבת", "נשכו", "תנים", "כלב", "חתול", "אושפז", "ננשך"]

PRIORITY_COMMITTEES = [
    "ועדת הכלכלה", "ועדת הכספים", "ועדת העבודה והרווחה", 
    "ועדת המדע והטכנולוגיה", "הוועדה המיוחדת לעובדים זרים", "עובדים זרים"
]

NEWS_FEEDS = [
    ("Davar", "https://www.davar1.co.il/feed/"),
    ("Calcalist", "https://www.calcalist.co.il/GeneralRSS/0,16154,L-8,00.xml"),
    ("Globes", "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederFeed?c=2"),
    ("TheMarker", "https://www.themarker.com/srv/rss/all"),
    ("Ynet", "https://www.ynet.co.il/Integration/StoryRss538.xml"),
    ("Maariv", "https://www.maariv.co.il/Rss/RssFeedsMivzakim"),
    ("MakorRishon", "https://www.makorrishon.co.il/category/news/feed/"),
    ("Kipa", "https://www.kipa.co.il/rss/news.xml"),
    ("TimesOfIsrael", "https://www.timesofisrael.com/il/feed/"),
    ("JPost", "https://www.jpost.com/rss/israelnews")
]

# ==========================================
# 2. אבטחה ומפתחות API (Streamlit Secrets)
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

# ==========================================
# 3. עיצוב ומיתוג בסיסי ויציב
# ==========================================
st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide", page_icon="🛵")

st.title("Wolt Israel 🛵")
st.subheader("Public Policy Scout | מערכת ארגונית לניטור סיכונים")
st.markdown("---")

# ==========================================
# 4. מנגנון בקרת כניסה (הגנת סיסמה)
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.write("### 🔒 כניסה מאובטחת לעובדי וולט")
        password = st.text_input("אנא הכנס סיסמת גישה:", type="password")
        
        # פיצול השורה בצורה בטוחה למניעת שבירת מחרוזת
        CORRECT_PASS = "WoltPolicy2026"
        if password == CORRECT_PASS:
            st.session_state["authenticated"] = True
            st.rerun()
        elif password:
            st.error("⚠️ סיסמה שגויה. הגישה חסומה.")
        return False
    return True

# ==========================================
# 5. פונקציות איסוף וניתוח נתונים
# ==========================================
def analyze_with_gemini(source, category, title):
    if not model:
        return "ניתוח ה-AI אינו זמין מכיוון שמפתח ה-API לא הוגדר ב-Secrets."
        
    prompt = f"""
    אתה מנהל מדיניות ציבורית בכיר בוולט (Wolt) ישראל.
    נתח את הפרסום הבא בקצרצר (עד 3 שורות). קבע האם יש כאן סיכון או הזדמנות למודל של וולט.
    מקור: {source} ({category})
    נושא: {title}
    תשובתך חייבת להיות בעברית מקצועית וממוקדת.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "לא ניתן לייצר ניתוח AI כרגע."

def fetch_knesset_data():
    events = []
    try:
        start_dt = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT00:00:00')
        url = "https://knesset.gov.il/Odata/ParliamentInfo.svc/KNS_Agenda"
        
        params = {
            '$filter': f"StartDate ge datetime'{start_dt}'",
            '$orderby': "StartDate asc",
            '$top': '500', 
            '$format': "json"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            for item in response.json().get('value', []):
                session_name = item.get('CommitteeSessionName', '') or ''
                subject = item.get('Subject', '') or ''
                committee = item.get('CommitteeName', '') or 'ועדה כללית'
                
                full_knesset_text = f"{session_name} {subject} {committee}"
                
                match_keyword = any(word in full_k
