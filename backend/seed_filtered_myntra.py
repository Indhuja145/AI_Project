import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
source=ROOT/'data'/'myntra_clothing_filtered.csv'; products=[]
with source.open(encoding='utf-8-sig',newline='') as handle:
    for row in csv.DictReader(handle):
        products.append({'id':row['product_id'],'name':row['product_name'],'category':row['category'],'brand':row['brand'],'price':float(row['price'] or 0),'rating':float(row['rating'] or 0),'image':row.get('image_url') or 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=600&q=80','seasonal_tags':row.get('seasonal_tags','Casual/General').split(', ') ,'description':row.get('description',''),'source':'Myntra clothing filtered dataset'})
(ROOT/'data'/'products.json').write_text(json.dumps(products),encoding='utf-8')
(ROOT/'data'/'reviews.json').write_text('[]',encoding='utf-8')
print(f'Seeded {len(products):,} clothing products into data/products.json')
