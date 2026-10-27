from backend.main import analyze, product_stats, seasonal_forecast, app
from fastapi.testclient import TestClient

def test_mixed_aspect_sentence_detects_aspects():
    sentiment, aspects, category = analyze('The color faded but the fabric is comfortable.')
    assert sentiment == 'Neutral'
    assert {item['aspect'] for item in aspects} >= {'Color & Appearance', 'Fabric Quality', 'Comfort & Fit'}

def test_priority_score_is_non_negative():
    product={'id':'test'}
    from backend.main import REVIEWS
    old=list(REVIEWS[:]); REVIEWS[:] = []
    try: assert product_stats(product)['priority_score'] >= 0
    finally: REVIEWS[:] = old

def test_health_endpoint_reports_runtime_state():
    response=TestClient(app).get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_seasonal_forecast_exposes_demand_and_preferences():
    forecast=seasonal_forecast()
    assert forecast['season']
    assert 0 <= forecast['demand_index'] <= 100
    assert isinstance(forecast['preference_signals'], list)
