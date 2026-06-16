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
# 2. כותרת ומיתוג (Wolt Israel)
# ==========================================
st.set_page_config(page_title="Wolt Israel - Policy Scout", layout="wide")

# לוגו וכותרת כחולה בשיטה פשוטה וחסינת שגיאות
st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Wolt_logo.svg/512px-Wolt_logo.svg.png", width=120)
st.title("Wolt Israel - Public Policy Scout")
st.subheader("מערכת ארגונית לניטור סיכונים והזדמנויות רגולטוריות")
st.markdown("---")

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
            ("Globes", "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederFeed?c=2"),
            ("TheMarker", "https://www.themarker.com/srv/rss/all"),
            ("Ynet", "https://www.ynet.co.il/Integration/StoryRss538.xml"),
            ("Maariv", "https://www.maariv.co.il/Rss/RssFeedsMivzakim"),
            ("Makor Rishon", "https://www.makorrishon.co.il/category/news/feed/"),
            ("Kipa", "https://www.kipa.co.il/rss/news.xml"),
            ("The Times of Israel", "https://www.timesofisrael.com/il/feed/"),
            ("The Jerusalem Post", "https://www.jpost.com/rss/israelnews")
        ]
        
        news_alerts = []
        for name, url in config_list:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '') or entry.get('description', '') or ''
                    link = entry.get('link', '')
                    pub_date = entry.get('published', '') or entry.get('updated', '') or "---"
                    
                    full_text_lower = f"{title} {summary}".lower()
                    match_he = any(word in full_text_lower for word in KEYWORDS)
                    match_en = any(word in full_text_lower for word in KEYWORDS_EN)
                    
                    if match_he or match_en:
                        if not any(alert['קישור'] == link for alert in news_alerts):
                            news_alerts.append({
                                "מקור": f"📰 {name}",
                                "קטגוריה": "מדיה ואקטואליה",
                                "כותרת": title,
                                "תאריך": pub_date[:16] if len(pub_date) > 16 else pub_date,
                                "עדיפות": "🔵 מעקב מדיה",
                                "קישור": link
                            })
            except:
                continue
        return news_alerts

    # ==========================================
    # 7. בניית ממשק המשתמש (Tabs Layout)
    # ==========================================
    tab1, tab2, tab3 = st.tabs(["🏛️ חקיקה וּועדות (אוטומטי)", "📂 סורק מסמכי ממשלה (PDF)", "📰 רדאר חדשות חי"])

    # טאב 1
    with tab1:
        st.markdown("### התראות רגולטוריות בזמן אמת מהכנסת והממשלה")
        with st.spinner("סורק מאגרים ממשלתיים..."):
            gov_alerts = []
            gov_alerts.extend(fetch_knesset_data())
            gov_alerts.extend(fetch_tazkirim_data())
            
        if not gov_alerts:
            st.info("לא נמצאו דיונים או תזכירי חוק קרובים התואמים את מילות המפתח של וולט.")
        else:
            for alert in gov_alerts:
                st.info(f"**{alert['מקור']}** | {alert['קטגוריה']} \n\n **נושא:** {alert['כותרת']} \n\n תאריך: {alert['תאריך']} | עדיפות: {alert['עדיפות']}")
                st.markdown(f"[🔗 למעבר למקור לחץ כאן]({alert['קישור']})")
                with st.expander("🔍 ניתוח מדיניות והמלצות - Gemini AI"):
                    analysis = analyze_with_gemini(alert['מקור'], alert['קטגוריה'], alert['כותרת'])
                    st.write(analysis)
                st.markdown("---")

    # טאב 2
    with tab2:
        st.markdown("### סורק החלטות ממשלה וועדות שרים")
        st.write("מזכירות הממשלה מפרסמת קובצי PDF. העלה אותם כאן לסריקה וניתוח מיידי:")
        uploaded_file = st.file_uploader("גרור או בחר קובץ PDF של הממשלה", type=["pdf"])
        
        if uploaded_file is not None:
            with st.spinner("ה-AI קורא ומנתח את המסמך..."):
                file_bytes = uploaded_file.read()
                prompt = "אתה מנהל מדיניות ציבורית בוולט ישראל. סרוק את ה-PDF המצורף וחפש סעיפים שקשורים למילות המפתח של החברה. תן תקציר בעברית של סיכונים או הזדמנויות לוולט."
                try:
                    response = model.generate_content([{"mime_type": "application/pdf", "data": file_bytes}, prompt])
                    st.success(response.text)
                except Exception as e:
                    st.error(f"שגיאה בניתוח: {e}")

    # טאב 3
    with tab3:
        st.markdown("### רדאר מדיניות בתקשורת הישראלית והבינלאומית")
        with st.spinner("סורק את 10 אתרי החדשות שהגדרת..."):
            news_alerts = fetch_news_data()
            
        if not news_alerts:
            st.info("אין כתבות אקטואליות חדשות בנושאי הליבה של וולט בשעות האחרונות.")
        else:
            for alert in news_alerts:
                st.info(f"**{alert['מקור']}** \n\n **כתבה:** {alert['כותרת']} \n\n פורסם: {alert['תאריך']}")
                st.markdown(f"[🔗 לקריאת הכתבה המלאה לחץ כאן]({alert['קישור']})")
                with st.expander("🔍 ניתוח ספין והשפעה תקשורתית - Gemini AI"):
                    analysis = analyze_with_gemini(alert['מקור'], "חדשות ומדיה", alert['כותרת'])
                    st.write(analysis)
                st.markdown("---")
