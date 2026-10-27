"""Generate clearly labeled synthetic review text from Myntra aggregate ratings.

This is a demo fallback, not real customer feedback. It lets the built-in NLP
pipeline demonstrate sentiment/aspect/emotion analysis when the source catalog
has ratings but no raw review text.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def build_review(product,index,variant):
    rating=float(product.get('rating') or 0); name=product['name']; category=product.get('category','fashion').lower(); color=product.get('color','')
    if rating>=4:
        templates=[f"The {category} from {name} looks beautiful and feels comfortable. The material quality and design are excellent.",f"I like the {name}; the fabric feels good and the fit is comfortable. The finish looks premium.",f"This {category} has a lovely design and good quality. It is worth the price for everyday wear.",f"The color and appearance of {name} are attractive. The material is soft and the product feels well made.",f"A great fashion product with comfortable fabric, a neat fit, and a beautiful design."]
        text=templates[variant%len(templates)]
        sentiment,emotion='Positive','Happy'
    elif rating>=3:
        templates=[f"The {category} from {name} has an acceptable design and quality, but the fit and material could be improved.",f"The design is fine, although the fabric and sizing are average for the price.",f"This product looks as expected. Comfort and material quality are mixed.",f"The color is nice but the finish and fit could be better.",f"An average {category}; it is usable, but the quality does not feel premium."]
        text=templates[variant%len(templates)]
        sentiment,emotion='Neutral','Neutral'
    else:
        templates=[f"The {category} from {name} was disappointing. The material quality and design did not meet expectations.",f"The fabric feels poor and the fit is uncomfortable. The product is not worth the price.",f"The color and finish were disappointing, and the material quality needs improvement.",f"The design looks different than expected and the quality feels low.",f"I am unhappy with this {category}; the stitching, fit, and fabric should be improved."]
        text=templates[variant%len(templates)]
        sentiment,emotion='Negative','Disappointed'
    aspects=[{'aspect':'Product Design','sentiment':sentiment},{'aspect':'Fabric Quality','sentiment':sentiment},{'aspect':'Comfort & Fit','sentiment':sentiment}]
    if 'color' in text.lower() or 'colour' in text.lower():
        aspects.insert(1, {'aspect':'Color & Appearance','sentiment':sentiment})
    return {'id':f'synthetic-myntra-{index}-{variant}','product_id':product['id'],'text':text,'review_text':text,'rating':rating,'season':'Summer' if any(x in category for x in ['shirt','cotton','linen']) else 'Festive Season' if any(x in category for x in ['saree','ethnic','wedding']) else 'Casual/General','timestamp':None,'review_date':None,'sentiment':sentiment,'aspects':aspects,'complaint_category':'Product Quality' if sentiment=='Negative' else None,'emotion':emotion,'is_fake':False,'generated':True,'source':'Synthetic review generated from Myntra aggregate rating'}

products=json.loads((ROOT/'data'/'products.json').read_text(encoding='utf-8'))
reviews=[]
for index,product in enumerate(products,1):
    # The catalog contains aggregate ratings rather than raw review rows. Use a
    # stable, wider synthetic range so the demo does not make every product
    # appear to have the same review volume.
    seed=sum(ord(char) for char in str(product['id'])) + index * 17
    count=3+(seed % 28)  # 3-30 generated reviews per product
    reviews.extend(build_review(product,index,variant) for variant in range(count))
(ROOT/'data'/'reviews.json').write_text(json.dumps(reviews),encoding='utf-8')
print(f'Generated {len(reviews):,} labeled synthetic reviews from product ratings.')
