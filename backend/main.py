import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
from database import SessionLocal, Product, User, Campaign, Donation
from fastapi.staticfiles import StaticFiles


app = FastAPI()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)) # Render thường dùng cổng 10000
    uvicorn.run(app, host="0.0.0.0", port=port)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductCreate(BaseModel):
    name: str
    stock: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Đặt các API routes lên trước
@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return {"data": products}

@app.post("/api/products")
def add_product(item: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(name=item.name, stock=item.stock)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"status": "success", "data": new_product}

# Của admin.html
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    # Đếm số lượng
    user_count = db.query(User).count()
    campaign_count = db.query(Campaign).count()
    total_stock = db.query(Product).with_entities(Product.stock).sum() # Hoặc sum số lượng
    
    return {
        "user_count": user_count,
        "campaign_count": campaign_count,
        "total_stock": total_stock
    }

#Chiến dịch
@app.get("/api/campaigns")
def get_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).all()
    return {"data": campaigns}

@app.post("/api/campaigns")
def add_campaign(item: dict, db: Session = Depends(get_db)):
    new_camp = Campaign(title=item["title"], goal_amount=item["goal_amount"])
    db.add(new_camp)
    db.commit()
    return {"status": "success"}

#Lấy đường dẫn tuyệt đối tới thư mục frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# 2. Đặt mount xuống dưới cùng
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")