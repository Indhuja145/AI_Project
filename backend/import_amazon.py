"""Import the official Amazon Fashion 5-core review subset.

Usage from the project root:
  python backend/import_amazon.py
  python backend/import_amazon.py --source data/AMAZON_FASHION_5.json.gz

The importer writes normalized JSON files consumed automatically by main.py.
It also accepts a Kaggle CSV with review text, rating, product ID, and date
columns when --source points to that file.
"""
import argparse, csv, gzip, json, re, urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DEFAULT_URL='https://jmcauley.ucsd.edu/data/amazon_v2/categoryFilesSmall/AMAZON_FASHION_5.json.gz'
NEGATIVE=['bad','poor','worst','faded','fade','late','delay','damaged','tear','shrunk','expensive','wrong','missing','uncomfortable','disappointed','defect','outdated','tight']
POSITIVE=['good','great','excellent','love','beautiful','comfortable','soft','durable','perfect','fast','reasonable','premium','quality','happy']
ASPECTS={'Fabric Quality':['fabric','stitch','stitching','durable','durability','shrink','thread','tear'],'Color & Appearance':['color','colour','fade','faded','print','pattern','appearance'],'Comfort & Fit':['comfort','comfortable','soft','texture','fit','size','tight','loose'],'Product Design':['design','style','pattern','outdated','look'],'Material Quality':['material','cotton','silk','polyester','quality']}
EMOTIONS={'Happy':['love','happy','excellent','perfect','comfortable','beautiful','satisfied'],'Excited':['excited','gorgeous','amazing','wow','premium'],'Disappointed':['disappointed','expected','overpriced','shrunk','faded','late'],'Angry':['worst','unacceptable','refund','wrong','damaged','fraud']}

def season(date):
    try: month=datetime.strptime(date, '%m %d, %Y').month
    except Exception:
        try: month=datetime.strptime(date, '%d %B %Y').month
        except Exception:
            try: month=datetime.fromisoformat(date).month
            except Exception: return 'Unknown'
    return 'Winter' if month in (12,1,2) else 'Spring' if month in (3,4,5) else 'Summer' if month in (6,7,8) else 'Autumn'

def classify(text, seen):
    low=text.lower(); negative=sum(w in low for w in NEGATIVE); positive=sum(w in low for w in POSITIVE)
    sentiment='Negative' if negative>positive else 'Positive' if positive>negative else 'Neutral'
    aspects=[]
    for name,words in ASPECTS.items():
        if any(re.search(r'\b'+re.escape(w)+r'\b',low) for w in words):
            aspects.append({'aspect':name,'sentiment':'Negative' if negative>positive else 'Positive' if positive>negative else 'Neutral'})
    emotion_scores={name:sum(w in low for w in words) for name,words in EMOTIONS.items()}; best=max(emotion_scores,key=emotion_scores.get)
    emotion=best if emotion_scores[best] else 'Neutral'
    category='Delivery' if any(w in low for w in ['delivery','delivered','late','delay','courier','shipping']) else 'Packaging' if any(w in low for w in ['package','packaging','damaged','box','missing']) else 'Pricing' if any(w in low for w in ['price','pricing','expensive','overpriced','worth','cost']) else 'Customer Service' if any(w in low for w in ['support','return','refund','service','response']) else 'Product Quality'
    is_fake=len(low)<18 or len(set(low.split()))<5 or low in seen
    return sentiment,aspects,category,emotion,is_fake

def rows_from_json(path):
    with gzip.open(path,'rt',encoding='utf-8') as source:
        yield from (json.loads(line) for line in source if line.strip())

def rows_from_csv(path):
    with path.open(newline='',encoding='utf-8-sig') as source:
        for row in csv.DictReader(source):
            raw=row.get('customer_reviews','')
            # Kaggle's catalog stores reviews as: title // rating // date // By ... // body | ...
            chunks=[chunk.strip() for chunk in raw.split(' | ') if chunk.strip()]
            if not chunks:
                yield row
                continue
            for chunk in chunks:
                parts=[part.strip() for part in chunk.split(' // ')]
                if len(parts)>=5:
                    yield {**row,'reviewText':parts[-1],'overall':parts[1],'reviewTime':parts[2]}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--source',default=str(ROOT/'data'/'AMAZON_FASHION_5.json.gz')); parser.add_argument('--download',action='store_true'); args=parser.parse_args()
    source=Path(args.source); source.parent.mkdir(parents=True,exist_ok=True)
    if args.download or not source.exists():
        print('Downloading official Amazon Fashion 5-core subset...')
        urllib.request.urlretrieve(DEFAULT_URL,source)
    rows=rows_from_json(source) if source.suffix=='.gz' else rows_from_csv(source)
    reviews=[]; products={}; seen=set()
    for index,row in enumerate(rows,1):
        text=row.get('reviewText') or row.get('review_text') or row.get('text') or ''
        product_id=row.get('asin') or row.get('product_id') or row.get('productId') or row.get('uniq_id') or 'unknown'
        date=row.get('reviewTime') or row.get('review_date') or row.get('date') or ''
        rating=float(row.get('overall') or row.get('rating') or 0)
        sentiment,aspects,category,emotion,is_fake=classify(text,seen); seen.add(text.lower())
        reviews.append({'id':f'amazon-{index}','product_id':product_id,'text':text,'review_text':text,'rating':rating,'season':season(date),'timestamp':date,'review_date':date,'sentiment':sentiment,'aspects':aspects,'complaint_category':category,'emotion':emotion,'is_fake':is_fake,'festival':None,'source':'Amazon Fashion 5-core'})
        price_text=str(row.get('price','0')).replace(',',''); price_match=re.search(r'[0-9]+(?:\.[0-9]+)?',price_text)
        price=float(price_match.group()) if price_match else 0
        products.setdefault(product_id,{'id':product_id,'name':row.get('product_name') or f'Amazon Fashion product {product_id}','category':row.get('amazon_category_and_sub_category','Amazon Fashion').split(' > ')[0],'price':price,'rating':0,'seasonal_tags':['Summer','Winter','Spring','Autumn'],'image':'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=600&q=80','review_count':0,'rating_sum':0})
        products[product_id]['review_count']+=1; products[product_id]['rating_sum']+=rating
    product_rows=[]
    for product in products.values(): product['rating']=round(product['rating_sum']/max(product['review_count'],1),2); product.pop('rating_sum'); product.pop('review_count'); product_rows.append(product)
    (ROOT/'data'/'reviews.json').write_text(json.dumps(reviews),encoding='utf-8'); (ROOT/'data'/'products.json').write_text(json.dumps(product_rows),encoding='utf-8')
    print(f'Imported {len(reviews):,} reviews and {len(product_rows):,} products. Flagged {sum(r["is_fake"] for r in reviews):,} suspected fake reviews.')

if __name__=='__main__': main()
