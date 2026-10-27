"""Create a clean textile-only Myntra CSV for MongoDB seeding.

Usage:
  python backend/filter_myntra_clothing.py --input data/myntra_fashion_products.csv
"""
import argparse, re
from collections import Counter
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
KEEP={
 'Sarees':['saree','sari'], 'Kurtas/Kurtis':['kurta','kurti','salwar','suit'],
 'Wedding Wear':['lehenga','sherwani','dhoti','blouse'], 'Shirts/Tops':['shirt','t-shirt','tshirt','top'],
 'Bottom Wear':['trouser','jeans','pant','shorts','skirt','legging'], 'Dupattas':['dupatta','stole','scarf'],
 'Nightwear/Innerwear':['nightwear','night suit','nightdress','lingerie','innerwear'],
 'Ethnic Wear':['ethnic wear','ethnic'], 'Western Wear':['western wear','western'],
 'Textile/Fabric':['cotton','silk','linen','chiffon','georgette','wool','rayon','viscose']}
EXCLUDE=['footwear','shoe','sandal','slipper','sneaker','bag','backpack','handbag','jewelry','jewellery','watch','sunglass','sunglasses','belt','beauty','lipstick','makeup','perfume','skincare','home decor','furniture','electronics','mobile','phone','laptop']

def first_col(frame,names):
    for name in names:
        if name in frame.columns: return frame[name].fillna('').astype(str)
    return pd.Series('',index=frame.index)

def category_for(text):
    low=text.lower()
    for category,words in KEEP.items():
        if any(re.search(r'\b'+re.escape(word)+r'\b',low) for word in words): return category
    return None

def seasonal_tags(category,text):
    low=(category+' '+text).lower(); tags=[]
    if category in ('Sarees','Wedding Wear') or any(x in low for x in ['festive','diwali','ethnic']): tags.append('Festive Season')
    if category=='Wedding Wear' or any(x in low for x in ['wedding','bridal']): tags.append('Wedding Season')
    if any(x in low for x in ['cotton','linen']): tags.append('Summer')
    if 'wool' in low: tags.append('Winter')
    return ', '.join(dict.fromkeys(tags or ['Casual/General']))

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--input',default=str(ROOT/'data'/'myntra_fashion_products.csv')); parser.add_argument('--output',default=str(ROOT/'data'/'myntra_clothing_filtered.csv')); parser.add_argument('--chunksize',type=int,default=50000); args=parser.parse_args()
    total=kept=0; chunks=[]
    for frame in pd.read_csv(args.input,chunksize=args.chunksize,low_memory=False):
        total+=len(frame)
        product_id=first_col(frame,['product_id','p_id','id','sku','uniq_id'])
        name=first_col(frame,['product_name','name','title']); category=first_col(frame,['category','masterCategory','subCategory','amazon_category_and_sub_category']); brand=first_col(frame,['brand','manufacturer']); description=first_col(frame,['description','product_description','desc']); price=first_col(frame,['price','selling_price','discounted_price']); rating=first_col(frame,['rating','avg_rating','average_rating']); image=first_col(frame,['image_url','img','image','imageURL'])
        text=(name+' '+category+' '+description).str.lower()
        matches=text.map(category_for)
        excluded=text.apply(lambda value:any(term in value for term in EXCLUDE))
        numeric_price=pd.to_numeric(price.str.replace(r'[^0-9.]','',regex=True),errors='coerce'); numeric_rating=pd.to_numeric(rating.str.extract(r'([0-9]+(?:\.[0-9]+)?)',expand=False),errors='coerce')
        valid=(matches.notna())&(~excluded)&(product_id.str.strip()!='')&(name.str.strip()!='')&description.str.strip().ne('')&numeric_price.notna()&numeric_rating.notna()
        result=pd.DataFrame({'product_id':product_id[valid].str.strip(),'product_name':name[valid].str.strip(),'category':matches[valid],'brand':brand[valid].str.strip(),'price':numeric_price[valid].round(2),'rating':numeric_rating[valid].round(2),'description':description[valid].str.strip(),'image_url':image[valid].str.strip()})
        result['seasonal_tags']=[seasonal_tags(c,t) for c,t in zip(result['category'],result['product_name']+' '+result['description'])]
        chunks.append(result); kept+=len(result)
    clean=pd.concat(chunks,ignore_index=True) if chunks else pd.DataFrame(columns=['product_id','product_name','category','brand','price','rating','description','image_url','seasonal_tags'])
    before=len(clean); clean=clean.drop_duplicates(subset=['product_id'],keep='first'); clean=clean.drop_duplicates(subset=['product_name','brand'],keep='first'); clean.to_csv(args.output,index=False)
    print(f'Original rows: {total:,}'); print(f'Rows after clothing filter: {kept:,}'); print(f'Rows after deduplication: {len(clean):,}'); print('Category breakdown:'); print(clean['category'].value_counts().to_string() if len(clean) else 'No clothing rows matched.'); print(f'Output: {args.output}')

if __name__=='__main__': main()
