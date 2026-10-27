"""Import a lightweight, product-only sample from the Myntra Kaggle CSV.

The source contains catalog products and aggregate ratings, not raw review text.
Those aggregates are kept on Products; Reviews is reset because fabricating raw
reviews would make the sentiment dashboard misleading.
"""
import argparse, csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--limit',type=int,default=1000); args=parser.parse_args()
    source=ROOT/'data'/'myntra_fashion_products.csv'
    products=[]
    with source.open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            if len(products)>=args.limit: break
            product_id=row.get('p_id') or row.get('id') or row.get('name')
            if not product_id or not row.get('name'): continue
            try: price=float(row.get('price') or 0); rating=float(row.get('avg_rating') or 0)
            except ValueError: price=rating=0
            products.append({'id':str(product_id),'name':row['name'].strip(),'category':row.get('brand') or 'Myntra Fashion','price':price,'rating':round(rating,2),'rating_count':int(float(row.get('ratingCount') or 0)),'color':row.get('colour') or 'Unknown','brand':row.get('brand') or 'Unknown','image':row.get('img') or 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=600&q=80','seasonal_tags':['Summer','Winter','Spring','Autumn'],'source':'Myntra Fashion Product Dataset'})
    (ROOT/'data'/'products.json').write_text(json.dumps(products),encoding='utf-8')
    (ROOT/'data'/'reviews.json').write_text('[]',encoding='utf-8')
    print(f'Imported {len(products):,} Myntra products; raw reviews in source: 0')

if __name__=='__main__': main()
