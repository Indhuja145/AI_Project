import os, re, json, logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger=logging.getLogger('threadsense')

SECRET = os.getenv('JWT_SECRET', 'demo-secret-change-me')
ALGORITHM = 'HS256'
# PBKDF2 avoids bcrypt backend incompatibilities on newer Python/bcrypt builds.
pwd = CryptContext(schemes=['pbkdf2_sha256'], deprecated='auto')
oauth2 = OAuth2PasswordBearer(tokenUrl='/api/auth/login')

ASPECTS = {
    'Fabric Quality': ['fabric', 'stitch', 'stitching', 'durable', 'durability', 'shrink', 'thread', 'tear'],
    'Color & Appearance': ['color', 'colour', 'fade', 'faded', 'print', 'pattern', 'appearance'],
    'Comfort & Fit': ['comfort', 'comfortable', 'soft', 'texture', 'fit', 'size', 'tight', 'loose'],
    'Product Design': ['design', 'style', 'pattern', 'outdated', 'look'],
    'Material Quality': ['material', 'cotton', 'silk', 'polyester', 'quality'],
    'Delivery': ['delivery', 'delivered', 'late', 'delay', 'courier', 'shipping'],
    'Packaging': ['package', 'packaging', 'damaged', 'box', 'missing'],
    'Pricing': ['price', 'pricing', 'expensive', 'overpriced', 'worth', 'cost'],
    'Customer Service': ['support', 'return', 'refund', 'service', 'response'],
}
EMOTION_WORDS = {
    'Happy':['love','happy','excellent','perfect','comfortable','beautiful','satisfied'],
    'Excited':['excited','gorgeous','amazing','wow','premium'],
    'Disappointed':['disappointed','expected','overpriced','shrunk','faded','late'],
    'Angry':['worst','unacceptable','refund','wrong','damaged','fraud'],
}
NEGATIVE = ['bad', 'poor', 'worst', 'faded', 'fade', 'late', 'delay', 'damaged', 'tear', 'shrunk', 'expensive', 'wrong', 'missing', 'uncomfortable', 'disappointed', 'defect', 'outdated', 'tight']
POSITIVE = ['good', 'great', 'excellent', 'love', 'beautiful', 'comfortable', 'soft', 'durable', 'perfect', 'fast', 'reasonable', 'premium', 'quality', 'happy']

def has_term(text, term):
    return re.search(r'\b'+re.escape(term)+r'\b', text) is not None

PRODUCTS = [
 {'id':'p1','name':'Monsoon Cotton Saree','category':'Sarees','price':2499,'rating':4.2,'seasonal_tags':['Summer','Festive Season'],'image':'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=600&q=80'},
 {'id':'p2','name':'Heritage Silk Kurta','category':'Kurtas','price':3299,'rating':4.6,'seasonal_tags':['Wedding Season','Festive Season'],'image':'https://images.unsplash.com/photo-1610030469668-8e9f641aafc8?auto=format&fit=crop&w=600&q=80'},
 {'id':'p3','name':'Indigo Linen Shirt','category':'Shirts','price':1799,'rating':3.8,'seasonal_tags':['Summer','Spring'],'image':'https://images.unsplash.com/photo-1603252110481-7ba873bf42ab?auto=format&fit=crop&w=600&q=80'},
 {'id':'p4','name':'Festive Banarasi Dupatta','category':'Accessories','price':1599,'rating':4.4,'seasonal_tags':['Festive Season','Wedding Season'],'image':'https://images.unsplash.com/photo-1583391733956-6c78276477e2?auto=format&fit=crop&w=600&q=80'}
]
RAW_REVIEWS = [
 ('p1','The fabric is comfortable and beautiful, but the color faded after two washes.','Summer','2026-07-03'),
 ('p1','Lovely print and soft cotton. Stitching is durable.','Festive Season','2026-07-10'),
 ('p1','Size was tight and color faded quickly.','Summer','2026-08-02'),
 ('p2','Excellent silk quality and perfect fit. Delivery was fast.','Wedding Season','2026-06-21'),
 ('p2','Beautiful design, premium material and comfortable texture.','Festive Season','2026-07-18'),
 ('p3','Good linen but the shirt shrunk after washing and the color faded.','Summer','2026-06-14'),
 ('p3','Overpriced for the material. Delivery was late and packaging damaged.','Spring','2026-05-28'),
 ('p4','Gorgeous pattern and quality material. Worth the price.','Wedding Season','2026-07-26'),
 ('p4','The package arrived late but the design is beautiful.','Festive Season','2026-08-05')
]

def analyze(text):
    low = text.lower(); score = sum(has_term(low,w) for w in NEGATIVE) - sum(has_term(low,w) for w in POSITIVE)
    sentiment = 'Negative' if score > 0 else ('Positive' if score < 0 else 'Neutral')
    aspects = []
    for name, words in ASPECTS.items():
        hits = [m.start() for w in words for m in re.finditer(r'\b'+re.escape(w)+r'\b', low)]
        if hits:
            # Use the sentence containing the aspect so mixed reviews remain explainable.
            point = hits[0]; sentence = re.split(r'[.!?]', low[max(0, low.rfind('.', 0, point)+1):low.find('.', point) if low.find('.', point) >= 0 else len(low)])
            context = sentence[0] if sentence else low
            local_neg = sum(has_term(context,w) for w in NEGATIVE)
            local_pos = sum(has_term(context,w) for w in POSITIVE)
            aspect_sentiment = 'Negative' if local_neg > local_pos else ('Positive' if local_pos > local_neg else sentiment)
            aspects.append({'aspect':name, 'sentiment':aspect_sentiment})
    if any(w in low for w in ASPECTS['Delivery']): category='Delivery'
    elif any(w in low for w in ASPECTS['Packaging']): category='Packaging'
    elif any(w in low for w in ASPECTS['Pricing']): category='Pricing'
    elif any(w in low for w in ASPECTS['Customer Service']): category='Customer Service'
    else: category='Product Quality'
    return sentiment, aspects, category

def emotion(text):
    low=text.lower(); scores={k:sum(w in low for w in words) for k,words in EMOTION_WORDS.items()}
    best=max(scores,key=scores.get)
    return best if scores[best] else 'Neutral'

def looks_fake(text):
    low=text.lower().strip()
    return len(low)<18 or len(set(low.split()))<5 or low in [r['text'].lower() for r in REVIEWS]

REVIEWS=[]
for i,(pid,text,season,date) in enumerate(RAW_REVIEWS,1):
    sent, aspects, category = analyze(text)
    REVIEWS.append({'id':f'r{i}','product_id':pid,'text':text,'season':season,'timestamp':date,'sentiment':sent,'aspects':aspects,'complaint_category':category,'emotion':emotion(text),'is_fake':False,'festival':season if 'Season' in season else None})

# If the importer has been run, use the real Amazon Fashion records instead of
# the small demo seed. This keeps the app runnable before the download exists.
REAL_REVIEWS = BASE_DIR / 'data' / 'reviews.json' if 'BASE_DIR' in globals() else Path(__file__).resolve().parent.parent / 'data' / 'reviews.json'
REAL_PRODUCTS = REAL_REVIEWS.with_name('products.json')
if REAL_REVIEWS.exists() and REAL_PRODUCTS.exists():
    REVIEWS = json.loads(REAL_REVIEWS.read_text(encoding='utf-8'))
    PRODUCTS = json.loads(REAL_PRODUCTS.read_text(encoding='utf-8'))

USERS = {'owner@textile.ai': {'email':'owner@textile.ai','name':'Asha Rao','role':'management','password':pwd.hash('demo123')}, 'design@textile.ai': {'email':'design@textile.ai','name':'Design Team','role':'design','password':pwd.hash('demo123')}, 'sales@textile.ai': {'email':'sales@textile.ai','name':'Marketing Team','role':'marketing','password':pwd.hash('demo123')}, 'qa@textile.ai': {'email':'qa@textile.ai','name':'Quality Assurance','role':'qa','password':pwd.hash('demo123')}}

class ReviewIn(BaseModel):
    product_id: str
    text: str
    season: str = 'Summer'

def token_for(user):
    return jwt.encode({'sub':user['email'],'exp':datetime.now(timezone.utc)+timedelta(hours=8)}, SECRET, algorithm=ALGORITHM)

async def current_user(token: str = Depends(oauth2)):
    try: email=jwt.decode(token, SECRET, algorithms=[ALGORITHM]).get('sub')
    except JWTError: raise HTTPException(status_code=401, detail='Invalid or expired token')
    if email not in USERS: raise HTTPException(status_code=401, detail='User not found')
    return USERS[email]

def require(*roles):
    async def checker(user=Depends(current_user)):
        if user['role'] not in roles: raise HTTPException(status_code=403, detail='This module is restricted to your role')
        return user
    return checker

def product_stats_map(source=None):
    result={}
    for r in source if source is not None else REVIEWS:
        if r.get('is_fake'): continue
        item=result.setdefault(r['product_id'],{'review_count':0,'negative_count':0,'complaint_count':0})
        item['review_count']+=1
        if r['sentiment']=='Negative': item['negative_count']+=1; item['complaint_count']+=1
    for item in result.values():
        count=max(item['review_count'],1); item['negative_pct']=round(item['negative_count']/count*100); item['priority_score']=round((item['negative_count']/count)*60 + item['complaint_count']*12 + item['review_count']*2,1); item.pop('complaint_count',None)
    return result

def product_stats(p):
    stats=product_stats_map().get(p['id'],{'review_count':0,'negative_count':0,'negative_pct':0,'priority_score':0})
    return stats

app=FastAPI(title='Textile Sentiment Analysis & Business Intelligence System', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:8000','http://localhost:8000'], allow_credentials=True, allow_methods=['GET','POST'], allow_headers=['Authorization','Content-Type'])
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'
app.mount('/static', StaticFiles(directory=FRONTEND_DIR / 'static'), name='static')

# MongoDB is the source of truth when MONGODB_URL is configured. The JSON data
# remains a useful first-run seed, and the in-memory lists keep the app usable
# when MongoDB has not been configured yet.
mongo_db = None
if os.getenv('MONGODB_URL'):
    try:
        from backend.db import get_database

        mongo_db = get_database()
        if mongo_db.products.count_documents({}) == 0 and PRODUCTS:
            mongo_db.products.insert_many(PRODUCTS)
        if mongo_db.reviews.count_documents({}) == 0 and REVIEWS:
            mongo_db.reviews.insert_many(REVIEWS)

        PRODUCTS = list(mongo_db.products.find({}, {'_id': 0}))
        REVIEWS = list(mongo_db.reviews.find({}, {'_id': 0}))
        logger.info('MongoDB connected: %s products, %s reviews', len(PRODUCTS), len(REVIEWS))
    except Exception:
        logger.exception('MongoDB connection failed; using local seed data')

@app.middleware('http')
async def request_logging(request:Request, call_next):
    response=await call_next(request)
    logger.info('%s %s %s', request.method, request.url.path, response.status_code)
    return response

@app.get('/health', include_in_schema=False)
async def health():
    return {'status':'ok','reviews':len(REVIEWS),'products':len(PRODUCTS)}

@app.get('/api/filter-counts')
async def filter_counts(user=Depends(current_user)):
    sentiments={'Positive':0,'Negative':0,'Neutral':0}; seasons={}
    for review in REVIEWS:
        sentiment=review.get('sentiment')
        if sentiment in sentiments: sentiments[sentiment]+=1
        season=review.get('season') or 'Unknown'
        item=seasons.setdefault(season,{'reviews':0,'positive':0,'negative':0,'neutral':0})
        item['reviews']+=1
        if sentiment in ('Positive','Negative','Neutral'): item[sentiment.lower()]+=1
    return {'total':len(REVIEWS),'sentiments':sentiments,'seasons':seasons}

@app.get('/', include_in_schema=False)
async def home(): return FileResponse(FRONTEND_DIR / 'static' / 'index.html')

@app.get('/login', include_in_schema=False)
async def login_page(): return FileResponse(FRONTEND_DIR / 'static' / 'index.html')

@app.post('/api/auth/login')
async def login(form: OAuth2PasswordRequestForm=Depends()):
    user=USERS.get(form.username)
    if not user or not pwd.verify(form.password,user['password']): raise HTTPException(status_code=401, detail='Incorrect email or password')
    return {'access_token':token_for(user),'token_type':'bearer','user':{'email':user['email'],'name':user['name'],'role':user['role']}}

@app.get('/api/auth/me')
async def me(user=Depends(current_user)): return {'email':user['email'],'name':user['name'],'role':user['role']}

@app.get('/api/dashboard', dependencies=[Depends(require('management'))])
async def dashboard(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None, view:Optional[str]=None):
    rows=[r for r in REVIEWS if (not sentiment or r['sentiment']==sentiment) and (not season or r['season']==season)]
    display_total=len(rows); total=max(display_total,1); counts={s:sum(r['sentiment']==s for r in rows) for s in ['Positive','Negative','Neutral']}
    stats_by_product=product_stats_map(rows); ps=[dict(p,**stats_by_product.get(p['id'],{'review_count':0,'negative_count':0,'negative_pct':0,'priority_score':0})) for p in PRODUCTS]
    issues={'Design':0,'Sales & Marketing':0,'Quality Assurance':0}
    design_aspects={'Product Design','Color & Appearance','Comfort & Fit'}
    qa_aspects={'Fabric Quality','Material Quality'}
    sales_categories={'Delivery','Packaging','Pricing','Customer Service'}
    for r in rows:
        if r['sentiment']!='Negative': continue
        mentioned={a['aspect'] for a in r.get('aspects',[])}
        if mentioned & design_aspects or r.get('complaint_category')=='Product Quality': issues['Design']+=1
        if mentioned & qa_aspects or r.get('complaint_category')=='Product Quality': issues['Quality Assurance']+=1
        if r.get('complaint_category') in sales_categories: issues['Sales & Marketing']+=1
    return {'metrics':{'products':len(PRODUCTS),'reviews':display_total,'positive_pct':round(counts['Positive']/total*100),'negative_pct':round(counts['Negative']/total*100),'neutral_pct':round(counts['Neutral']/total*100)},'sentiment':counts,'priority_products':sorted(ps,key=lambda x:x['priority_score'],reverse=True),'top_products':sorted(ps,key=lambda x:x['rating'],reverse=True),'issues':issues,'seasonal':seasonal_data(rows)}

async def design_analytics(user, sentiment=None, season=None):
    design_aspects={'Color & Appearance','Comfort & Fit','Product Design'}
    aspects={}
    rows=[r for r in REVIEWS if (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season)]
    for r in rows:
        for a in r['aspects']:
            if a['aspect'] not in design_aspects: continue
            aspects.setdefault(a['aspect'],{'positive':0,'negative':0,'neutral':0,'total':0}); aspects[a['aspect']][a['sentiment'].lower()]+=1; aspects[a['aspect']]['total']+=1
    stats_by_product=product_stats_map()
    return {'module':'design','aspects':aspects,'priority_products':sorted([dict(p,**stats_by_product.get(p['id'],{'review_count':0,'negative_count':0,'negative_pct':0,'priority_score':0})) for p in PRODUCTS],key=lambda x:x['priority_score'],reverse=True),'recommendations':['Review sizing measurements for Monsoon Cotton Saree','Refine color and print direction for the next collection','Use customer-loved comfort signals as design benchmarks']}

async def sales_analytics(user, sentiment=None, season=None):
    rows=[r for r in REVIEWS if (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season)]
    parameters={}; review_counts={}
    for r in rows:
        review_counts[r['product_id']]=review_counts.get(r['product_id'],0)+1
        parameter=r.get('complaint_category') or 'Product Quality'
        item=parameters.setdefault(parameter,{'total':0,'positive':0,'negative':0,'neutral':0})
        item['total']+=1; item[r['sentiment'].lower()]+=1
    products_by_id={p['id']:p for p in PRODUCTS}; product_rows={}
    for r in rows:
        if r['sentiment']!='Negative' or r.get('is_fake'): continue
        item=product_rows.setdefault(r['product_id'],{'negative_count':0,'negative_comments':[]})
        item['negative_count']+=1; item['negative_comments'].append(r['text'])
    priority={'high':[],'medium':[],'low':[]}
    for product in PRODUCTS:
        product_id=product['id']; item=product_rows.get(product_id,{'negative_count':0,'negative_comments':[]})
        review_count=review_counts.get(product_id,0)
        item['product_id']=product_id; item['name']=product.get('name',product_id); item['negative_pct']=round(item['negative_count']/max(review_count,1)*100)
        item['review_count']=review_count
        # Base marketing priority on actual negative-review volume. A low
        # catalogue rating alone must not create a fake negative review card.
        # The imported data has larger synthetic review batches, so 20+ is
        # treated as urgent and 1-19 as moderate risk.
        if item['negative_count']>=20:
            item['priority']='High'
        elif item['negative_count']>0:
            item['priority']='Medium'
        else:
            item['priority']='Low'
        priority[item['priority'].lower()].append(item)
    for items in priority.values(): items.sort(key=lambda item:(item['negative_count'],item['negative_pct']),reverse=True)
    return {'module':'sales','parameters':parameters,'priority_products':priority,'categories':{name:item['total'] for name,item in parameters.items()},'recommendations':['Add proactive order tracking and courier SLA alerts','Improve protective packaging for outbound shipments','Test value messaging on products with pricing objections'],'trend':'Delivery complaints are the largest service signal in the latest review sample.'}

async def qa_analytics(user, sentiment=None, season=None):
    defects=[r for r in REVIEWS if (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season) and not r.get('is_fake')]
    return {'module':'qa','alerts':len(defects),'defect_categories':{k:sum(k.lower() in r['text'].lower() for r in defects) for k in ['fabric','color','stitch','durability','damaged']},'recommendations':['Inspect color-fixation batches before dispatch','Add wash-resistance testing to QA checklist','Review stitching and shrinkage tolerances for repeat complaints']}

def seasonal_data(source=None):
    rows=source if source is not None else REVIEWS
    seasons=sorted({r.get('season') or 'Unknown' for r in rows})
    return {s:{'reviews':sum(r.get('season')==s for r in rows),'positive':sum(r.get('season')==s and r['sentiment']=='Positive' for r in rows),'negative':sum(r.get('season')==s and r['sentiment']=='Negative' for r in rows),'neutral':sum(r.get('season')==s and r['sentiment']=='Neutral' for r in rows)} for s in seasons}

def seasonal_forecast(source=None, baseline=None):
    rows=source if source is not None else REVIEWS
    baseline_rows=baseline if baseline is not None else rows
    summary=seasonal_data(rows)
    if not summary: return {'season':None,'sales_change_pct':0,'negative_pct':0,'preference_signals':[]}
    season, metrics=max(summary.items(),key=lambda item:item[1]['reviews'])
    total=metrics['reviews']
    baseline_summary=seasonal_data(baseline_rows)
    normal=sum(item['reviews'] for item in baseline_summary.values())/max(len(baseline_summary),1)
    sales_change_pct=round((total-normal)/normal*100) if normal else 0
    matching=[r for r in rows if (r.get('season') or 'Unknown')==season]
    aspect_counts={}
    for review in matching:
        for item in review.get('aspects',[]):
            if item['sentiment']=='Positive': aspect_counts[item['aspect']]=aspect_counts.get(item['aspect'],0)+1
    return {'season':season,'sales_change_pct':sales_change_pct,'negative_pct':round(metrics['negative']/max(total,1)*100),'preference_signals':[name for name,_ in sorted(aspect_counts.items(),key=lambda item:item[1],reverse=True)[:3]]}

@app.get('/api/analytics/design', dependencies=[Depends(require('management','design'))])
async def design_endpoint(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None): return await design_analytics(user,sentiment,season)

@app.get('/api/analytics/sales', dependencies=[Depends(require('management','marketing'))])
async def sales_endpoint(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None): return await sales_analytics(user,sentiment,season)

@app.get('/api/analytics/qa', dependencies=[Depends(require('management','qa'))])
async def qa_endpoint(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None): return await qa_analytics(user,sentiment,season)

@app.get('/api/analytics/aspects')
async def aspects_endpoint(user=Depends(current_user)):
    role_aspects={
        'management':set(ASPECTS),
        'design':{'Color & Appearance','Comfort & Fit','Product Design'},
        'marketing':{'Delivery','Packaging','Pricing','Customer Service'},
        'qa':{'Fabric Quality','Material Quality'},
    }
    allowed=role_aspects.get(user['role'],set(ASPECTS))
    data={}
    for r in REVIEWS:
        if r.get('is_fake'): continue
        for a in r['aspects']:
            if a['aspect'] not in allowed: continue
            x=data.setdefault(a['aspect'],{'positive':0,'negative':0,'neutral':0,'total':0}); x[a['sentiment'].lower()]+=1; x['total']+=1
    for x in data.values(): x['satisfaction_pct']=round((x['positive']+x['neutral']*.5)/max(x['total'],1)*100)
    return data

@app.get('/api/analytics/emotions')
async def emotions_endpoint(user=Depends(current_user)):
    result={k:0 for k in ['Happy','Excited','Neutral','Disappointed','Angry']}
    for r in REVIEWS:
        if not r.get('is_fake'): result[r['emotion']]+=1
    return result

@app.get('/api/analytics/suggestions')
async def suggestions_endpoint(user=Depends(current_user)):
    return {'suggestions':[{'complaint':'Color fading after washing','suggestion':'Improve dye fixation and conduct wash-resistance testing.'},{'complaint':'Late delivery','suggestion':'Add courier SLA alerts, route optimization, and order tracking.'},{'complaint':'Size inconsistency','suggestion':'Standardize garment measurements and add pre-dispatch fitting checks.'}]}

@app.get('/api/products')
async def products(user=Depends(current_user), search:Optional[str]=None, sentiment:Optional[str]=None, season:Optional[str]=None, page:int=Query(1,ge=1), page_size:int=Query(24,ge=1,le=100)):
    rows=PRODUCTS if not search else [p for p in PRODUCTS if search.lower() in p['name'].lower() or search.lower() in p.get('category','').lower()]
    filtered_reviews=[r for r in REVIEWS if (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season)]
    stats_by_product=product_stats_map(filtered_reviews)
    enriched=[dict(p,**stats_by_product.get(p['id'],{'review_count':0,'negative_count':0,'negative_pct':0,'priority_score':0})) for p in rows]
    if sentiment or season:
        enriched=[p for p in enriched if p['review_count']>0]
    enriched.sort(key=lambda p:(p['priority_score'],p['negative_count'],p['review_count']),reverse=True)
    start=(page-1)*page_size
    return {'items':enriched[start:start+page_size],'total':len(enriched),'page':page,'page_size':page_size}

@app.get('/api/products/{product_id}')
async def product(product_id:str,user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None):
    p=next((p for p in PRODUCTS if p['id']==product_id),None)
    if not p: raise HTTPException(404,'Product not found')
    rs=[r for r in REVIEWS if r['product_id']==product_id and (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season)]; positives=[r for r in rs if r['sentiment']=='Positive']; negatives=[r for r in rs if r['sentiment']=='Negative']; stats=product_stats_map(rs).get(product_id,{'review_count':0,'negative_count':0,'negative_pct':0,'priority_score':0})
    aspect_counts={}
    for review in rs:
        for item in review.get('aspects',[]):
            key=item['aspect']; aspect_counts.setdefault(key,{'positive':0,'negative':0,'total':0}); aspect_counts[key][item['sentiment'].lower()]+=1; aspect_counts[key]['total']+=1
    top_positive=sorted(((k,v['positive']) for k,v in aspect_counts.items() if v['positive']),key=lambda x:x[1],reverse=True)
    top_negative=sorted(((k,v['negative']) for k,v in aspect_counts.items() if v['negative']),key=lambda x:x[1],reverse=True)
    strength=top_positive[0][0].lower() if top_positive else p.get('category','product quality').lower()
    concern=top_negative[0][0].lower() if top_negative else None
    rating=float(p.get('rating') or 0)
    if negatives and concern:
        summary=f"{p['name']} earns {rating:.1f}/5 from {len(rs)} analyzed reviews, with customers responding most positively to its {strength}. The main opportunity is {concern}, which appears in {top_negative[0][1]} negative signal{'s' if top_negative[0][1] != 1 else ''} and is lowering confidence in repeat purchase."
        recommendation=f"Prioritize a {concern} review for the next {p.get('category','product').lower()} batch, then monitor whether negative feedback falls below {stats.get('negative_pct',0)}%."
    elif positives:
        summary=f"{p['name']} is a strong performer at {rating:.1f}/5. Across {len(rs)} analyzed reviews, customers consistently highlight its {strength}; there are no recurring negative themes requiring immediate action."
        recommendation=f"Protect the current {strength} experience and use this product as a benchmark for other {p.get('category','textile').lower()} items."
    else:
        summary=f"{p['name']} has {len(rs)} analyzed reviews and a {rating:.1f}/5 rating. The available feedback is still too mixed to identify one reliable strength or risk, so this product should remain under observation."
        recommendation='Collect more verified feedback before making a major quality or merchandising change.'
    return {**p,**stats,'reviews':rs,'positive_reviews':len(positives),'negative_reviews':len(negatives),'summary':summary,'recommendation':recommendation}

@app.post('/api/reviews', dependencies=[Depends(require('management','qa'))])
async def add_review(body:ReviewIn,user=Depends(current_user)):
    if not any(p['id']==body.product_id for p in PRODUCTS): raise HTTPException(404,'Product not found')
    sent,aspects,category=analyze(body.text); review={'id':f'r{len(REVIEWS)+1}','product_id':body.product_id,'text':body.text,'season':body.season,'timestamp':datetime.now().date().isoformat(),'sentiment':sent,'aspects':aspects,'complaint_category':category,'emotion':emotion(body.text),'is_fake':looks_fake(body.text),'festival':body.season if 'Season' in body.season else None}
    if mongo_db is not None:
        mongo_db.reviews.insert_one(review)
    REVIEWS.append(review)
    return review

@app.post('/api/reviews/bulk', dependencies=[Depends(require('management','qa'))])
async def bulk_reviews(items:list[ReviewIn],user=Depends(current_user)):
    return [await add_review(item,user) for item in items]

@app.get('/api/analytics/fake-reviews')
async def fake_stats(user=Depends(current_user)):
    flagged=sum(bool(r.get('is_fake')) for r in REVIEWS)
    return {'flagged':flagged,'included':len(REVIEWS)-flagged,'total':len(REVIEWS)}

@app.get('/api/seasonal')
async def seasonal(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None):
    rows=[r for r in REVIEWS if (not sentiment or r.get('sentiment')==sentiment) and (not season or r.get('season')==season)]
    sentiment_rows=[r for r in REVIEWS if not sentiment or r.get('sentiment')==sentiment]
    forecast=seasonal_forecast(rows, sentiment_rows)
    season=forecast['season'] or 'upcoming season'
    preferences=', '.join(forecast['preference_signals']) or 'customer feedback signals'
    return {'data':seasonal_data(rows),'forecast':forecast,'prediction':f'{season} has the strongest demand signal. Prioritize inventory and promotions around {preferences.lower()}.'}

@app.get('/api/reviews')
async def reviews_endpoint(user=Depends(current_user), sentiment:Optional[str]=None, season:Optional[str]=None, search:Optional[str]=None, page:int=Query(1,ge=1), page_size:int=Query(25,ge=1,le=100)):
    rows=[r for r in REVIEWS if (not sentiment or r['sentiment']==sentiment) and (not season or r['season']==season) and (not search or search.lower() in r['text'].lower())]
    start=(page-1)*page_size
    return {'items':rows[start:start+page_size],'total':len(rows),'page':page,'page_size':page_size}

class QueryIn(BaseModel):
    question:str

@app.post('/api/query')
async def natural_language_query(body:QueryIn,user=Depends(current_user)):
    q=body.question.lower().strip(); valid=[r for r in REVIEWS if not r.get('is_fake')]
    if not q:
        return {'answer':'Ask me anything about the textile products, reviews, quality, fit, delivery, or seasonal demand.','confidence':1,'type':'summary','data':{}}
    if re.fullmatch(r'(hi|hello|hey|hii|good morning|good afternoon|good evening)[!. ]*',q):
        return {'answer':'Hello! I am your textile AI analyst. Ask me about a product, fabric quality, fit, color, delivery, customer complaints, or seasonal demand.','confidence':1,'type':'summary','data':{}}
    if any(phrase in q for phrase in ['thank you','thanks','that helps','great answer']):
        return {'answer':'You are welcome. Ask another textile question whenever you are ready.','confidence':1,'type':'summary','data':{}}

    product_names={p['id']:p['name'] for p in PRODUCTS}
    if any(word in q for word in ['best','highest rated','top rated','rating','star']):
        if not PRODUCTS: return {'answer':'There are no products available to compare yet.','confidence':1,'type':'summary','data':{}}
        best=max(PRODUCTS,key=lambda product:float(product.get('rating') or 0))
        return {'answer':f'{best["name"]} is currently the highest-rated product at {float(best.get("rating") or 0):.1f}/5. Its strongest verified signals should be used as a benchmark for the next collection.','confidence':0.9,'type':'summary','data':{}}
    if any(word in q for word in ['how many','number of','count','total']) and any(word in q for word in ['review','feedback']):
        return {'answer':f'There are {len(valid)} verified reviews covering {len(PRODUCTS)} textile products in the current dataset.','confidence':0.98,'type':'summary','data':{}}
    if any(word in q for word in ['recommend','recommendation','improve','next step','what should']) and not any(word in q for word in ['sustainable','trend','fashion','return','price']):
        return {'answer':'Prioritize colorfastness and shrinkage testing, standardize fit measurements, and add delivery tracking with stronger packaging. These actions address the clearest recurring textile signals in the verified reviews.','confidence':0.85,'type':'summary','data':{}}
    if any(word in q for word in ['positive','happy','liked','love','satisfied']):
        positive=sum(review['sentiment']=='Positive' for review in valid)
        return {'answer':f'Customers left {positive} positive reviews, or {round(positive/max(len(valid),1)*100)}% of the verified sample. Comfort, appearance, and material quality are the most common strengths.','confidence':0.87,'type':'summary','data':{}}
    if any(word in q for word in ['emotion','feeling','angry','disappointed']):
        emotions={name:sum(review.get('emotion')==name for review in valid) for name in ['Happy','Excited','Neutral','Disappointed','Angry']}
        strongest=max(emotions,key=emotions.get)
        return {'answer':f'The strongest customer emotion is {strongest} with {emotions[strongest]} verified reviews. Use the disappointed and angry reviews to prioritize service and quality follow-up.','confidence':0.84,'type':'bar','data':emotions}
    if any(word in q for word in ['compare','difference','versus','vs']):
        if not PRODUCTS: return {'answer':'There are no products available to compare yet.','confidence':1,'type':'summary','data':{}}
        best=max(PRODUCTS,key=lambda product:float(product.get('rating') or 0)); weakest=min(PRODUCTS,key=lambda product:float(product.get('rating') or 0))
        return {'answer':f'{best["name"]} leads the catalog at {float(best.get("rating") or 0):.1f}/5, while {weakest["name"]} is lowest at {float(weakest.get("rating") or 0):.1f}/5. Compare their fabric, fit, and color feedback before making a range decision.','confidence':0.88,'type':'summary','data':{}}

    if any(word in q for word in ['color','colour','fade','fading','print']):
        matches=[r for r in valid if any(word in r['text'].lower() for word in ['color','colour','fade','faded','print'])]
        counts={name:0 for name in product_names.values()}
        for review in matches: counts[product_names.get(review['product_id'],review['product_id'])]=counts.get(product_names.get(review['product_id'],review['product_id']),0)+1
        answer=max(counts,key=counts.get) if matches else 'No matching product data'
        return {'answer':f'{answer} has the most color-related complaints in the current dataset ({counts.get(answer,0)} reviews). Consider wash-resistance testing and improved dye fixation.','confidence':0.9,'type':'bar','data':counts}
    if any(word in q for word in ['negative','complaint','problem','issue','bad']):
        counts={name:0 for name in product_names.values()}
        for review in valid:
            if review['sentiment']=='Negative':
                name=product_names.get(review['product_id'],review['product_id']); counts[name]=counts.get(name,0)+1
        answer=max(counts,key=counts.get) if counts else 'No data'
        return {'answer':f'{answer} currently has the highest negative-review count ({counts.get(answer,0)}). Review its quality and fit signals before the next production batch.','confidence':0.86,'type':'bar','data':counts}
    if any(word in q for word in ['delivery','shipping','courier','late','packaging']):
        matches=[r for r in valid if r['complaint_category'] in ['Delivery','Packaging']]
        return {'answer':f'I found {len(matches)} delivery or packaging-related reviews. The clearest action is to add courier SLA alerts, proactive tracking, and stronger protective packaging.','confidence':0.84,'type':'summary','data':{}}
    if any(word in q for word in ['summer','winter','spring','autumn','season','festive','wedding','demand']):
        season_counts={s:sum(r['season']==s for r in valid) for s in ['Summer','Winter','Spring','Autumn','Festive Season','Wedding Season']}
        season=max(season_counts,key=season_counts.get)
        return {'answer':f'{season} has the strongest review activity with {season_counts[season]} verified reviews. For the upcoming Summer season, prioritize breathable cotton and comfort-focused promotions.','confidence':0.82,'type':'bar','data':season_counts}
    if any(word in q for word in ['fabric','material','cotton','silk','quality','durable','shrink']):
        matches=[r for r in valid if any(word in r['text'].lower() for word in ['fabric','material','cotton','silk','quality','durable','shrink'])]
        positive=sum(r['sentiment']=='Positive' for r in matches)
        return {'answer':f'Fabric and material feedback is mostly positive: {positive} of {len(matches)} matching reviews are positive. Keep testing shrinkage and wash durability, especially for cotton products.','confidence':0.84,'type':'summary','data':{}}
    if any(word in q for word in ['fit','size','comfortable','comfort','care','wash','washing']):
        return {'answer':'For textile fit and care, standardize garment measurements, include a clear size guide, and validate shrinkage and colorfastness after washing. The current reviews highlight fit and wash durability as useful quality checkpoints.','confidence':0.79,'type':'summary','data':{}}
    product_matches=[p for p in PRODUCTS if p['name'].lower() in q or p.get('category','').lower() in q]
    if product_matches:
        product=product_matches[0]; reviews=[r for r in valid if r['product_id']==product['id']]
        return {'answer':f'{product["name"]} has a {product.get("rating",0):.1f}/5 rating from {len(reviews)} verified reviews. Ask me about its strengths, complaints, fit, fabric, or delivery.','confidence':0.88,'type':'summary','data':{}}
    textile_topics={
        'sustainable':'For more sustainable textile production, prioritize durable materials, low-impact dyes, recycled fibers, and transparent care guidance so products last longer.',
        'trend':'Current textile planning should balance breathable comfort, versatile silhouettes, durable materials, and colorfast prints. Validate any trend with fresh customer feedback before scaling it.',
        'fashion':'For a strong fashion assortment, combine customer-loved comfort and material quality with seasonal colors, practical fits, and a clear price-to-value story.',
        'return':'For returns, make sizing and care information prominent, standardize measurements, and track return reasons alongside review sentiment to identify preventable product issues.',
        'price':'Price perception should be evaluated alongside material quality, durability, finish, and delivery experience. Customers are more tolerant of premium pricing when the value is clear.',
    }
    for topic,answer in textile_topics.items():
        if topic in q: return {'answer':answer,'confidence':0.78,'type':'summary','data':{}}

    stopwords={'what','which','where','when','why','how','does','do','are','is','the','this','that','about','from','with','your','our','can','you','tell','me','please','should','have','has','for','and','all'}
    terms=[term for term in re.findall(r'[a-z0-9]+',q) if len(term)>2 and term not in stopwords]
    matches=[review for review in valid if any(term in review['text'].lower() or term in product_names.get(review['product_id'],'').lower() for term in terms)]
    if matches:
        positive=sum(review['sentiment']=='Positive' for review in matches); negative=sum(review['sentiment']=='Negative' for review in matches)
        top_product=max(set(product_names.get(review['product_id'],review['product_id']) for review in matches),key=lambda name:sum(product_names.get(review['product_id'],review['product_id'])==name for review in matches))
        return {'answer':f'I found {len(matches)} reviews related to "{body.question}". The matching feedback is {positive} positive and {negative} negative, with {top_product} appearing most often. Ask me to break this down by product, sentiment, or aspect.','confidence':0.68,'type':'summary','data':{}}
    return {'answer':f'I do not have a direct review match for "{body.question}" yet. I can still help with textile design, materials, care, fit, pricing, sustainability, quality, delivery, and customer feedback.','confidence':0.55,'type':'summary','data':{}}

@app.get('/api/alerts')
async def alerts(user=Depends(current_user)):
    negative=sum(r['sentiment']=='Negative' and not r.get('is_fake') for r in REVIEWS)
    return {'live':True,'last_updated':datetime.now(timezone.utc).isoformat(),'alerts':[{'severity':'high','title':'Quality watch','message':f'{negative} verified negative reviews require attention.'}] if negative else []}
