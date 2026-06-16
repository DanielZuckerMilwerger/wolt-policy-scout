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
    st.warning("שימו לב: מפתח Gemini API לא מוגדר עדיין ב-Secrets של השרת. המערכת תציג נתונים אך לא תבצע ניתוח AI.")
    model = None

# ==========================================
# 2. עיצוב ומיתוג (Wolt Blue & Styling)
# ==========================================
st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; color: #202125; }
    h1, h2, h3, h4 { color: #00c2e8 !important; font-family: 'Segoe UI', sans-serif; }
    .wolt-card {
        border-right: 5px solid #00c2e8;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 4px;
        margin-bottom: 15px;
        text-align: right;
    }
    .stTextInput, .stFileUploader { direction: rtl; text-align: right; }
    </style>
""", unsafe_allow_index=True)

# כותרת האתר ולוגו
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Wolt_logo.svg/512px-Wolt_logo.svg.png", width=120)
st.title("Wolt Israel - Public Policy Scout")
st.subheader("מערכת ארגונית לניטור סיכונים והזדמנויות רגולטוריות")

# ==========================================
# 3. מנגנון בקרת כניסה (הגנת סיסמה)
# ==========================================
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.markdown("### 🔒 כניסה מאובטחת לעובדי וולט")
        password = st.text_input("אנא הכנס סיסמת גישה:", type="password")
        if password == "WoltPolicy2026":  # סיסמת הכניסה שלך
            st.session_state["authenticated"] = True
            st.rerun()
        elif password:
            st.error("⚠️ סיסמה שגויה. הגישה חסומה.")
        return False
    return True

# אם המשתמש עבר את חסימת הסיסמה
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
    
    PRIORITY_COMMITTEES = ["ועדת הכלכלה", "ועדת הכספים", "ועדת העבודה והרווחה"]

    # ==========================================
    # 5. מוח ה-AI (Gemini)
    # ==========================================
    def analyze_with_gemini(source, category, title, text_content=""):
        if not model:
            return "ניתוח ה-AI אינו זמין מכיוון שמפתח ה-API לא הוגדר."
            
        prompt = f"""
        אתה מנהל מדיניות ציבורית בכיר ויועץ רגולטורי של חברת וולט (Wolt) ישראל.
        להלן פרסום/ידיעה חדשה מהרשת או מהממשלה:
        מקור: {source} ({category})
        כותרת/נושא: {title}
        תוכן נוסף (אם יש): {text_content[:500]}
        
        נתח את הפרסום בקצרצר (עד 3 שורות). קבע האם יש כאן סיכון או הזדמנות למודל של וולט (תעסוקת שליחים כעצמאיים, רגולציה תחבורתית, חובות רישוי, משלוחי מזון/פארם).
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
    
    # א. כנסת ישראל (API)
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

    # ב. מאגר החקיקה ותזכירי החוק (API)
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
                            "קישור": f"https://www.tazkirim.gov.il/"
                        })
                return tazkirim
            return []
        except:
            return []

    # ג. רדאר חדשות (10 אתרים מבוססי RSS) - נכתב משמאל לימין למניעת שגיאות RTL
    def fetch_news_data():
        feeds_config = [
            {"name": "עיתון דבר", "url": "https://www.davar1.co.il/feed/"},
            {"name": "כלכליסט", "url": "https://www.calcalist.co.il/GeneralRSS/0,16154,L-8,00.xml"},
            {"name": "גלובס", "url": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederFeed?c=2"},
            {"name": "דה מרקר", "url": "https://www.themarker.com/srv/rss/all"},
            {"name": "Ynet - כלכלה", "url": "https://www.ynet.co.il/Integration/StoryRss538.xml"},
            {"name": "מעריב - מבזקים", "url": "https://www.maariv.co.il/Rss/RssFeedsMivzakim"},
            {"name": "מקור ראשון", "url": "https://www.makorrishon.
