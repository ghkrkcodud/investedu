"""
📈 모의투자 플랫폼 - 최종 버전
==================================================
실행: streamlit run app_final.py

추가 기능:
  1. 태블릿 반응형 UI 최적화
  2. 커뮤니티 탭 (초보자 질문 / 전문가 답변)
  3. 거래 탭 주가 차트 (캔들스틱 + 라인)
  4. 속도 최적화 유지 (병렬 조회 + 캐싱)
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import random
import requests
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# ──────────────────────────────────────────────
# ★ KIS API 설정
# ──────────────────────────────────────────────
KIS_APP_KEY    = "여기에_앱키_입력"
KIS_APP_SECRET = "여기에_앱시크릿_입력"
KIS_BASE_URL   = "https://openapivts.koreainvestment.com:29443"
# KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"  # 실전

_KIS_ENABLED = (
    KIS_APP_KEY != "여기에_앱키_입력" and
    KIS_APP_SECRET != "여기에_앱시크릿_입력" and
    len(KIS_APP_KEY) > 10
)
CACHE_TTL = 5

# ──────────────────────────────────────────────
# 0. 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="모의투자 플랫폼",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# 1. CSS — 태블릿 반응형 포함
# ──────────────────────────────────────────────
@st.cache_data
def _css():
    return """<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap');

html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif;}

/* ── 태블릿 반응형 ── */
@media (max-width: 1024px) {
    .block-container{padding:1rem !important;}
    .stat-value{font-size:17px !important;}
    .stat-label{font-size:11px !important;}
    section[data-testid="stSidebar"]{width:200px !important;}
    .stRadio label{font-size:13px !important;}
}
@media (max-width: 768px) {
    .block-container{padding:0.5rem !important;}
    .stat-card{padding:12px 14px !important;}
    .stat-value{font-size:15px !important;}
}

/* ── 사이드바 ── */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1628,#0f2040);}
section[data-testid="stSidebar"] *{color:#e8f0fe !important;}
section[data-testid="stSidebar"] .stRadio label{font-size:15px !important;padding:6px 0 !important;}

/* ── 카드 ── */
.stat-card{background:linear-gradient(135deg,#1a2f4e,#0d1f35);border:1px solid #1e4070;border-radius:14px;padding:18px 20px;color:white;height:100%;}
.stat-label{font-size:12px;color:#7fa8cc;margin-bottom:6px;}
.stat-value{font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace;}
.stat-sub{font-size:12px;margin-top:6px;color:#aac4de;}
.up{color:#ff5858 !important;}.down{color:#4da6ff !important;}.neutral{color:#aac4de !important;}

/* ── 호가창 ── */
.ask-row{background:#fff5f5;border-radius:6px;padding:5px 10px;margin:2px 0;display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:13px;}
.bid-row{background:#f0f6ff;border-radius:6px;padding:5px 10px;margin:2px 0;display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:13px;}
.cur-row{background:#1a2f4e;color:white;border-radius:6px;padding:8px 10px;margin:4px 0;display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:15px;}

/* ── 미션 ── */
.mission-card{border:1px solid #e0e8f0;border-radius:12px;padding:16px 18px;margin:8px 0;background:white;}
.mission-done{border:1px solid #b7ebc8;border-radius:12px;padding:16px 18px;margin:8px 0;background:#f0fff4;opacity:.85;}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-right:6px;}
.badge-입문{background:#d4edda;color:#155724;}.badge-중급{background:#fff3cd;color:#856404;}
.badge-고급{background:#f8d7da;color:#721c24;}.badge-완료{background:#cce5ff;color:#004085;}

/* ── 커뮤니티 ── */
.post-card{border:1px solid #e0e8f0;border-radius:12px;padding:16px 18px;margin:10px 0;background:white;transition:box-shadow .15s;}
.post-card:hover{box-shadow:0 4px 16px rgba(74,144,226,.12);}
.post-title{font-size:16px;font-weight:700;color:#1a1a2e;margin-bottom:6px;}
.post-meta{font-size:12px;color:#888;margin-bottom:8px;}
.post-body{font-size:14px;color:#444;line-height:1.7;}
.answer-card{border-left:4px solid #4a90e2;background:#f8faff;border-radius:0 10px 10px 0;padding:12px 16px;margin:8px 0;}
.expert-badge{background:#4a90e2;color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;}
.tag{background:#e8f0fe;color:#4a90e2;padding:2px 8px;border-radius:12px;font-size:11px;margin-right:4px;}
.tag-hot{background:#fff0f0;color:#ff5858;padding:2px 8px;border-radius:12px;font-size:11px;margin-right:4px;}

/* ── 기타 ── */
.dict-card{border-left:4px solid #4a90e2;background:#f8faff;border-radius:0 10px 10px 0;padding:14px 18px;margin:8px 0;}
.toast{background:#1a2f4e;color:white;padding:12px 20px;border-radius:10px;border-left:4px solid #4a90e2;margin:8px 0;}
.api-real{background:#d4edda;color:#155724;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;display:inline-block;}
.api-demo{background:#fff3cd;color:#856404;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;display:inline-block;}
div[data-testid="stButton"]>button{border-radius:8px;font-weight:600;font-family:'Noto Sans KR',sans-serif;min-height:40px;}
.stNumberInput input,.stTextInput input,.stTextArea textarea{border-radius:8px !important;font-family:'Noto Sans KR',sans-serif !important;}
</style>"""

st.markdown(_css(), unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 2. KIS API
# ──────────────────────────────────────────────
class KISApi:
    def __init__(self):
        self._token=None; self._token_exp=0

    def _get_token(self):
        if self._token and time.time()<self._token_exp: return self._token
        res=requests.post(f"{KIS_BASE_URL}/oauth2/tokenP",
            json={"grant_type":"client_credentials","appkey":KIS_APP_KEY,"appsecret":KIS_APP_SECRET},timeout=10)
        d=res.json()
        if "access_token" not in d: raise ValueError(f"토큰 발급 실패: {d}")
        self._token=d["access_token"]; self._token_exp=time.time()+42000
        return self._token

    def _h(self,tr_id):
        return {"Content-Type":"application/json","authorization":f"Bearer {self._get_token()}",
                "appkey":KIS_APP_KEY,"appsecret":KIS_APP_SECRET,"tr_id":tr_id}

    def get_price(self,ticker):
        res=requests.get(f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=self._h("FHKST01010100"),
            params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":ticker},timeout=8)
        out=res.json().get("output",{})
        if not out or int(out.get("stck_prpr",0))==0: raise ValueError("가격 없음")
        return {"ticker":ticker,"current_price":int(out["stck_prpr"]),"open_price":int(out["stck_oprc"]),
                "high_price":int(out["stck_hgpr"]),"low_price":int(out["stck_lwpr"]),
                "volume":int(out["acml_vol"]),"change_rate":float(out["prdy_ctrt"]),"change_price":int(out["prdy_vrss"])}

    def get_orderbook(self,ticker):
        res=requests.get(f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
            headers=self._h("FHKST01010200"),
            params={"FID_COND_MRKT_DIV_CODE":"J","FID_INPUT_ISCD":ticker},timeout=8)
        out=res.json().get("output1",{})
        asks=[{"price":int(out.get(f"askp{i}",0)),"qty":int(out.get(f"askp_rsqn{i}",0))} for i in range(1,6)]
        bids=[{"price":int(out.get(f"bidp{i}",0)),"qty":int(out.get(f"bidp_rsqn{i}",0))} for i in range(1,6)]
        return {"asks":asks,"bids":bids,"current":asks[0]["price"] if asks else 0}


# ──────────────────────────────────────────────
# 3. 데모 데이터
# ──────────────────────────────────────────────
DEMO_STOCKS={
    "005930":{"name":"삼성전자",        "base_price":75000, "sector":"반도체","desc":"세계 최대 메모리 반도체 기업"},
    "000660":{"name":"SK하이닉스",       "base_price":189000,"sector":"반도체","desc":"HBM 메모리 선도 기업"},
    "035420":{"name":"NAVER",           "base_price":195000,"sector":"IT",   "desc":"국내 1위 포털·클라우드 기업"},
    "035720":{"name":"카카오",           "base_price":42000, "sector":"IT",   "desc":"모바일 플랫폼·핀테크 기업"},
    "051910":{"name":"LG화학",           "base_price":320000,"sector":"화학", "desc":"배터리 소재·석유화학 기업"},
    "006400":{"name":"삼성SDI",          "base_price":280000,"sector":"배터리","desc":"전기차 배터리 선도 기업"},
    "207940":{"name":"삼성바이오로직스",  "base_price":820000,"sector":"바이오","desc":"바이오 의약품 위탁생산 세계 1위"},
    "068270":{"name":"셀트리온",         "base_price":175000,"sector":"바이오","desc":"바이오시밀러 전문 기업"},
    "105560":{"name":"KB금융",           "base_price":87000, "sector":"금융", "desc":"국내 최대 금융지주"},
    "055550":{"name":"신한지주",         "base_price":53000, "sector":"금융", "desc":"글로벌 은행 및 금융서비스"},
    "000270":{"name":"기아",            "base_price":115000,"sector":"자동차","desc":"전기차 전환 선도 완성차 기업"},
    "005380":{"name":"현대차",           "base_price":245000,"sector":"자동차","desc":"글로벌 완성차 및 수소차 기업"},
    "069500":{"name":"KODEX 200",       "base_price":36000, "sector":"ETF",  "desc":"코스피 200 추종 대표 ETF"},
    "360750":{"name":"TIGER 미국S&P500","base_price":17500, "sector":"ETF",  "desc":"미국 S&P500 지수 추종 ETF"},
}

MISSIONS=[
    {"id":1,"title":"첫 번째 투자",      "desc":"주식을 1종목 이상 매수해보세요.",           "type":"min_tickers","value":1,      "reward":50000, "difficulty":"입문"},
    {"id":2,"title":"분산 투자 입문",    "desc":"서로 다른 3개 종목 이상을 보유하세요.",    "type":"min_tickers","value":3,      "reward":100000,"difficulty":"입문"},
    {"id":3,"title":"포트폴리오 다각화", "desc":"5개 종목 이상을 동시에 보유하세요.",      "type":"min_tickers","value":5,      "reward":200000,"difficulty":"중급"},
    {"id":4,"title":"섹터 분산 투자",    "desc":"3개 이상 다른 섹터에 투자하세요.",        "type":"min_sectors","value":3,      "reward":300000,"difficulty":"중급"},
    {"id":5,"title":"ETF 투자자",        "desc":"ETF 종목을 1개 이상 보유하세요.",         "type":"has_etf",    "value":1,      "reward":100000,"difficulty":"입문"},
    {"id":6,"title":"대형 포트폴리오",   "desc":"주식 평가금액 200만원 이상을 달성하세요.","type":"eval_amount","value":2000000,"reward":500000,"difficulty":"고급"},
]

DICTIONARY={
    "주식":      {"def":"기업이 자금 조달을 위해 발행하는 증서. 보유자는 기업 소유권 일부를 가집니다.","ex":"삼성전자 1주 보유 = 삼성전자의 작은 주주"},
    "ETF":      {"def":"여러 종목을 묶은 펀드를 주식처럼 거래소에서 사고팔 수 있게 만든 상품.","ex":"KODEX 200 = 코스피 200개 종목에 한 번에 분산 투자"},
    "시장가":    {"def":"현재 시장 가격으로 즉시 매매하는 주문. 빠르지만 정확한 가격 보장 안 됨.","ex":"삼성전자 시장가 매수 → 최우선 매도호가에 즉시 체결"},
    "지정가":    {"def":"원하는 가격을 지정해 해당 가격 도달 시 체결되는 주문.","ex":"74,000원 지정가 매수 → 주가가 74,000원 이하일 때만 체결"},
    "분산투자":  {"def":"여러 종목·섹터에 나눠 투자해 리스크를 줄이는 전략.","ex":"IT 33% + 금융 33% + 바이오 33% → 한 섹터 폭락 시 손실 완화"},
    "슬리피지":  {"def":"주문 가격과 실제 체결 가격의 차이. 대량 주문이나 변동성 클 때 발생.","ex":"75,000원 주문 → 호가 잔량 부족으로 75,100원에 체결"},
    "PER":      {"def":"주가수익비율. 주가 ÷ 주당순이익. 낮을수록 저평가 가능성.","ex":"PER 10 = 현재 주가가 연간 이익의 10배"},
    "배당금":    {"def":"기업이 이익 일부를 주주에게 나눠주는 금액.","ex":"삼성전자 주당 361원 배당 × 100주 = 36,100원 수령"},
    "시가총액":  {"def":"현재 주가 × 발행 주식 수. 기업의 시장 가치.","ex":"주가 75,000원 × 60억 주 = 약 450조 원"},
    "포트폴리오":{"def":"투자자가 보유한 여러 금융 자산의 집합.","ex":"삼성전자 40% + NAVER 30% + ETF 30%"},
    "호가":      {"def":"매수자·매도자가 제시하는 가격. 매도호가(ask)와 매수호가(bid)로 구분.","ex":"매도호가 75,100원 / 매수호가 75,000원 → 스프레드 100원"},
    "수익률":    {"def":"(현재가 - 매입가) ÷ 매입가 × 100. 투자 성과 지표.","ex":"75,000원 매수 → 80,000원 = +6.67% 수익"},
}

# 커뮤니티 초기 샘플 게시물
SAMPLE_POSTS = [
    {"id":1,"title":"PER이 낮으면 무조건 좋은 건가요?","body":"주식 공부를 시작했는데 PER이 낮을수록 저평가된 주식이라고 들었어요. 그럼 PER이 낮은 주식을 사면 무조건 오르나요?",
     "author":"주식초보123","time":"2025-05-08 09:23","tags":["PER","가치투자","초보질문"],"views":142,"answers":[
         {"author":"투자전문가A","expert":True,"body":"PER이 낮다고 무조건 좋은 건 아닙니다! PER이 낮은 이유가 성장성이 없거나 리스크가 높기 때문일 수 있어요. 반드시 업종 평균 PER과 비교하고, 실적 추이도 함께 봐야 합니다.","time":"2025-05-08 10:05"}
     ]},
    {"id":2,"title":"ETF와 개별 주식 중 초보자에게 뭐가 나을까요?","body":"주식을 처음 시작하는데 ETF를 살지 개별 종목을 살지 고민입니다. 어떤 게 더 안전한가요?",
     "author":"새내기투자자","time":"2025-05-07 14:11","tags":["ETF","초보질문","분산투자"],"views":289,"answers":[
         {"author":"재테크멘토","expert":True,"body":"초보자라면 ETF를 강력히 추천합니다. 개별 종목은 공부가 많이 필요하지만 ETF는 여러 종목에 자동으로 분산되어 리스크가 낮아요. KODEX 200 같은 지수 추종 ETF로 시작해보세요!","time":"2025-05-07 15:30"}
     ]},
    {"id":3,"title":"분산투자는 몇 개 종목이 적당한가요?","body":"분산투자를 해야 한다고 하는데 종목을 너무 많이 사면 관리가 어려울 것 같아요. 적정 종목 수가 있나요?",
     "author":"투자공부중","time":"2025-05-06 11:45","tags":["분산투자","포트폴리오"],"views":198,"answers":[]},
]


# ──────────────────────────────────────────────
# 4. 세션 초기화
# ──────────────────────────────────────────────
def _init():
    # 키별로 개별 확인 — 새로 추가된 키가 없어도 안전하게 초기화
    defaults = {
        "logged_in":     False,
        "user_name":     "",
        "cash":          10_000_000,
        "bonus_cash":    0,
        "holdings":      {},
        "orders":        [],
        "order_seq":     1,
        "done_missions": set(),
        "prices":        {},
        "price_cache":   {},
        "current_page":  "🏠  포트폴리오",
        "posts":         list(SAMPLE_POSTS),
        "post_seq":      len(SAMPLE_POSTS)+1,
        "chart_history": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    if "kis" not in st.session_state:
        st.session_state.kis = KISApi() if _KIS_ENABLED else None
    st.session_state.initialized = True


# ──────────────────────────────────────────────
# 5. 가격 조회 (병렬 + 캐시)
# ──────────────────────────────────────────────
def _price_one(ticker):
    info=DEMO_STOCKS.get(ticker,{"name":ticker,"base_price":50000,"sector":"기타","desc":""})
    # 세션에 없으면 안전하게 초기화
    if "price_cache"   not in st.session_state: st.session_state.price_cache   = {}
    if "prices"        not in st.session_state: st.session_state.prices         = {}
    if "chart_history" not in st.session_state: st.session_state.chart_history  = {}
    c=st.session_state.price_cache.get(ticker)
    if c and (time.time()-c["ts"])<CACHE_TTL: return c["data"]
    kis=st.session_state.get("kis")
    if kis:
        try:
            d=kis.get_price(ticker)
            d.update({"name":info["name"],"sector":info["sector"],"desc":info.get("desc","")})
            st.session_state.price_cache[ticker]={"data":d,"ts":time.time()}
            st.session_state.prices[ticker]=d["current_price"]
            _update_chart(ticker,d["current_price"])
            return d
        except Exception: pass
    base=info["base_price"]
    prev=st.session_state.prices.get(ticker,int(base*random.uniform(0.97,1.03)))
    cur=max(int(prev*random.uniform(0.992,1.008)),1)
    st.session_state.prices[ticker]=cur
    _update_chart(ticker,cur)
    d={"ticker":ticker,"name":info["name"],"sector":info["sector"],"desc":info.get("desc",""),
       "current_price":cur,"open_price":int(base*random.uniform(0.98,1.02)),
       "high_price":int(cur*random.uniform(1.0,1.015)),"low_price":int(cur*random.uniform(0.985,1.0)),
       "volume":random.randint(300_000,8_000_000),"change_rate":round((cur-base)/base*100,2),"change_price":cur-base}
    st.session_state.price_cache[ticker]={"data":d,"ts":time.time()}
    return d

def _price_bulk(tickers):
    if "price_cache" not in st.session_state: st.session_state.price_cache = {}
    now=time.time()
    if all(t in st.session_state.price_cache and (now-st.session_state.price_cache[t]["ts"])<CACHE_TTL for t in tickers):
        return [st.session_state.price_cache[t]["data"] for t in tickers]
    stale=[t for t in tickers if t not in st.session_state.price_cache or (now-st.session_state.price_cache[t]["ts"])>=CACHE_TTL]
    if stale:
        with ThreadPoolExecutor(max_workers=min(8,len(stale))) as ex:
            list(ex.map(_price_one,stale))
    return [st.session_state.price_cache.get(t,{}).get("data") or _price_one(t) for t in tickers]

def _orderbook(ticker):
    kis=st.session_state.get("kis")
    if kis:
        try: return kis.get_orderbook(ticker)
        except Exception: pass
    price=st.session_state.prices.get(ticker,DEMO_STOCKS.get(ticker,{}).get("base_price",50000))
    tick=max(int(price*0.001),100)
    return {"asks":[{"price":price+tick*i,"qty":random.randint(200,8000)} for i in range(1,6)],
            "bids":[{"price":price-tick*i,"qty":random.randint(200,8000)} for i in range(1,6)],"current":price}

def _update_chart(ticker,price):
    """차트 히스토리 업데이트 (최근 60개 유지)"""
    if ticker not in st.session_state.chart_history:
        # 초기 히스토리 생성 (60분치 시뮬레이션)
        base=DEMO_STOCKS.get(ticker,{}).get("base_price",price)
        hist=[]
        t=datetime.now()-timedelta(minutes=60)
        p=int(base*random.uniform(0.97,1.03))
        for i in range(60):
            p=max(int(p*random.uniform(0.995,1.005)),1)
            hist.append({"time":t+timedelta(minutes=i),"price":p})
        st.session_state.chart_history[ticker]=hist
    h=st.session_state.chart_history[ticker]
    h.append({"time":datetime.now(),"price":price})
    if len(h)>120: st.session_state.chart_history[ticker]=h[-120:]


# ──────────────────────────────────────────────
# 6. 유틸
# ──────────────────────────────────────────────
def _fmt(n): return f"{int(n):,}원"
def _sign(v): return "+" if v>=0 else ""


# ──────────────────────────────────────────────
# 7. 주문 처리
# ──────────────────────────────────────────────
def place_market_order(ticker,side,qty):
    ob=_orderbook(ticker); levels=ob["asks"] if side=="buy" else ob["bids"]
    info=DEMO_STOCKS.get(ticker,{"name":ticker,"sector":"기타"})
    rem,total=qty,0
    for lv in levels:
        if rem<=0: break
        fq=min(rem,lv["qty"]); total+=fq*lv["price"]; rem-=fq
    if rem>0:
        p=levels[-1]["price"] if levels else ob["current"]; total+=rem*p
    avg=round(total/qty)
    if side=="buy":
        cost=avg*qty; avail=st.session_state.cash+st.session_state.bonus_cash
        if avail<cost: return {"ok":False,"msg":f"잔액 부족 (필요 {_fmt(cost)} / 보유 {_fmt(avail)})"}
        if st.session_state.bonus_cash>=cost: st.session_state.bonus_cash-=cost
        else:
            need=cost-st.session_state.bonus_cash; st.session_state.bonus_cash=0; st.session_state.cash-=need
        h=st.session_state.holdings
        if ticker in h:
            pq=h[ticker]["quantity"]; pa=h[ticker]["avg_price"]; nq=pq+qty
            h[ticker]["avg_price"]=round((pa*pq+avg*qty)/nq); h[ticker]["quantity"]=nq
        else:
            h[ticker]={"name":info["name"],"sector":info["sector"],"quantity":qty,"avg_price":avg}
    else:
        h=st.session_state.holdings
        if ticker not in h or h[ticker]["quantity"]<qty:
            have=h[ticker]["quantity"] if ticker in h else 0
            return {"ok":False,"msg":f"보유 수량 부족 (보유 {have}주 / 요청 {qty}주)"}
        h[ticker]["quantity"]-=qty
        if h[ticker]["quantity"]==0: del h[ticker]
        st.session_state.cash+=avg*qty
    st.session_state.orders.insert(0,{"id":st.session_state.order_seq,"ticker":ticker,"name":info["name"],
        "side":side,"type":"market","qty":qty,"price":avg,"status":"filled","time":datetime.now().strftime("%m/%d %H:%M")})
    st.session_state.order_seq+=1
    return {"ok":True,"avg_price":avg,"total":avg*qty,"completed_missions":_check_missions()}

def place_limit_order(ticker,side,qty,limit_price):
    info=DEMO_STOCKS.get(ticker,{"name":ticker,"sector":"기타"})
    if side=="buy":
        avail=st.session_state.cash+st.session_state.bonus_cash
        if avail<limit_price*qty: return {"ok":False,"msg":f"잔액 부족 (예약 {_fmt(limit_price*qty)} / 보유 {_fmt(avail)})"}
    st.session_state.orders.insert(0,{"id":st.session_state.order_seq,"ticker":ticker,"name":info["name"],
        "side":side,"type":"limit","qty":qty,"price":limit_price,"status":"pending","time":datetime.now().strftime("%m/%d %H:%M")})
    st.session_state.order_seq+=1
    return {"ok":True,"msg":f"지정가 {_fmt(limit_price)} 주문 접수 완료"}

def cancel_order(oid):
    for o in st.session_state.orders:
        if o["id"]==oid and o["status"]=="pending": o["status"]="cancelled"

def _check_missions():
    h=st.session_state.holdings; tickers=list(h.keys())
    sectors=set(h[t]["sector"] for t in tickers); etf_cnt=sum(1 for t in tickers if h[t]["sector"]=="ETF")
    eval_amt=sum(st.session_state.price_cache.get(t,{}).get("data",{}).get("current_price",
        DEMO_STOCKS.get(t,{}).get("base_price",0))*h[t]["quantity"] for t in tickers)
    newly=[]
    for m in MISSIONS:
        if m["id"] in st.session_state.done_missions: continue
        ok=(m["type"]=="min_tickers" and len(tickers)>=m["value"]) or \
           (m["type"]=="min_sectors" and len(sectors)>=m["value"]) or \
           (m["type"]=="has_etf"     and etf_cnt>=m["value"]) or \
           (m["type"]=="eval_amount" and eval_amt>=m["value"])
        if ok:
            st.session_state.done_missions.add(m["id"]); st.session_state.bonus_cash+=m["reward"]; newly.append(m)
    return newly


# ──────────────────────────────────────────────
# 8. 주가 차트 — TradingView Lightweight Charts
# ──────────────────────────────────────────────
def _render_tv_chart(ticker, chart_type="candle"):
    """TradingView Lightweight Charts 렌더링"""
    import json

    hist = st.session_state.chart_history.get(ticker, [])
    if len(hist) < 2:
        st.caption("차트 데이터 수집 중...")
        return

    df = pd.DataFrame(hist)
    cur_price = df["price"].iloc[-1]
    first_price = df["price"].iloc[0]
    is_up = cur_price >= first_price
    up_color   = "#ef5350"   # 트레이딩뷰 상승색 (빨강)
    down_color = "#26a69a"   # 트레이딩뷰 하락색 (초록)
    line_color = up_color if is_up else down_color

    if chart_type == "candle":
        # 1분 단위 OHLC
        df["group"] = df["time"].dt.floor("1min")
        ohlc = df.groupby("group")["price"].agg(
            open="first", high="max", low="min", close="last"
        ).reset_index()
        series_data = [
            {"time": int(row["group"].timestamp()),
             "open": row["open"], "high": row["high"],
             "low": row["low"],   "close": row["close"]}
            for _, row in ohlc.iterrows()
        ]
        series_json = json.dumps(series_data)
        series_js = f"""
        const series = chart.addCandlestickSeries({{
            upColor:         '{up_color}',
            downColor:       '{down_color}',
            borderUpColor:   '{up_color}',
            borderDownColor: '{down_color}',
            wickUpColor:     '{up_color}',
            wickDownColor:   '{down_color}',
        }});
        series.setData({series_json});
        """
    else:
        # 라인 차트
        series_data = [
            {"time": int(row["time"].timestamp()), "value": row["price"]}
            for _, row in df.iterrows()
        ]
        series_json = json.dumps(series_data)
        series_js = f"""
        const series = chart.addAreaSeries({{
            lineColor:       '{line_color}',
            topColor:        '{line_color}33',
            bottomColor:     '{line_color}00',
            lineWidth:       2,
            crosshairMarkerVisible: true,
            crosshairMarkerRadius:  4,
        }});
        series.setData({series_json});
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#131722; }}
  #tv-chart {{ width:100%; height:380px; }}
  .toolbar {{
      display:flex; align-items:center; gap:8px;
      background:#1e222d; padding:8px 14px;
      border-bottom:1px solid #2a2e39;
      font-family:'Noto Sans KR',sans-serif;
  }}
  .ticker-name {{ color:#d1d4dc; font-size:15px; font-weight:700; }}
  .price-now   {{ color:#d1d4dc; font-size:14px; margin-left:8px; font-family:'JetBrains Mono',monospace; }}
  .price-chg   {{ font-size:13px; margin-left:4px; font-family:'JetBrains Mono',monospace; }}
  .up   {{ color:{up_color}; }}
  .down {{ color:{down_color}; }}
  #legend {{
      position:absolute; top:44px; left:12px;
      color:#d1d4dc; font-size:12px; font-family:'JetBrains Mono',monospace;
      pointer-events:none; z-index:10;
      background:rgba(19,23,34,0.85); padding:4px 8px; border-radius:4px;
  }}
</style>
</head>
<body>
<div class="toolbar">
  <span class="ticker-name">{ticker}</span>
  <span class="price-now">{cur_price:,}원</span>
  <span class="price-chg {'up' if is_up else 'down'}">
    {'▲' if is_up else '▼'} {abs(cur_price - first_price):,}원
    ({'+' if is_up else ''}{(cur_price-first_price)/first_price*100:.2f}%)
  </span>
</div>
<div style="position:relative;">
  <div id="tv-chart"></div>
  <div id="legend"></div>
</div>
<script>
const chart = LightweightCharts.createChart(document.getElementById('tv-chart'), {{
    width:  document.getElementById('tv-chart').clientWidth,
    height: 380,
    layout: {{
        background:  {{ color: '#131722' }},
        textColor:   '#d1d4dc',
        fontSize:    11,
        fontFamily:  'JetBrains Mono, monospace',
    }},
    grid: {{
        vertLines:   {{ color: '#1e222d' }},
        horzLines:   {{ color: '#1e222d' }},
    }},
    crosshair: {{
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {{ color:'#4a90e2', labelBackgroundColor:'#2962ff' }},
        horzLine: {{ color:'#4a90e2', labelBackgroundColor:'#2962ff' }},
    }},
    rightPriceScale: {{
        borderColor: '#2a2e39',
        scaleMargins: {{ top:0.1, bottom:0.1 }},
    }},
    timeScale: {{
        borderColor:       '#2a2e39',
        timeVisible:       true,
        secondsVisible:    false,
        tickMarkFormatter: (t) => {{
            const d = new Date(t * 1000);
            return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
        }},
    }},
    handleScroll:   true,
    handleScale:    true,
}});

{series_js}

// 크로스헤어 범례
const legend = document.getElementById('legend');
chart.subscribeCrosshairMove(param => {{
    if (!param.time || !param.seriesData.size) {{
        legend.style.display = 'none'; return;
    }}
    legend.style.display = 'block';
    const data = param.seriesData.values().next().value;
    const d = new Date(param.time * 1000);
    const timeStr = d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
    if (data.open !== undefined) {{
        legend.innerHTML = timeStr +
            '  O <span style="color:{up_color}">' + data.open.toLocaleString() + '</span>' +
            '  H <span style="color:{up_color}">' + data.high.toLocaleString() + '</span>' +
            '  L <span style="color:{down_color}">' + data.low.toLocaleString() + '</span>' +
            '  C <span style="color:#d1d4dc">' + data.close.toLocaleString() + '</span>';
    }} else {{
        legend.innerHTML = timeStr + '  ' + data.value.toLocaleString() + '원';
    }}
}});

// 최신 데이터로 스크롤
chart.timeScale().scrollToRealTime();

// 반응형 리사이즈
window.addEventListener('resize', () => {{
    chart.applyOptions({{ width: document.getElementById('tv-chart').clientWidth }});
}});
</script>
</body>
</html>
"""
    st.components.v1.html(html, height=430, scrolling=False)


# ──────────────────────────────────────────────
# 9. 화면 렌더링
# ──────────────────────────────────────────────
def page_portfolio():
    st.markdown("## 🏠 내 포트폴리오")
    h=st.session_state.holdings; holdings_data=[]; total_eval=total_cost=0
    if h:
        prices=_price_bulk(list(h.keys())); pm={p["ticker"]:p for p in prices}
        for ticker,info in h.items():
            p=pm.get(ticker) or _price_one(ticker)
            cur=p["current_price"]; ea=cur*info["quantity"]; ca=info["avg_price"]*info["quantity"]
            profit=ea-ca; rate=profit/ca*100 if ca else 0
            holdings_data.append({"ticker":ticker,"name":info["name"],"sector":info["sector"],
                "quantity":info["quantity"],"avg_price":info["avg_price"],"cur_price":cur,
                "eval_amt":ea,"profit":profit,"rate":rate})
            total_eval+=ea; total_cost+=ca
    tp=total_eval-total_cost; tr=tp/total_cost*100 if total_cost else 0
    ta=st.session_state.cash+st.session_state.bonus_cash+total_eval

    c1,c2,c3,c4=st.columns(4)
    for col,label,val,sub in [
        (c1,"💰 총 자산",_fmt(ta),""),
        (c2,"🏦 가용 현금",_fmt(st.session_state.cash+st.session_state.bonus_cash),
         f"보너스 {_fmt(st.session_state.bonus_cash)} 포함" if st.session_state.bonus_cash else ""),
        (c3,"📦 주식 평가액",_fmt(total_eval),""),
        (c4,"📈 평가 손익",f"{_sign(tp)}{_fmt(tp)}",f"{_sign(tr)}{tr:.2f}%"),
    ]:
        sc="up" if "+" in sub else "down" if "-" in sub else "neutral"
        col.markdown(f'<div class="stat-card"><div class="stat-label">{label}</div>'
                     f'<div class="stat-value">{val}</div>'
                     f'{"<div class=stat-sub "+sc+">"+sub+"</div>" if sub else ""}</div>',unsafe_allow_html=True)
    st.markdown("<br>",unsafe_allow_html=True)

    if not holdings_data:
        st.info("💡 아직 보유 종목이 없습니다. **시장** 탭에서 첫 투자를 시작해보세요!")
        return
    cp,cb=st.columns(2)
    with cp:
        st.markdown("##### 섹터 비중")
        df=pd.DataFrame(holdings_data).groupby("sector")["eval_amt"].sum().reset_index()
        fig=px.pie(df,names="sector",values="eval_amt",hole=0.45,
                   color_discrete_sequence=["#4a90e2","#ff6b6b","#ffd166","#06d6a0","#118ab2","#ef476f"])
        fig.update_traces(textposition="inside",textinfo="percent+label")
        fig.update_layout(margin=dict(t=10,b=10,l=10,r=10),height=260,showlegend=False,paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig,use_container_width=True)
    with cb:
        st.markdown("##### 종목별 손익률")
        df2=pd.DataFrame(holdings_data).sort_values("rate")
        fig2=go.Figure(go.Bar(x=df2["rate"],y=df2["name"],orientation="h",
            marker_color=["#ff5858" if r>=0 else "#4da6ff" for r in df2["rate"]],
            text=[f"{_sign(r)}{r:.2f}%" for r in df2["rate"]],textposition="outside"))
        fig2.update_layout(xaxis_title="손익률 (%)",margin=dict(t=10,b=10,l=10,r=70),
                           height=260,plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2,use_container_width=True)

    st.markdown("##### 보유 종목 상세")
    for hi in holdings_data:
        r=hi["rate"]
        with st.expander(f"{'🔴' if r>=0 else '🔵'} **{hi['name']}** ({hi['ticker']})  ·  {_sign(r)}{r:.2f}%"):
            a,b,c,d=st.columns(4)
            a.metric("보유 수량",f"{hi['quantity']}주")
            b.metric("평균 매입가",_fmt(hi['avg_price']))
            c.metric("현재가",_fmt(hi['cur_price']))
            d.metric("평가 손익",f"{_sign(hi['profit'])}{_fmt(hi['profit'])}",f"{_sign(r)}{r:.2f}%")


def page_market():
    st.markdown("## 📊 시장")
    c1,c2=st.columns([3,1])
    with c1: keyword=st.text_input("🔍 종목 검색",placeholder="종목명 또는 코드 입력",label_visibility="collapsed")
    with c2:
        sectors=["전체"]+sorted(set(v["sector"] for v in DEMO_STOCKS.values()))
        sel_sec=st.selectbox("섹터",sectors,label_visibility="collapsed")
    with st.spinner("시세 불러오는 중..."): all_stocks=_price_bulk(list(DEMO_STOCKS.keys()))
    if keyword: all_stocks=[s for s in all_stocks if keyword in s["name"] or keyword in s["ticker"]]
    if sel_sec!="전체": all_stocks=[s for s in all_stocks if s["sector"]==sel_sec]
    mode="🟢 실제 API" if _KIS_ENABLED else "🟡 데모 데이터"
    st.caption(f"📌 총 {len(all_stocks)}개 종목 · {mode} · {CACHE_TTL}초 캐시")
    st.divider()
    for col,label in zip(st.columns([3,2,2,2,1]),["종목명","현재가","등락률","거래량",""]):
        col.markdown(f"<small style='color:gray;font-weight:600'>{label}</small>",unsafe_allow_html=True)
    for s in all_stocks:
        r=s["change_rate"]; cls="up" if r>=0 else "down"; arr="▲" if r>=0 else "▼"
        sc=st.columns([3,2,2,2,1])
        sc[0].markdown(f"**{s['name']}**  \n`{s['ticker']}` · {s['sector']}")
        sc[1].markdown(f"<span style='font-family:JetBrains Mono,monospace;font-weight:600'>{_fmt(s['current_price'])}</span>",unsafe_allow_html=True)
        sc[2].markdown(f"<span class='{cls}'>{arr} {abs(r):.2f}%</span>",unsafe_allow_html=True)
        sc[3].markdown(f"<small>{s['volume']:,}</small>",unsafe_allow_html=True)
        with sc[4]:
            if st.button("거래",key=f"mkt_{s['ticker']}"):
                st.session_state["sel_ticker"]=s["ticker"]
                st.session_state["current_page"]="💹  거래"
                st.rerun()
        st.divider()


def page_trading():
    st.markdown("## 💹 거래")
    opts={f"{v['name']} ({k})":k for k,v in DEMO_STOCKS.items()}
    dk=st.session_state.get("sel_ticker","005930")
    dl=next((l for l,t in opts.items() if t==dk),list(opts.keys())[0])
    selected=st.selectbox("종목 선택",list(opts.keys()),index=list(opts.keys()).index(dl))
    ticker=opts[selected]; info=DEMO_STOCKS.get(ticker,{})

    p=_price_one(ticker); ob=_orderbook(ticker)
    cur=p["current_price"]; rate=p["change_rate"]
    arr="▲" if rate>=0 else "▼"; cls="up" if rate>=0 else "down"

    # 현재가 헤더
    st.markdown(f'<div class="stat-card" style="margin-bottom:16px">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="stat-label">{info.get("sector","")} · {info.get("desc","")}</div>'
                f'<div style="font-size:13px;color:#7fa8cc;margin-bottom:6px">{ticker}</div>'
                f'<div style="font-size:30px;font-weight:900;font-family:JetBrains Mono,monospace">{_fmt(cur)}</div>'
                f'<div class="stat-sub {cls}">{arr} {abs(rate):.2f}%</div></div>'
                f'<div style="text-align:right;color:#7fa8cc;font-size:12px">'
                f'<div>시가 {_fmt(p["open_price"])}</div><div>고가 {_fmt(p["high_price"])}</div>'
                f'<div>저가 {_fmt(p["low_price"])}</div><div>거래량 {p["volume"]:,}</div>'
                f'</div></div></div>',unsafe_allow_html=True)

    # ── 주가 차트 (TradingView 스타일) ────────────────
    st.markdown("##### 📈 주가 차트")
    _, type_col = st.columns([5, 1])
    with type_col:
        chart_type = st.radio("차트 유형", ["캔들", "라인"], label_visibility="collapsed")
    ct = "candle" if chart_type == "캔들" else "line"
    _render_tv_chart(ticker, ct)

    st.divider()

    # ── 호가창 + 주문폼 ──────────────────────────────
    co,cf=st.columns([1,1])
    with co:
        st.markdown("##### 호가창")
        for ask in reversed(ob["asks"]):
            st.markdown(f'<div class="ask-row"><span style="color:#ff5858">{ask["price"]:,}원</span>'
                        f'<span style="color:#999">{ask["qty"]:,}주</span></div>',unsafe_allow_html=True)
        st.markdown(f'<div class="cur-row"><span>현재가</span><span>{cur:,}원</span></div>',unsafe_allow_html=True)
        for bid in ob["bids"]:
            st.markdown(f'<div class="bid-row"><span style="color:#4da6ff">{bid["price"]:,}원</span>'
                        f'<span style="color:#999">{bid["qty"]:,}주</span></div>',unsafe_allow_html=True)

    with cf:
        st.markdown("##### 주문")
        avail=st.session_state.cash+st.session_state.bonus_cash
        side=st.radio("",["매수","매도"],horizontal=True,label_visibility="collapsed")
        side_en="buy" if side=="매수" else "sell"
        ot=st.radio("주문 유형",["시장가","지정가"],horizontal=True)
        qty=st.number_input("수량 (주)",min_value=1,max_value=10000,value=1,step=1)
        lp=st.number_input("지정 가격 (원)",min_value=1,value=cur,step=100) if ot=="지정가" else None
        est=(lp if lp else cur)*qty
        if side_en=="buy":
            st.markdown(f'<div class="toast">💰 예상 매수 금액: <b>{_fmt(est)}</b><br>'
                        f'🏦 가용 현금: <b>{_fmt(avail)}</b>'
                        f'{"<br>⚠️ <span style=color:#ff8080>잔액 부족</span>" if avail<est else ""}</div>',unsafe_allow_html=True)
        else:
            held=st.session_state.holdings.get(ticker,{}).get("quantity",0)
            avg_p=st.session_state.holdings.get(ticker,{}).get("avg_price",0)
            pp=(cur-avg_p)*qty if avg_p else 0
            st.markdown(f'<div class="toast">📦 보유 수량: <b>{held}주</b>'
                        f'{"<br>💵 예상 매도: <b>"+_fmt(est)+"</b>" if held>=qty else "<br>⚠️ <span style=color:#ff8080>보유 수량 부족</span>"}'
                        f'{"<br>📈 예상 손익: <b style=color:"+("#ff5858" if pp>=0 else "#4da6ff")+">"+_sign(pp)+_fmt(pp)+"</b>" if held>=qty and avg_p else ""}'
                        f'</div>',unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        if st.button(f"{'🔴 매수' if side_en=='buy' else '🔵 매도'} 주문 ({qty}주)",use_container_width=True,type="primary"):
            res=place_market_order(ticker,side_en,qty) if ot=="시장가" \
                else place_limit_order(ticker,side_en,qty,float(lp))
            if res["ok"]:
                if ot=="시장가":
                    st.success(f"✅ 체결 완료! 평균 {_fmt(res['avg_price'])} · 총 {_fmt(res['total'])}")
                    for m in res.get("completed_missions",[]):
                        st.balloons(); st.success(f"🎯 미션 달성! **{m['title']}** → +{_fmt(m['reward'])} 보너스!")
                else: st.info(res["msg"])
                st.rerun()
            else: st.error(res["msg"])

    st.divider(); st.markdown("##### 이 종목 주문 내역")
    tor=[o for o in st.session_state.orders if o["ticker"]==ticker]
    if not tor: st.caption("주문 내역이 없습니다.")
    else:
        for o in tor[:8]:
            ico={"filled":"✅","pending":"⏳","cancelled":"❌"}.get(o["status"],"")
            c1,c2=st.columns([5,1])
            c1.caption(f"{ico} {'매수' if o['side']=='buy' else '매도'} · {o['type']} · {o['qty']}주 · {_fmt(o['price'])} · {o['time']}")
            with c2:
                if o["status"]=="pending":
                    if st.button("취소",key=f"cancel_{o['id']}"): cancel_order(o["id"]); st.rerun()


def page_mission():
    st.markdown("## 🎯 미션")
    st.caption("미션을 완료하면 모의투자에 사용 가능한 **보너스 캐시**를 받습니다.")
    done=st.session_state.done_missions; n=len(done)
    rs=sum(m["reward"] for m in MISSIONS if m["id"] in done)
    st.markdown(f"### 진행 현황: {n} / {len(MISSIONS)} 완료")
    st.progress(n/len(MISSIONS))
    if rs: st.success(f"🏆 총 획득 보상: **{_fmt(rs)}** (보너스 캐시 적립 완료)")
    st.divider()
    for m in MISSIONS:
        is_done=m["id"] in done; css="mission-done" if is_done else "mission-card"
        badge=f'<span class="badge badge-완료">완료</span>' if is_done else f'<span class="badge badge-{m["difficulty"]}">{m["difficulty"]}</span>'
        extra=f'<span style="float:right;color:#1e7e34">+{_fmt(m["reward"])}</span>' if is_done else \
              f'<span style="color:#1e7e34;font-weight:600;margin-top:8px;display:block">🎁 보상: {_fmt(m["reward"])}</span>'
        st.markdown(f'<div class="{css}">{badge}<strong style="font-size:16px">{m["title"]}</strong>{extra if is_done else ""}<br>'
                    f'<span style="color:#666;font-size:14px">{m["desc"]}</span>{extra if not is_done else ""}</div>',unsafe_allow_html=True)


def page_dictionary():
    st.markdown("## 📖 투자 사전")
    st.caption("투자하면서 만나는 금융 용어를 쉽게 찾아보세요.")
    search=st.text_input("🔍 용어 검색",placeholder="예: ETF, 분산투자, PER, 슬리피지…")
    results={k:v for k,v in DICTIONARY.items() if search in k} if search else DICTIONARY
    if search and not results:
        st.warning(f"**'{search}'** 에 해당하는 용어가 없습니다.")
        if st.button(f"🤖 AI에게 '{search}' 설명 요청"):
            with st.spinner("설명 생성 중…"):
                try:
                    res=requests.post("https://api.anthropic.com/v1/messages",
                        headers={"Content-Type":"application/json"},
                        json={"model":"claude-sonnet-4-20250514","max_tokens":500,
                              "messages":[{"role":"user","content":f"금융/투자 용어 '{search}'을 초보 투자자도 이해하기 쉽게 한국어로 **정의**, **예시**, **주의사항** 형식으로 설명해주세요."}]},
                        timeout=20)
                    if res.status_code==200:
                        text=res.json()["content"][0]["text"]
                        st.markdown(f'<div class="dict-card" style="border-color:#06d6a0">'
                                    f'<div style="font-size:16px;font-weight:700;margin-bottom:8px">🤖 AI 설명: {search}</div>'
                                    f'<div style="font-size:14px;line-height:1.8">{text.replace(chr(10),"<br>")}</div></div>',unsafe_allow_html=True)
                except Exception: st.info("🔌 인터넷 연결이 필요합니다.")
        return
    cols=st.columns(2)
    for i,(term,info) in enumerate(results.items()):
        with cols[i%2]:
            st.markdown(f'<div class="dict-card"><div style="font-size:16px;font-weight:700;margin-bottom:6px">📌 {term}</div>'
                        f'<div style="font-size:14px;color:#334;margin-bottom:8px">{info["def"]}</div>'
                        f'<div style="font-size:13px;color:#555;background:#fff;padding:8px;border-radius:6px"><b>예시:</b> {info["ex"]}</div></div>',unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 커뮤니티 페이지 (NEW)
# ──────────────────────────────────────────────
def page_community():
    st.markdown("## 💬 커뮤니티")
    st.caption("주식 초보자가 전문가에게 질문하고 답변받는 공간입니다.")

    tab_list, tab_write = st.tabs(["📋 질문 목록", "✏️ 질문하기"])

    # ── 질문 목록 탭 ──────────────────────────────
    with tab_list:
        # 검색 + 정렬
        sc1, sc2 = st.columns([3,1])
        with sc1:
            kw = st.text_input("🔍 검색", placeholder="궁금한 키워드를 검색하세요", label_visibility="collapsed")
        with sc2:
            sort = st.selectbox("정렬", ["최신순","조회순","답변많은순"], label_visibility="collapsed")

        posts = list(st.session_state.posts)
        if kw:
            posts=[p for p in posts if kw in p["title"] or kw in p["body"]]
        if sort=="조회순":   posts=sorted(posts,key=lambda x:x["views"],reverse=True)
        elif sort=="답변많은순": posts=sorted(posts,key=lambda x:len(x["answers"]),reverse=True)
        else: posts=sorted(posts,key=lambda x:x["id"],reverse=True)

        st.markdown(f"**총 {len(posts)}개 질문**")
        st.divider()

        for post in posts:
            ans_cnt = len(post["answers"])
            ans_badge = f'<span style="background:#e8f0fe;color:#4a90e2;padding:2px 8px;border-radius:12px;font-size:11px">💬 답변 {ans_cnt}개</span>'
            hot_badge = '<span class="tag-hot">🔥 HOT</span>' if post["views"]>150 else ""

            # 태그
            tags_html = "".join([f'<span class="tag">{t}</span>' for t in post.get("tags",[])])

            with st.expander(f"{'✅' if ans_cnt>0 else '❓'} {post['title']}  {hot_badge}"):
                st.markdown(f'<div class="post-meta">👤 {post["author"]} · 🕐 {post["time"]} · 👁️ {post["views"]}회 {ans_badge}</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="post-body">{post["body"]}</div>',unsafe_allow_html=True)
                if tags_html: st.markdown(tags_html,unsafe_allow_html=True)

                # 답변 목록
                if post["answers"]:
                    st.markdown("---")
                    st.markdown("**💡 답변**")
                    for ans in post["answers"]:
                        expert_html = '<span class="expert-badge">⭐ 전문가</span>' if ans.get("expert") else ""
                        st.markdown(f'<div class="answer-card">'
                                    f'<div style="font-size:12px;color:#888;margin-bottom:6px">'
                                    f'{expert_html} <b>{ans["author"]}</b> · {ans["time"]}</div>'
                                    f'<div style="font-size:14px;line-height:1.7;color:#333">{ans["body"]}</div>'
                                    f'</div>',unsafe_allow_html=True)

                # 답변 작성
                st.markdown("**답변 달기**")
                ans_key = f"ans_{post['id']}"
                ans_text = st.text_area("답변을 입력하세요", key=ans_key, height=80, label_visibility="collapsed",
                                        placeholder="알고 있는 내용을 친절하게 공유해주세요!")
                col_btn1, col_btn2 = st.columns([1,4])
                with col_btn1:
                    if st.button("답변 등록", key=f"ans_btn_{post['id']}", type="primary"):
                        if ans_text.strip():
                            post["answers"].append({
                                "author": st.session_state.user_name,
                                "expert": False,
                                "body":   ans_text.strip(),
                                "time":   datetime.now().strftime("%Y-%m-%d %H:%M"),
                            })
                            post["views"] += 1
                            st.success("답변이 등록되었습니다!")
                            st.rerun()
                        else:
                            st.warning("답변 내용을 입력해주세요.")

    # ── 질문 작성 탭 ──────────────────────────────
    with tab_write:
        st.markdown("### ✏️ 새 질문 작성")
        st.caption("궁금한 점을 자유롭게 질문하세요. 전문가와 다른 투자자들이 답변해드립니다!")

        q_title = st.text_input("제목", placeholder="예) ETF와 주식의 차이가 뭔가요?", max_chars=100)
        q_body  = st.text_area("내용", placeholder="궁금한 점을 자세히 적어주세요.\n예) 처음 주식을 시작하려는데...",
                               height=150)
        q_tags_input = st.text_input("태그 (쉼표로 구분)", placeholder="예) ETF, 초보질문, 분산투자")

        col1, col2 = st.columns([1,5])
        with col1:
            if st.button("질문 등록", type="primary", use_container_width=True):
                if not q_title.strip():
                    st.warning("제목을 입력해주세요.")
                elif not q_body.strip():
                    st.warning("내용을 입력해주세요.")
                else:
                    tags = [t.strip() for t in q_tags_input.split(",") if t.strip()] if q_tags_input else []
                    new_post = {
                        "id":      st.session_state.post_seq,
                        "title":   q_title.strip(),
                        "body":    q_body.strip(),
                        "author":  st.session_state.user_name,
                        "time":    datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "tags":    tags,
                        "views":   0,
                        "answers": [],
                    }
                    st.session_state.posts.append(new_post)
                    st.session_state.post_seq += 1
                    st.success("✅ 질문이 등록되었습니다! 질문 목록 탭에서 확인하세요.")
                    st.balloons()

        st.divider()
        st.markdown("##### 💡 좋은 질문 작성 팁")
        st.markdown("""
        - 질문은 **구체적**일수록 좋은 답변을 받을 수 있어요
        - 어떤 상황에서 궁금증이 생겼는지 **맥락을 함께** 적어주세요
        - 이미 찾아본 내용이 있다면 **어떤 부분이 이해 안 됐는지** 적어주세요
        - 태그를 달면 전문가가 더 빠르게 찾아볼 수 있어요
        """)


# ──────────────────────────────────────────────
# 10. 로그인
# ──────────────────────────────────────────────
def page_login():
    _,mid,_=st.columns([1,2,1])
    with mid:
        st.markdown('<div style="text-align:center;padding:30px 0 10px">'
                    '<div style="font-size:48px">📈</div>'
                    '<div style="font-size:28px;font-weight:900;color:#0f2440;margin:8px 0">모의투자 플랫폼</div>'
                    '<div style="color:#666;margin-bottom:24px">실시간 시장 데이터로 배우는 스마트 투자 교육</div>'
                    '</div>',unsafe_allow_html=True)
        t1,t2=st.tabs(["🔑 로그인","✍️ 회원가입"])
        with t1:
            email=st.text_input("이메일",key="li_email")
            pw=st.text_input("비밀번호",type="password",key="li_pw")
            if st.button("로그인",use_container_width=True,type="primary"):
                if email and pw:
                    st.session_state.logged_in=True
                    st.session_state.user_name=email.split("@")[0]
                    st.rerun()
                else: st.warning("이메일과 비밀번호를 입력해주세요.")
        with t2:
            re=st.text_input("이메일",key="rg_email"); rn=st.text_input("닉네임",key="rg_nick")
            rp=st.text_input("비밀번호",type="password",key="rg_pw")
            rp2=st.text_input("비밀번호 확인",type="password",key="rg_pw2")
            if st.button("회원가입",use_container_width=True,type="primary"):
                if rp!=rp2: st.error("비밀번호가 일치하지 않습니다.")
                elif not all([re,rn,rp]): st.warning("모든 항목을 입력해주세요.")
                else:
                    st.session_state.logged_in=True; st.session_state.user_name=rn; st.rerun()
        st.divider()
        st.caption("⚠️ 이 플랫폼은 교육용 모의투자 서비스입니다. 실제 금전 거래가 발생하지 않습니다.")


# ──────────────────────────────────────────────
# 11. 메인
# ──────────────────────────────────────────────
_init()

if not st.session_state.logged_in:
    page_login(); st.stop()

with st.sidebar:
    st.markdown(f'<div style="padding:12px 0 6px">'
                f'<div style="font-size:18px;font-weight:700">📈 모의투자</div>'
                f'<div style="font-size:13px;color:#8eb4d8;margin-top:2px">👤 {st.session_state.user_name}</div>'
                f'</div>',unsafe_allow_html=True)
    st.markdown(f'<span class="api-{"real" if _KIS_ENABLED else "demo"}">{"🟢 실제 API 연동" if _KIS_ENABLED else "🟡 데모 모드"}</span>',unsafe_allow_html=True)
    ct=st.session_state.cash+st.session_state.bonus_cash
    st.markdown(f'<div style="background:#0d1f35;border-radius:10px;padding:12px 14px;margin:8px 0">'
                f'<div style="font-size:11px;color:#7fa8cc">가용 현금</div>'
                f'<div style="font-size:18px;font-weight:700;font-family:JetBrains Mono,monospace">{_fmt(ct)}</div>'
                f'{"<div style=font-size:11px;color:#06d6a0>보너스 "+_fmt(st.session_state.bonus_cash)+" 포함</div>" if st.session_state.bonus_cash else ""}'
                f'</div>',unsafe_allow_html=True)
    dn=len(st.session_state.done_missions)
    st.markdown(f"<div style='font-size:12px;color:#7fa8cc;padding:4px 0'>🎯 미션 {dn}/{len(MISSIONS)} 완료</div>",unsafe_allow_html=True)
    # 커뮤니티 새 질문 수 표시
    unanswered=sum(1 for p in st.session_state.posts if len(p["answers"])==0)
    if unanswered: st.markdown(f"<div style='font-size:12px;color:#ffd166;padding:2px 0'>💬 미답변 질문 {unanswered}개</div>",unsafe_allow_html=True)
    st.divider()
    PAGES=["🏠  포트폴리오","📊  시장","💹  거래","🎯  미션","📖  투자 사전","💬  커뮤니티"]
    cur=st.session_state.get("current_page","🏠  포트폴리오")
    page=st.radio("메뉴",PAGES,index=PAGES.index(cur) if cur in PAGES else 0,label_visibility="collapsed")
    st.session_state["current_page"]=page
    st.divider()
    if st.button("🔄 새로고침",use_container_width=True):
        st.session_state.price_cache={}; st.rerun()
    if st.button("🚪 로그아웃",use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    if not _KIS_ENABLED:
        st.markdown("<br>",unsafe_allow_html=True)
        st.caption("💡 API 키를 입력하면\n실제 시세로 전환됩니다")

if   "포트폴리오" in page: page_portfolio()
elif "시장"       in page: page_market()
elif "거래"       in page: page_trading()
elif "미션"       in page: page_mission()
elif "투자 사전"  in page: page_dictionary()
elif "커뮤니티"   in page: page_community()
