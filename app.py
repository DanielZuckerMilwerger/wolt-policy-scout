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
        return "API key missing in Streamlit secrets."
    
    # שימוש בפורמט אנגלי נקי לחלוטין למניעת שבירת שורות
    p1 = "You are a public policy manager at Wolt Israel. Analyze this in Hebrew (up to 3 lines) for risks or opportunities: "
    p2 = f"Source: {source}, Category: {category}, Title: {title}"
    prompt = f"{p1} {p2}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return "AI analysis unavailable at the moment."

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
                
                txt = f"{session_name} {subject} {committee}"
                match_kw = any(w in txt for w in KEYWORDS)
                match_comm = any(c in committee for c in PRIORITY_COMMITTEES)
                
                if match_kw or match_comm:
                    title_to_show = session_name if session_name else subject
                    if not title_to_show:
                        title_to_show = f"ישיבה של {committee}"
                    
                    date_parsed = datetime.strptime(item['StartDate'], '%Y-%m-%dT%H:%M:%S')
                    date_str = date_parsed.strftime('%d/%m/%Y %H:%M')
                    link_kn = "https://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgendas.aspx"
                    
                    events.append({
                        "מקור": "🏛️ כנסת ישראל",
                        "קטגוריה": committee,
                        "כותרת": title_to_show,
                        "תאריך": date_str,
                        "עדיפות": "🔥 גבוהה" if match_comm else "🔵 רגילה",
                        "קישור": link_kn
                    })
    except:
        pass
    return events

def fetch_tazkirim_data():
    tazkirim = []
    try:
        resource_id = "9207e37d-b6bd-4df5-91db-fc539dfbbf76"
        url = "https://data.gov.il/api/3/action/datastore_search"
        params = {'resource_id': resource_id, 'limit': 40, 'sort': 'PublishDate desc'}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            records = response.json().get('result', {}).get('records', [])
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
    except:
        pass
    return tazkirim

def process_entry(name, entry):
    title = entry.get('title', '')
    summary = entry.get('summary', '') or entry.get('description', '') or ''
    link = entry.get('link', '')
    pub_date_str = entry.get('published', '') or entry.get('updated', '')
    
    full_text = f"{title} {summary}".lower()
    match_he = any(word in full_text for word in KEYWORDS)
    match_en = any(word in full_text for word in KEYWORDS_EN)
    negative = any(word in full_text for word in NEGATIVE_KEYWORDS)
    
    if (match_he or match_en) and not negative:
        return {
            "מקור": name,
            "קטגוריה": "מדיה ואקטואליה",
            "כותרת": title,
            "תאריך": pub_date_str[:16],
            "עדיפות": "🔵 מעקב מדיה",
            "קישור": link
        }
    return None

def fetch_news_data():
    news_alerts = []
    try:
        for name, url in NEWS_FEEDS:
            feed = feedparser.parse(url)
            for entry in feed.entries[:12]:
                processed = process_entry(name, entry)
                if processed:
                    if not any(alert['קישור'] == processed['קישור'] for alert in news_alerts):
                        news_alerts.append(processed)
    except:
        pass
    return news_alerts

# ==========================================
# 6. הצגת הממשק למשתמש מחובר
# ==========================================
if check_password():
    tab1, tab2, tab3 = st.tabs(["🏛️ חקיקה וּועדות", "📂 סורק מסמכים (PDF)", "📰 רדאר חדשות"])

    with tab1:
        st.write("### 🏛️ עדכוני כנסת ישראל ומאגר החקיקה הלאומי")
        with st.spinner("סורק מאגרים ממשלתיים..."):
            gov_alerts = []
            gov_alerts.extend(fetch_knesset_data())
            gov_alerts.extend(fetch_tazkirim_data())
            
        if not gov_alerts:
            st.info("לא נמצאו דיונים או תזכירי חוק קרובים התואמים את מילות המפתח של וולט.")
        else:
            for alert in gov_alerts:
                with st.container(border=True):
                    st.write(f"### {alert['מקור']} | {alert['קטגוריה']}")
                    st.info(f"**נושא הדיון:** {alert['כותרת']}")
                    st.write(f"📅 תאריך: {alert['תאריך']} | 📊 עדיפות: {alert['עדיפות']}")
                    st.markdown(f"[🔗 למעבר למקור הדיון לחץ כאן]({alert['קישור']})")
                    
                    with st.expander("🔍 ניתוח מדיניות - Gemini AI"):
                        analysis = analyze_with_gemini(alert['מקור'], alert['קטגוריה'], alert['כותרת'])
                        st.write(analysis)

    with tab2:
        st.write("### 📂 סורק החלטות ממשלה וועדות שרים (PDF)")
        st.write("מזכירות הממשלה מפרסמת קובצי PDF. העלה אותם כאן לסריקה וניתוח מיידי:")
        uploaded_file = st.file_uploader("גרור או בחר קובץ PDF של הממשלה", type=["pdf"])
        
        if uploaded_file is not None:
            with st.spinner("ה-AI קורא ומנתח את המסמך..."):
                file_bytes = uploaded_file.read()
                prompt = "You are a policy manager at Wolt Israel. Summarize in Hebrew any risks or opportunities in this PDF."
                try:
                    response = model.generate_content([{"mime_type": "application/pdf", "data": file_bytes}, prompt])
                    st.success(response.text)
                except Exception as e:
                    st.error(f"Error analyzing document: {e}")

    with tab3:
        st.write("### 📰 רדאר מדיניות בתקשורת הישראלית")
        with st.spinner("סורק את אתרי החדשות..."):
            news_alerts = fetch_news_data()
            
        if not news_alerts:
            st.info("אין כתבות אקטואליות חדשות בנושאי הליבה של וולט בשעות האחרונות.")
        else:
            for alert in news_alerts:
                with st.container(border=True):
                    st.write(f"### 📰 {alert['מקור']}")
                    st.warning(f"**כתבה:** {alert['כותרת']}")
                    st.write(f"📅 פורסם בתאריך: {alert['תאריך']}")
                    st.markdown(f"[🔗 לקריאת הכתבה המלאה לחץ כאן]({alert['קישור']})")
                    
                    with st.expander("🔍 ניתוח ספין תקשורתי - Gemini AI"):
                        analysis = analyze_with_gemini(alert['מקור'], "חדשות ומדיה", alert['כותרת'])
                        st.write(analysis)
