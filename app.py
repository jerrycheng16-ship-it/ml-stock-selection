import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from requests import Session
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import RidgeCV

# 網頁版面設定
st.set_page_config(page_title="多因子機器學習選股與回測儀表板", layout="wide")

# 🎨 自訂 CSS：美化按鈕、縮小並低調化側邊欄的「移除」按鈕、低調化「說明」按鈕
st.markdown(
    """
    <style>
    div[data-baseweb="select"] > div {
        max-height: 200px !important;
        overflow-y: auto !important;
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton > button {
        background-color: #ff4b4b !important;
        color: white !important;
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 0.6em 1em !important;
        width: 100% !important;
        border-radius: 8px !important;
        border: none !important;
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton > button:hover {
        background-color: #ff2b2b !important;
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button {
        background-color: #2b2b2b !important;
        color: #d1d1d1 !important;
        font-size: 15px !important;
        font-weight: normal !important;
        padding: 0.6em 1em !important;
        width: 100% !important;
        border-radius: 8px !important;
        border: 1px solid #444444 !important;
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button:hover {
        background-color: #3d3d3d !important;
        color: #ffffff !important;
        border-color: #666666 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #2b2b2b !important;
        color: #d1d1d1 !important;
        font-size: 12px !important;
        padding: 2px 6px !important;
        width: auto !important;
        border-radius: 4px !important;
        border: 1px solid #444444 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #3d3d3d !important;
        color: #ffffff !important;
        border-color: #666666 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "backtest_executed" not in st.session_state:
    st.session_state.backtest_executed = False

# 🛠️ 主標題與功能描述
st.title("多因子機器學習選股與回測儀表板")
st.markdown("### 【功能說明】結合多因子量化模型（價值、動態、品質、低波動、規模）與機器學習演算法的智慧選股、動態多空對沖回測與績效分析系統。")

# -------------------------------------------------------------
# 1. 0050 完整 50 檔成分股字典
# -------------------------------------------------------------
TW_STOCK_MAP = {
    "2330.TW": "台積電", "2454.TW": "聯發科", "2308.TW": "台達電", "2317.TW": "鴻海",
    "3711.TW": "日月光投控", "2303.TW": "聯電", "2383.TW": "台光電", "3037.TW": "欣興",
    "2881.TW": "富邦金", "2891.TW": "中信金", "2382.TW": "廣達", "2882.TW": "國泰金",
    "2412.TW": "中華電", "2886.TW": "兆豐金", "2884.TW": "玉山金", "1216.TW": "統一",
    "2892.TW": "第一金", "2885.TW": "元大金", "2890.TW": "永豐金", "3045.TW": "台灣大",
    "2357.TW": "華碩", "3231.TW": "緯創", "2603.TW": "長榮", "2345.TW": "智邦",
    "3017.TW": "奇鋐", "2301.TW": "光寶科", "2395.TW": "研華", "4904.TW": "遠傳",
    "2449.TW": "京元電子", "2344.TW": "華邦電", "2408.TW": "南亞科", "3008.TW": "大立光",
    "6669.TW": "緯穎", "3443.TW": "創意", "3653.TW": "健策", "2360.TW": "致茂",
    "2059.TW": "川湖", "4958.TW": "臻鼎-KY", "1303.TW": "南亞", "6505.TW": "台塑化",
    "5880.TW": "合庫金", "2883.TW": "凱基金", "2887.TW": "台新新光金", "2880.TW": "華南金",
    "1301.TW": "台塑", "1326.TW": "台化", "2002.TW": "中鋼", "1101.TW": "台泥",
    "1102.TW": "亞泥", "2610.TW": "華航"
}
TW_KEYS = list(TW_STOCK_MAP.keys())

# -------------------------------------------------------------
# 2. S&P 500 完整字典
# -------------------------------------------------------------
US_STOCK_MAP = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet (Class A)", "GOOG": "Alphabet (Class C)", "META": "Meta Platforms",
    "BRK-B": "Berkshire Hathaway", "LLY": "Eli Lilly and Company", "AVGO": "Broadcom",
    "TSLA": "Tesla", "WMT": "Walmart", "JPM": "JPMorgan Chase", "V": "Visa",
    "XOM": "ExxonMobil", "MA": "Mastercard", "COST": "Costco", "UNH": "UnitedHealth Group",
    "NFLX": "Netflix", "HD": "Home Depot", "PG": "Procter & Gamble", "JNJ": "Johnson & Johnson",
    "BAC": "Bank of America", "ABBV": "AbbVie", "MRK": "Merck & Co.", "CVX": "Chevron",
    "CRM": "Salesforce", "AMD": "Advanced Micro Devices", "TMUS": "T-Mobile US", "ADBE": "Adobe",
    "LIN": "Linde plc", "ACN": "Accenture", "IBM": "IBM", "PEP": "PepsiCo",
    "KO": "Coca-Cola Company", "TMO": "Thermo Fisher Scientific", "MCD": "McDonald's",
    "DIS": "Walt Disney Company", "NOW": "ServiceNow", "GE": "GE Aerospace", "AMAT": "Applied Materials",
    "AXP": "American Express", "ISRG": "Intuitive Surgical", "QCOM": "Qualcomm", "TXN": "Texas Instruments",
    "PFE": "Pfizer", "CAT": "Caterpillar", "UBER": "Uber", "BKNG": "Booking Holdings",
    "PM": "Philip Morris International", "LOW": "Lowe's", "NEE": "NextEra Energy", "RTX": "RTX Corporation",
    "HON": "Honeywell", "COP": "ConocoPhillips", "UNP": "Union Pacific", "BA": "Boeing",
    "SBUX": "Starbucks", "GILD": "Gilead Sciences", "MDLZ": "Mondelez International", "LRCX": "Lam Research",
    "ADI": "Analog Devices", "SRE": "Sempra", "PLTR": "Palantir Technologies", "INTC": "Intel",
    "PYPL": "PayPal", "SNAP": "Snap", "ZM": "Zoom Video Communications", "SHOP": "Shopify",
    "MMM": "3M", "AOS": "A. O. Smith", "ABT": "Abbott Laboratories", "AES": "AES Corporation",
    "AFL": "Aflac", "A": "Agilent Technologies", "APD": "Air Products and Chemicals", "ABNB": "Airbnb",
    "AKAM": "Akamai Technologies", "ALB": "Albemarle", "ARE": "Alexandria Real Estate Equities",
    "ALGN": "Align Technology", "ALLE": "Allegion", "LNT": "Alliant Energy", "ALL": "Allstate",
    "MO": "Altria Group", "AMCR": "Amcor", "AEE": "Ameren", "AEP": "American Electric Power",
    "AIG": "American International Group", "AMT": "American Tower", "AWK": "American Water Works",
    "AMP": "Ameriprise Financial", "AME": "Ametek", "AMGN": "Amgen", "APH": "Amphenol", "ANSS": "Ansys",
    "AON": "Aon", "APA": "APA Corporation", "APTV": "Aptiv", "ACGL": "Arch Capital Group",
    "ADM": "Archer-Daniels-Midland", "ANET": "Arista Networks", "AJG": "Arthur J. Gallagher & Co.",
    "AIZ": "Assurant", "T": "AT&T", "ATO": "Atmos Energy", "ADSK": "Autodesk", "ADP": "Automatic Data Processing",
    "AZO": "AutoZone", "AVB": "AvalonBay Communities", "AVY": "Avery Dennison", "AXON": "Axon Enterprise",
    "BKR": "Baker Hughes", "BALL": "Ball Corporation", "BK": "Bank of New York Mellon", "BBWI": "Bath & Body Works",
    "BAX": "Baxter International", "BDX": "Becton Dickinson", "BBY": "Best Buy", "BIO": "Bio-Rad Laboratories",
    "BIIB": "Biogen", "BLK": "BlackRock", "BX": "Blackstone", "BWA": "BorgWarner", "BSX": "Boston Scientific",
    "BMY": "Bristol Myers Squibb", "BR": "Broadridge Financial Solutions", "BRO": "Brown & Brown",
    "BF-B": "Brown–Forman", "BLDR": "Builders FirstSource", "BG": "Bunge Global", "BXP": "BXP, Inc.",
    "CHRW": "C.H. Robinson", "CDNS": "Cadence Design Systems", "CZR": "Caesars Entertainment",
    "CPT": "Camden Property Trust", "CPB": "Campbell Soup Company", "COF": "Capital One Financial",
    "CAH": "Cardinal Health", "KMX": "CarMax", "CCL": "Carnival Corporation", "CARR": "Carrier Global",
    "CBOE": "Cboe Global Markets", "CBRE": "CBRE Group", "CDW": "CDW", "COR": "Cencora", "CNC": "Centene Corporation",
    "CNP": "CenterPoint Energy", "CF": "CF Industries", "CRL": "Charles River Laboratories",
    "SCHW": "Charles Schwab Corporation", "CHTR": "Charter Communications", "CMG": "Chipotle Mexican Grill",
    "CB": "Chubb Limited", "CHD": "Church & Dwight", "CI": "Cigna", "CINF": "Cincinnati Financial",
    "CTAS": "Cintas", "CSCO": "Cisco", "C": "Citigroup", "CFG": "Citizens Financial Group", "CLX": "Clorox",
    "CME": "CME Group", "CMS": "CMS Energy", "CTSH": "Cognizant", "CL": "Colgate-Palmolive", "CMCSA": "Comcast",
    "CAG": "Conagra Brands", "ED": "Consolidated Edison", "STZ": "Constellation Brands", "CEG": "Constellation Energy",
    "COO": "CooperCompanies", "CPRT": "Copart", "GLW": "Corning", "CPAY": "Corpay", "CTVA": "Corteva",
    "CSGP": "CoStar Group", "CTRA": "Coterra", "CRWD": "CrowdStrike", "CCI": "Crown Castle", "CSX": "CSX Corporation",
    "CMI": "Cummins", "CVS": "CVS Health", "DHR": "Danaher Corporation", "DRI": "Darden Restaurants",
    "DVA": "DaVita Inc.", "DAY": "Dayforce", "DECK": "Deckers Outdoor", "DE": "John Deere", "DAL": "Delta Air Lines",
    "DVN": "Devon Energy", "DXCM": "DexCom", "FANG": "Diamondback Energy", "DLR": "Digital Realty",
    "DFS": "Discover Financial Services", "DG": "Dollar General", "DLTR": "Dollar Tree", "D": "Dominion Energy",
    "DPZ": "Domino's Pizza", "DOV": "Dover Corporation", "DOW": "Dow Inc.", "DHI": "D.R. Horton", "DTE": "DTE Energy",
    "DUK": "Duke Energy", "DD": "DuPont", "EMN": "Eastman Chemical", "ETN": "Eaton Corporation", "EBAY": "eBay",
    "ECL": "Ecolab", "EIX": "Edison International", "EW": "Edwards Lifesciences", "EA": "Electronic Arts",
    "ELV": "Elevance Health", "EMR": "Emerson Electric", "ENPH": "Enphase Energy", "ETR": "Entergy",
    "EOG": "EOG Resources", "EPAM": "EPAM Systems", "EQT": "EQT Corporation", "EFX": "Equifax",
    "EQR": "Equity Residential", "ERIE": "Erie Indemnity", "ESS": "Essex Property Trust", "EL": "Estée Lauder",
    "ETSY": "Etsy", "EG": "Everest Group", "ES": "Eversource Energy", "EXC": "Exelon", "EXPE": "Expedia Group",
    "EXPD": "Expeditors International", "EXR": "Extra Space Storage", "FFIV": "F5, Inc.", "FDS": "FactSet",
    "FICO": "Fair Isaac", "FAST": "Fastenal", "FRT": "Federal Realty", "FDX": "FedEx", "FIS": "Fidelity National",
    "FITB": "Fifth Third Bancorp", "FSLR": "First Solar", "FE": "FirstEnergy", "FI": "FIS", "FLT": "FleetCor",
    "FMC": "FMC Corporation", "F": "Ford Motor Company", "FTNT": "Fortinet", "FTV": "Fortive",
    "FOXA": "Fox (Class A)", "FOX": "Fox (Class B)", "BEN": "Franklin Resources", "FCX": "Freeport-McMoRan",
    "GRMN": "Garmin", "IT": "Gartner", "GEHC": "GE HealthCare", "GEV": "GE Vernova", "GEN": "Gen Digital",
    "GNRC": "Generac Holdings", "GD": "General Dynamics", "GIS": "General Mills", "GM": "General Motors",
    "GPC": "Genuine Parts Company", "GL": "Globe Life", "GPN": "Global Payments", "GS": "Goldman Sachs",
    "HAL": "Halliburton", "HIG": "Hartford Financial", "HAS": "Hasbro", "HCA": "HCA Healthcare",
    "DOC": "Healthpeak Properties", "HSIC": "Henry Schein", "HSY": "Hershey Company", "HES": "Hess Corporation",
    "HPE": "Hewlett Packard Enterprise", "HLT": "Hilton Worldwide", "HOLX": "Hologic", "HRL": "Hormel Foods",
    "HST": "Host Hotels & Resorts", "HWM": "Howmet Aerospace", "HPQ": "HP Inc.", "HUBB": "Hubbell Incorporated",
    "HUM": "Humana", "HBAN": "Huntington Bancshares", "HII": "Huntington Ingalls", "IEX": "IDEX Corporation",
    "IDXX": "Idexxx Laboratories", "ITW": "Illinois Tool Works", "ILMN": "Illumina", "INCY": "Incyte",
    "IR": "Ingersoll Rand", "PODD": "Insulet", "ICE": "Intercontinental Exchange", "IFF": "IFF",
    "IP": "International Paper", "IPG": "Interpublic Group", "INTU": "Intuit", "IVZ": "Invesco",
    "INVH": "Invitation Homes", "IQV": "IQVIA", "IRM": "Iron Mountain", "JBHT": "J.B. Hunt", "JBL": "Jabil",
    "JKHY": "Jack Henry & Associates", "J": "Jacobs Solutions", "JCI": "Johnson Controls", "JNPR": "Juniper Networks",
    "KVUE": "Kenvue", "KDP": "Keurig Dr Pepper", "KEY": "KeyCorp", "KEYS": "Keysight Technologies",
    "KHC": "Kraft Heinz", "KIM": "Kimco Realty", "KMB": "Kimberly-Clark", "KMI": "Kinder Morgan",
    "KLAC": "KLA Corporation", "KR": "Kroger", "LHX": "L3Harris Technologies", "LH": "Labcorp", "LW": "Lamb Weston",
    "LVS": "Las Vegas Sands", "LDOS": "Leidos", "LEN": "Lennar Corporation", "LNC": "Lincoln National",
    "LYV": "Live Nation", "LKQ": "LKQ Corporation", "LMT": "Lockheed Martin", "L": "Loews Corporation",
    "LULU": "Lululemon Athletica", "LYB": "LyondellBasell", "MTB": "M&T Bank", "MPC": "Marathon Petroleum",
    "MKTX": "MarketAxess", "MAR": "Marriott International", "MMC": "Marsh McLennan", "MLM": "Martin Marietta",
    "MAS": "Masco", "MTCH": "Match Group", "MKC": "McCormick & Company", "MCK": "McKesson", "MDT": "Medtronic",
    "MET": "MetLife", "MTD": "Mettler Toledo", "MGM": "MGM Resorts", "MCHP": "Microchip Technology",
    "MU": "Micron Technology", "MAA": "Mid-America Apartment", "MRNA": "Moderna", "MHK": "Mohawk Industries",
    "MOH": "Molina Healthcare", "TAP": "Molson Coors", "MPWR": "Monolithic Power Systems", "MNST": "Monster Beverage",
    "MCO": "Moody's Corporation", "MS": "Morgan Stanley", "MOS": "Mosaic Company", "MSI": "Motorola Solutions",
    "MSCI": "MSCI", "NDAQ": "Nasdaq, Inc.", "NTAP": "NetApp", "NEM": "Newmont", "NWSA": "News Corp (Class A)",
    "NWS": "News Corp (Class B)", "NKE": "Nike, Inc.", "NI": "NiSource", "NDSN": "Nordson Corporation",
    "NSC": "Norfolk Southern Railway", "NTRS": "Northern Trust", "NOC": "Northrop Grumman",
    "NCLH": "Norwegian Cruise Line", "NRG": "NRG Energy", "NUE": "Nucor", "NVR": "NVR, Inc.",
    "NXPI": "NXP Semiconductors", "ORLY": "O'Reilly Auto Parts", "OXY": "Occidental Petroleum",
    "ODFL": "Old Dominion Freight Line", "OMC": "Omnicom Group", "ON": "ON Semiconductor", "OKE": "ONEOK",
    "ORCL": "Oracle Corporation", "OTIS": "Otis Worldwide", "PCAR": "PACCAR", "PKG": "Packaging Corporation",
    "PANW": "Palo Alto Networks", "PARA": "Paramount Global", "PH": "Parker Hannifin", "PAYX": "Paychex",
    "PAYC": "Paycom", "PNR": "Pentair", "PCG": "PG&E Corporation", "PSX": "Phillips 66", "PNW": "Pinnacle West",
    "PNC": "PNC Financial Services", "POOL": "Pool Corporation", "PPG": "PPG Industries", "PPL": "PPL Corporation",
    "PFG": "Principal Financial", "PGR": "Progressive Corporation", "PLD": "Prologis", "PRU": "Prudential Financial",
    "PEG": "Public Service Enterprise", "PSA": "Public Storage", "PHM": "PulteGroup", "PWR": "Quanta Services",
    "DGX": "Quest Diagnostics", "RL": "Ralph Lauren", "RJF": "Raymond James Financial", "O": "Realty Income",
    "REG": "Regency Centers", "REGN": "Regeneron", "RF": "Regions Financial", "RSG": "Republic Services",
    "RMD": "ResMed", "RVTY": "Revvity", "RHI": "Robert Half", "ROK": "Rockwell Automation", "ROL": "Rollins, Inc.",
    "ROP": "Roper Technologies", "ROST": "Ross Stores", "RCL": "Royal Caribbean Group", "SPGI": "S&P Global",
    "SBAC": "SBA Communications", "SLB": "Schlumberger", "STX": "Seagate Technology", "SEE": "Sealed Air",
    "SHW": "Sherwin-Williams", "SPG": "Simon Property Group", "SWKS": "Skyworks Solutions", "SJM": "J.M. Smucker",
    "SNA": "Snap-on", "SEDG": "SolarEdge", "SO": "Southern Company", "LUV": "Southwest Airlines",
    "SWK": "Stanley Black & Decker", "STT": "State Street Corporation", "STLD": "Steel Dynamics", "STE": "STERIS",
    "SYK": "Stryker Corporation", "SMCI": "Supermicro", "SYF": "Synchrony Financial", "SNPS": "Synopsys",
    "SYY": "Sysco", "TROW": "T. Rowe Price", "TTWO": "Take-Two Interactive", "TPR": "Tapestry, Inc.",
    "TRGP": "Targa Resources", "TGT": "Target Corporation", "TEL": "TE Connectivity", "TDY": "Teledyne Technologies",
    "TFX": "Teleflex", "TER": "Teradyne", "TXT": "Textron", "TJX": "TJX Companies", "TSCO": "Tractor Supply",
    "TT": "Trane Technologies", "TDG": "TransDigm Group", "TRV": "Travelers Companies", "TRMB": "Trimble Inc.",
    "TFC": "Truist Financial", "TYL": "Tyler Technologies", "TSN": "Tyson Foods", "USB": "U.S. Bancorp",
    "UDR": "UDR, Inc.", "ULTA": "Ulta Beauty", "UPS": "United Parcel Service", "URI": "United Rentals",
    "UHS": "Universal Health Services", "VLO": "Valero Energy", "VTR": "Ventas", "VRSN": "VeriSign",
    "VRSK": "Verisk Analytics", "VZ": "Verizon Communications", "VRTX": "Vertex Pharmaceuticals",
    "VFC": "V.F. Corporation", "VICI": "VICI Properties", "VST": "Vistra Corp.", "VNO": "Vornado Realty Trust",
    "VMC": "Vulcan Materials", "WAB": "Wabtec", "WBA": "Walgreens Boots Alliance", "WBD": "Warner Bros. Discovery",
    "WM": "Waste Management", "WAT": "Waters Corporation", "WEC": "WEC Energy Group", "WFC": "Wells Fargo",
    "WELL": "Welltower", "WST": "West Pharmaceutical Services", "WDC": "Western Digital", "WY": "Weyerhaeuser",
    "WHR": "Whirlpool Corporation", "WMB": "Williams Companies", "WTW": "Willis Towers Watson",
    "GWW": "W. W. Grainger", "WYNN": "Wynn Resorts", "XEL": "Xcel Energy", "XYL": "Xylem", "YUM": "Yum! Brands",
    "ZBRA": "Zebra Technologies", "ZBH": "Zimmer Biomet", "ZTS": "Zoetis"
}
US_KEYS = list(US_STOCK_MAP.keys())

# -------------------------------------------------------------
# 3. 跨資產 ETF 配置字典 (已移除 BNO)
# -------------------------------------------------------------
ETF_STOCK_MAP = {
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "TLT": "20+年期美國公債 ETF",
    "GLD": "黃金信託 ETF", "IWM": "羅素 2000 小型股 ETF", "VNQ": "美國房地產 ETF",
    "SMH": "半導體產業 ETF", "VGK": "歐洲 FTSE ETF", "EWT": "MSCI 台灣 ETF",
    "EWY": "MSCI 韓國 ETF", "HYG": "美國高收益債 ETF", "EMB": "新興市場美元債 ETF",
    "NDIA": "印度概念 ETF", "ASHR": "中國滬深 300 ETF", "AAXJ": "亞洲除日本 ETF",
    "EEM": "MSCI 新興市場 ETF", "SLV": "白銀信託 ETF", "EWZ": "MSCI 巴西 ETF",
    "IEF": "7-10年期美國公債 ETF"
}
ETF_KEYS = list(ETF_STOCK_MAP.keys())

# -------------------------------------------------------------
# 側邊欄設定
# -------------------------------------------------------------
st.sidebar.header("參數與市場設定")

market_choice = st.sidebar.selectbox("選擇交易市場", ["🇹🇼 台灣股市 (台股)", "🇺🇸 美國股市 (美股)", "🌐 跨資產 ETF 配置"], key="market_choice_box")

if "🇹🇼" in market_choice:
    market_key = "TW"
    ALL_STOCK_MAP = TW_STOCK_MAP
    benchmark_ticker = "^TWII"
    benchmark_name = "台灣加權指數 (TWII)"
    default_selected = TW_KEYS[:20]
    default_manual = "2330.TW"
elif "🇺🇸" in market_choice:
    market_key = "US"
    ALL_STOCK_MAP = US_STOCK_MAP
    benchmark_ticker = "^GSPC"
    benchmark_name = "標普 500 指數 (S&P 500)"
    default_selected = US_KEYS[:20]
    default_manual = "TSM"
else:
    market_key = "ETF"
    ALL_STOCK_MAP = ETF_STOCK_MAP
    benchmark_ticker = "SPY"
    benchmark_name = "S&P 500 ETF (SPY)"
    default_selected = ETF_KEYS[:10]
    default_manual = "TLT"

if "last_market_key" not in st.session_state or st.session_state.last_market_key != market_key:
    st.session_state.last_market_key = market_key
    st.session_state.selected_stocks_state = default_selected
    st.session_state.my_multiselect = default_selected
    st.session_state.manual_added_stocks = [default_manual]
    st.session_state.excluded_stocks = []
    st.session_state.backtest_executed = False

if "selected_stocks_state" not in st.session_state:
    st.session_state.selected_stocks_state = default_selected
if "my_multiselect" not in st.session_state:
    st.session_state.my_multiselect = default_selected
if "manual_added_stocks" not in st.session_state:
    st.session_state.manual_added_stocks = [default_manual]
if "excluded_stocks" not in st.session_state:
    st.session_state.excluded_stocks = []

train_window = st.sidebar.slider("訓練月數 (Train Window)", min_value=12, max_value=60, value=36, step=6)
target_start_date = st.sidebar.date_input("回測開始日期", pd.to_datetime("2023-12-31"))
target_end_date = st.sidebar.date_input("回測結束日期", pd.to_datetime("2026-12-31"))

st.sidebar.markdown("---")
st.sidebar.subheader("觀察股票池設定")

if market_key == "TW":
    st.sidebar.markdown("##### ⚡ 0050 內建快速組合 (依市值排序)")
    c1, c2 = st.sidebar.columns(2)
    c3, c4 = st.sidebar.columns(2)
    KEYS_POOL = TW_KEYS
    if c1.button("Top 20"):
        st.session_state.selected_stocks_state = KEYS_POOL[:20]
        st.session_state.my_multiselect = KEYS_POOL[:20]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c2.button("Top 30"):
        st.session_state.selected_stocks_state = KEYS_POOL[:30]
        st.session_state.my_multiselect = KEYS_POOL[:30]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c3.button("Top 50"):
        st.session_state.selected_stocks_state = KEYS_POOL[:50]
        st.session_state.my_multiselect = KEYS_POOL[:50]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c4.button("每5名選1(共10)"):
        sampled_10 = [KEYS_POOL[i] for i in range(0, len(KEYS_POOL), 5)][:10]
        st.session_state.selected_stocks_state = sampled_10
        st.session_state.my_multiselect = sampled_10
        st.session_state.excluded_stocks = []
        st.rerun()
    st.sidebar.markdown("---")
elif market_key == "US":
    st.sidebar.markdown("##### ⚡ S&P 500 內建快速組合 (依市值排序)")
    c1, c2 = st.sidebar.columns(2)
    c3, c4 = st.sidebar.columns(2)
    KEYS_POOL = US_KEYS
    if c1.button("Top 20"):
        st.session_state.selected_stocks_state = KEYS_POOL[:20]
        st.session_state.my_multiselect = KEYS_POOL[:20]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c2.button("Top 30"):
        st.session_state.selected_stocks_state = KEYS_POOL[:30]
        st.session_state.my_multiselect = KEYS_POOL[:30]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c3.button("Top 50"):
        st.session_state.selected_stocks_state = KEYS_POOL[:50]
        st.session_state.my_multiselect = KEYS_POOL[:50]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c4.button("每25名抽1(共20)"):
        sampled_20 = [KEYS_POOL[i] for i in range(0, min(len(KEYS_POOL), 500), 25)][:20]
        st.session_state.selected_stocks_state = sampled_20
        st.session_state.my_multiselect = sampled_20
        st.session_state.excluded_stocks = []
        st.rerun()
    st.sidebar.markdown("---")
else:
    st.sidebar.markdown("##### ⚡ 跨資產 ETF 快速組合")
    c1, c2 = st.sidebar.columns(2)
    c3, c4 = st.sidebar.columns(2)
    KEYS_POOL = ETF_KEYS
    if c1.button("Top 10"):
        st.session_state.selected_stocks_state = KEYS_POOL[:10]
        st.session_state.my_multiselect = KEYS_POOL[:10]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c2.button("Top 15"):
        st.session_state.selected_stocks_state = KEYS_POOL[:15]
        st.session_state.my_multiselect = KEYS_POOL[:15]
        st.session_state.excluded_stocks = []
        st.rerun()
    if c3.button("全部列出 (19檔)"):
        st.session_state.selected_stocks_state = KEYS_POOL
        st.session_state.my_multiselect = KEYS_POOL
        st.session_state.excluded_stocks = []
        st.rerun()
    if c4.button("核心資產組合"):
        core_etfs = ["SPY", "QQQ", "TLT", "GLD", "IWM", "VNQ", "IEF", "HYG"]
        st.session_state.selected_stocks_state = core_etfs
        st.session_state.my_multiselect = core_etfs
        st.session_state.excluded_stocks = []
        st.rerun()
    st.sidebar.markdown("---")

if market_key == "TW":
    pool_label = "從 0050 名單勾選或搜尋"
elif market_key == "US":
    pool_label = "從 S&P 500 名單勾選或搜尋"
else:
    pool_label = "從跨資產 ETF 名單勾選或搜尋"

valid_defaults = [s for s in st.session_state.selected_stocks_state if s in ALL_STOCK_MAP]
if not valid_defaults:
    valid_defaults = default_selected

def update_selection():
    st.session_state.selected_stocks_state = st.session_state.my_multiselect

selected_pool = st.sidebar.multiselect(
    pool_label,
    options=list(ALL_STOCK_MAP.keys()),
    default=valid_defaults,
    format_func=lambda x: f"{x} - {ALL_STOCK_MAP[x]}",
    key="my_multiselect",
    on_change=update_selection
)

st.session_state.selected_stocks_state = selected_pool

if len(st.session_state.selected_stocks_state) > 50:
    st.sidebar.warning("⚠️ 觀察池上限為 50 檔，已自動幫您截取前 50 檔以優化運算效能。")
    st.session_state.selected_stocks_state = st.session_state.selected_stocks_state[:50]

st.sidebar.markdown("##### 📌 (2) 手動輸入其他標的")
st.sidebar.caption("輸入其他代號（用逗號分隔）：")
manual_input = st.sidebar.text_input("輸入代號", "")
user_manual_list = [s.strip().upper() for s in manual_input.split(",") if s.strip()]

required_months = train_window + 12 
if user_manual_list:
    check_start_date = pd.to_datetime(target_start_date) - pd.DateOffset(months=required_months)
    for ticker in user_manual_list:
        if ticker not in ALL_STOCK_MAP:
            ALL_STOCK_MAP[ticker] = f"自選股 ({ticker})"
        try:
            test_df = yf.download(ticker, start=check_start_date.strftime("%Y-%m-%d"), progress=False)
            if test_df.empty or len(test_df) < 50:
                st.sidebar.error(f"❌ {ticker}：歷史資料不足")
            else:
                earliest_date = test_df.index.min()
                if earliest_date > check_start_date + pd.DateOffset(months=6):
                    st.sidebar.error(f"❌ {ticker}：歷史資料未滿訓練期")
                else:
                    if ticker not in st.session_state.manual_added_stocks:
                        st.session_state.manual_added_stocks.append(ticker)
                    if ticker in st.session_state.excluded_stocks:
                        st.session_state.excluded_stocks.remove(ticker)
                    st.sidebar.success(f"✅ {ticker} 通過檢核並加入！")
        except:
            st.sidebar.error(f"❌ {ticker}：無法取得有效歷史資料")

combined_pool = []
for ticker in st.session_state.selected_stocks_state + st.session_state.manual_added_stocks:
    if ticker not in combined_pool:
        combined_pool.append(ticker)

final_stock_pool = [t for t in combined_pool if t not in st.session_state.excluded_stocks and t in ALL_STOCK_MAP]

if len(final_stock_pool) > 50:
    final_stock_pool = final_stock_pool[:50]

st.session_state.final_exec_pool = final_stock_pool
pool_count = len(final_stock_pool)

st.sidebar.markdown("---")
st.sidebar.markdown(f"##### 📌 (3) 最終觀察池與管理 ({pool_count}/50 檔上限)")

col_cl1, col_cl2 = st.sidebar.columns([2, 1])
col_cl1.caption("點擊「移除」可個別取消：")
if col_cl2.button("清除全部"):
    st.session_state.excluded_stocks = list(combined_pool)
    st.session_state.manual_added_stocks = []
    st.session_state.selected_stocks_state = []
    st.session_state.my_multiselect = []
    st.session_state.backtest_executed = False
    st.rerun()

if final_stock_pool:
    for ticker in final_stock_pool:
        col_a, col_b = st.sidebar.columns([3, 1])
        col_a.text(f"{ticker} ({ALL_STOCK_MAP.get(ticker, '自選')})")
        if col_b.button("移除", key=f"rm_{ticker}_{market_key}"):
            if ticker in st.session_state.manual_added_stocks:
                st.session_state.manual_added_stocks.remove(ticker)
            if ticker in st.session_state.selected_stocks_state:
                st.session_state.selected_stocks_state.remove(ticker)
            if ticker in st.session_state.get("my_multiselect", []):
                st.session_state.my_multiselect.remove(ticker)
            if ticker not in st.session_state.excluded_stocks:
                st.session_state.excluded_stocks.append(ticker)
            st.session_state.backtest_executed = False
            st.rerun()
else:
    st.sidebar.warning("目前觀察池為空")

st.sidebar.markdown("---")

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    run_backtest = st.button("🚀 開始執行回測與機器學習運算")
with col_btn2:
    show_guide = st.button("📖 說明")

if "show_help" not in st.session_state:
    st.session_state.show_help = False

if show_guide:
    st.session_state.show_help = not st.session_state.show_help

if st.session_state.show_help:
    with st.container():
        st.markdown(f"""
        ### 📖 網站操作說明與使用指南 ({market_choice})
        本系統旨在協助您透過量化多因子與機器學習來進行智慧選股與歷史回測。
        """)
        st.markdown("---")

if run_backtest:
    active_eval_pool = st.session_state.get("final_exec_pool", [])
    if not active_eval_pool:
        st.error("請至少選擇或輸入一檔符合資格的股票或 ETF！")
    else:
        with st.spinner(f"正在向 Yahoo Finance 同步 {market_choice} 數據並執行機器學習回測中，請稍候..."):
            session = Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            stock_fundamentals = {}
            default_fallback_tickers = []

            for ticker in active_eval_pool:
                try:
                    tk = yf.Ticker(ticker, session=session)
                    info = tk.info
                    pe = info.get("trailingPE", 20.0)
                    if pe is None or pe <= 0:
                        pe = 20.0
                    val_metric = 1.0 / pe
                    margin = info.get("profitMargins", 0.15)
                    if margin is None:
                        margin = 0.15
                    mcap = info.get("marketCap", 1e11)
                    if mcap is None:
                        mcap = 1e11
                    size_metric = np.log(mcap)
                    stock_fundamentals[ticker] = {"Value": val_metric, "Quality": margin, "Size": size_metric}
                except Exception as e:
                    default_fallback_tickers.append(ticker)
                    stock_fundamentals[ticker] = {"Value": 0.05, "Quality": 0.15, "Size": 25.0}

            if default_fallback_tickers:
                st.warning(f"⚠️ 注意：以下標的無法順利取得完整基本面數據（如 ETF 無本益比，或雲端連線受限），已自動以預設值 (Value=5) 替代：{', '.join(default_fallback_tickers)}")

            fetch_start_date = pd.to_datetime(target_start_date) - pd.DateOffset(months=(12 + train_window))
            fetch_end_date = pd.to_datetime(target_end_date) + pd.Timedelta(days=5)

            download_tickers = list(set(active_eval_pool + [benchmark_ticker]))
            df_raw = yf.download(download_tickers, start=fetch_start_date.strftime("%Y-%m-%d"), end=fetch_end_date.strftime("%Y-%m-%d"), progress=False, threads=True)
            df_prices = df_raw["Adj Close"] if "Adj Close" in df_raw.columns else df_raw["Close"]
            if isinstance(df_prices, pd.Series):
                df_prices = df_prices.to_frame()

            benchmark_monthly_ret = df_prices[benchmark_ticker].resample("ME").last().pct_change().shift(-1) if benchmark_ticker in df_prices.columns else pd.Series(dtype=float)

            stock_prices = df_prices[[col for col in active_eval_pool if col in df_prices.columns]].ffill().bfill()
            if isinstance(stock_prices, pd.Series):
                stock_prices = stock_prices.to_frame(name=active_eval_pool[0])

            df_monthly = stock_prices.resample("ME").last()
            df_next_ret = df_monthly.pct_change().shift(-1)
            df_mom = df_monthly.pct_change(12)

            df_daily_ret = stock_prices.pct_change()
            df_vol_monthly = (df_daily_ret.rolling(252).std() * np.sqrt(252)).resample("ME").last()

            dataset = []
            valid_dates = df_monthly.index[12:-1]

            for date in valid_dates:
                date_str = date.strftime("%Y-%m-%d")
                for ticker in active_eval_pool:
                    if ticker not in df_monthly.columns:
                        continue
                    mom_val = df_mom.loc[date, ticker] if date in df_mom.index else np.nan
                    vol_val = df_vol_monthly.loc[date, ticker] if date in df_vol_monthly.index else np.nan
                    next_ret_val = df_next_ret.loc[date, ticker] if date in df_next_ret.index else np.nan

                    if pd.isna(mom_val) or pd.isna(vol_val) or pd.isna(next_ret_val):
                        continue

                    fund = stock_fundamentals.get(ticker, {"Value": 0.05, "Quality": 0.15, "Size": 25.0})
                    dataset.append({
                        "Date": date_str, "Stock": ticker,
                        "Value": round(fund["Value"] * 100, 2),
                        "Momentum": round(mom_val * 100, 2), 
                        "Quality": round(fund["Quality"] * 100, 2), 
                        "LowVol": round(vol_val * 100, 2), 
                        "Size": round(fund["Size"], 2),
                        "Next_Return": next_ret_val * 100
                    })

            raw_data_df = pd.DataFrame(dataset)
            if raw_data_df.empty:
                st.error("抓取不到足夠的歷史資料！")
            else:
                data = raw_data_df.copy()
                data["Date"] = pd.to_datetime(data["Date"])
                data = data.set_index(["Date", "Stock"])

                base_features = ["Value", "Momentum", "Quality", "LowVol", "Size"]
                data[base_features] = data.groupby("Date")[base_features].transform(lambda g: g.rank(pct=True) * 2 - 1)

                poly = PolynomialFeatures(degree=2, include_bias=False)
                expanded_feats = poly.fit_transform(data[base_features])
                expanded_feat_names = poly.get_feature_names_out(base_features)

                data_expanded = pd.DataFrame(expanded_feats, index=data.index, columns=expanded_feat_names)
                data_expanded["Next_Return"] = data["Next_Return"]

                dates = data_expanded.index.get_level_values("Date").unique().sort_values()

                portfolio_returns = []
                n_stocks = len(active_eval_pool)
                n_top = max(1, int(n_stocks * 0.2))
                alphas_range = np.logspace(-2, 4, 10)

                for t in range(train_window, len(dates)):
                    test_date = dates[t]
                    train_dates = dates[t - train_window : t]
                    train_data = data_expanded.loc[train_dates]
                    test_data = data_expanded.loc[test_date]

                    X_tr, y_tr = train_data[expanded_feat_names], train_data["Next_Return"]
                    X_te, y_te = test_data[expanded_feat_names], test_data["Next_Return"]

                    model = RidgeCV(alphas=alphas_range).fit(X_tr, y_tr)
                    preds = model.predict(X_te)

                    res = pd.DataFrame({"Stock": test_data.index.get_level_values("Stock"), "Actual": y_te.values, "Pred": preds})
                    res["Rank"] = res["Pred"].rank(ascending=False, method='first')
                    res["Stock_Name"] = res["Stock"].map(lambda s: ALL_STOCK_MAP.get(s, s))

                    long_df = res[res["Rank"] <= n_top]
                    short_df = res[res["Rank"] > (n_stocks - n_top)]
                    bm_ret = (benchmark_monthly_ret.loc[test_date] * 100) if test_date in benchmark_monthly_ret.index else np.nan

                    portfolio_returns.append({
                        "Date": test_date,
                        "Long_Stock": ",".join(long_df["Stock_Name"].values),
                        "Long_Return": long_df["Actual"].mean(),
                        "Short_Stock": ",".join(short_df["Stock_Name"].values),
                        "Short_Return": short_df["Actual"].mean(),
                        "LongShort_Return": long_df["Actual"].mean() - short_df["Actual"].mean(),
                        "Benchmark_Return": bm_ret
                    })

                df_backtest = pd.DataFrame(portfolio_returns)
                if df_backtest.empty:
                    st.warning("在您設定的回測期間內沒有足夠的回測資料！")
                else:
                    df_backtest = df_backtest.set_index("Date")
                    df_backtest = df_backtest.loc[pd.to_datetime(target_start_date):pd.to_datetime(target_end_date)]

                    df_backtest["Long_Nav"] = (1 + df_backtest["Long_Return"].fillna(0) / 100).cumprod()
                    df_backtest["Short_Nav"] = (1 + df_backtest["Short_Return"].fillna(0) / 100).cumprod()
                    df_backtest["Benchmark_Nav"] = (1 + df_backtest["Benchmark_Return"].fillna(0) / 100).cumprod()

                    def calc_drawdown(nav_series):
                        roll_max = nav_series.cummax()
                        return (nav_series - roll_max) / roll_max

                    max_dd_long = calc_drawdown(df_backtest["Long_Nav"]).min() * 100
                    max_dd_short = calc_drawdown(df_backtest["Short_Nav"]).min() * 100
                    max_dd_bm = calc_drawdown(df_backtest["Benchmark_Nav"]).min() * 100

                    mean_long_ret = df_backtest['Long_Return'].mean()
                    mean_short_ret = df_backtest['Short_Return'].mean()
                    mean_bm_ret = df_backtest["Benchmark_Return"].mean()
                    win_rate = (df_backtest['LongShort_Return'] > 0).mean() * 100

                    summary_df = pd.DataFrame([
                        {"指標": "Long (多頭組合) 平均月報酬", "數值": f"{mean_long_ret:.2f}%", "Max Drawdown": f"{max_dd_long:.2f}%"},
                        {"指標": "Short (空頭組合) 平均月報酬", "數值": f"{mean_short_ret:.2f}%", "Max Drawdown": f"{max_dd_short:.2f}%"},
                        {"指標": f"大盤指數 ({benchmark_name})", "數值": f"{mean_bm_ret:.2f}%", "Max Drawdown": f"{max_dd_bm:.2f}%"},
                        {"指標": "Long-Short (多空對沖) 勝率", "數值": f"{win_rate:.2f}%", "Max Drawdown": "-"}
                    ])

                    latest_date = dates[-1]
                    next_month_str = (latest_date + pd.DateOffset(months=1)).strftime("%Y-%m")
                    train_dates = dates[-1 - train_window : -1]
                    X_train, y_train = data_expanded.loc[train_dates, expanded_feat_names], data_expanded.loc[train_dates, "Next_Return"]
                    X_test = data_expanded.loc[dates[-1], expanded_feat_names]

                    model_latest = RidgeCV(alphas=alphas_range).fit(X_tr, y_tr)
                    preds_latest = model_latest.predict(X_test)

                    latest_results = pd.DataFrame({
                        "股票代碼": X_test.index.get_level_values("Stock"),
                        "預測Alpha": preds_latest
                    })
                    latest_results["股票名稱"] = latest_results["股票代碼"].map(ALL_STOCK_MAP)
                    latest_results["排名"] = latest_results["預測Alpha"].rank(ascending=False, method='first').astype(int)
                    latest_results["訊號"] = "HOLD"
                    latest_results.loc[latest_results["排名"] <= n_top, "訊號"] = "🔥 LONG (買進)"
                    latest_results.loc[latest_results["排名"] > (n_stocks - n_top), "訊號"] = "❄️ SHORT (放空)"

                    st.session_state.backtest_executed = True
                    st.session_state.next_month_str = next_month_str
                    st.session_state.latest_results = latest_results
                    st.session_state.summary_df = summary_df
                    st.session_state.df_backtest = df_backtest
                    st.session_state.raw_data_df = raw_data_df
                    st.session_state.n_top = n_top
                    st.session_state.n_stocks = n_stocks

if st.session_state.backtest_executed:
    next_month_str = st.session_state.next_month_str
    latest_results = st.session_state.latest_results
    summary_df = st.session_state.summary_df
    df_backtest = st.session_state.df_backtest
    raw_data_df = st.session_state.raw_data_df
    n_top = st.session_state.n_top
    n_stocks = st.session_state.n_stocks

    st.subheader(f"🏆 【{next_month_str} 最新排名與信號】({market_choice})")
    display_latest_results = latest_results.sort_values("排名")[["排名", "股票代碼", "股票名稱", "訊號", "預測Alpha"]].copy()
    display_latest_results["股票代碼"] = display_latest_results["股票代碼"].apply(
        lambda s: f"[{s}](https://finance.yahoo.com/quote/{s}/chart?range=1y&interval=1d)"
    )
    st.markdown(display_latest_results.to_markdown(index=False), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📊 【歷史回測績效與 Max Drawdown 摘要】")
    st.table(summary_df)

    st.markdown("---")
    st.subheader("📈 【累積淨值走勢圖 (Nav)】")
    chart_data = df_backtest[["Long_Nav", "Short_Nav", "Benchmark_Nav"]]
    chart_data.columns = ["Long 組合", "Short 組合", benchmark_name]
    st.line_chart(chart_data)

    st.markdown("---")
    with st.expander("📅 【點擊展開：每月對沖報酬與明細資料】"):
        display_df = df_backtest.reset_index()
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
        for col in ["Long_Return", "Short_Return", "LongShort_Return", "Benchmark_Return"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].round(2).astype(str) + "%"
        st.dataframe(display_df, use_container_width=True)

    st.markdown("---")
    with st.expander("📋 【點擊展開：原始因子與特徵明細資料 (Raw Data - 🔒 管理員專用)】"):
        password_input = st.text_input("請輸入管理員密碼以檢視 Raw Data", type="password", key="raw_data_pwd")
        if password_input == "Jerry0722":
            st.success("✅ 密碼正確！已解鎖原始特徵明細資料：")
            st.dataframe(raw_data_df, use_container_width=True)
        elif password_input:
            st.error("❌ 密碼錯誤，請重新輸入。")
        else:
            st.info("💡 提示：本區塊含有機器學習特徵與原始模型數據，需輸入正確授權密碼方可解鎖。")
