import os
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
from database import SystemRegulation, Recipient, SessionLocal, Product, User, Campaign, Donation, InventoryLog, SystemLog
from fastapi.staticfiles import StaticFiles
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Các Class định nghĩa cấu trúc dữ liệu nhận vào (Pydantic Models) ---

class ProductCreate(BaseModel):
    name: str
    stock: int
    unit: str
    category: str

class UserCreate(BaseModel):
    username: str
    full_name: str = None
    email: str = None
    role: str

class UserUpdateStatus(BaseModel):
    status: str
    lock_reason: str = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def write_log(db, action, details, page, actor="Admin"):
    log = SystemLog(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        action=action,
        details=details,
        page=page,
        actor=actor
    )
    db.add(log)

# --- HÀM TỰ ĐỘNG SINH LUẬT MẪU DOANH NGHIỆP CỐ ĐỊNH KHI KHỞI ĐỘNG ---
def init_default_regulations():
    db = SessionLocal()
    try:
        if db.query(SystemRegulation).count() == 0:
            default_rules = [
                SystemRegulation(rule_group="LOCK_USER", rule_code="QD-001", rule_name="Spam quyên góp ảo / Tạo chiến dịch giả mạo"),
                SystemRegulation(rule_group="LOCK_USER", rule_code="QD-002", rule_name="Sử dụng ngôn từ công kích, vi phạm thuần phong mỹ tục"),
                SystemRegulation(rule_group="LOCK_USER", rule_code="QD-003", rule_name="Gian lận trục lợi vật phẩm cứu trợ từ kho hàng"),
                SystemRegulation(rule_group="LOCK_USER", rule_code="QD-004", rule_name="Tạm khóa theo yêu cầu bảo mật chủ động từ chủ tài khoản"),
                SystemRegulation(rule_group="INVENTORY_CRITERIA", rule_code="LIMIT_QA", rule_name="Cảnh báo tồn kho quần áo xuống quá thấp", value="20")
            ]
            db.add_all(default_rules)
            db.commit()
            print("=== Khởi tạo thành công Sách Quy định hệ thống ===")
    except Exception as e:
        print(f"Lỗi khởi tạo luật: {e}")
    finally:
        db.close()

init_default_regulations()

# --- API QUY ĐỊNH HỆ THỐNG ---
@app.get("/api/regulations")
def get_regulations(group: str = None, db: Session = Depends(get_db)):
    query = db.query(SystemRegulation).filter(SystemRegulation.is_active == True)
    if group:
        query = query.filter(SystemRegulation.rule_group == group)
    return {"data": query.all()}

@app.post("/api/regulations")
def create_regulation(item: dict, db: Session = Depends(get_db)):
    new_rule = SystemRegulation(
        rule_group=item["rule_group"],
        rule_code=item["rule_code"],
        rule_name=item["rule_name"],
        value=item.get("value", "")
    )
    db.add(new_rule)
    db.commit()
    return {"status": "success"}


# --- API QUẢN LÝ NGƯỜI DÙNG (USERS) ---

# 1. API Lấy danh sách
@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    formatted_users = []
    for u in users:
        reg_date = u.created_at.strftime("%Y-%m-%d") if u.created_at else "2026-06-23"
        formatted_users.append({
            "user_id": u.user_id,
            "user_code": u.user_code,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "lock_reason": u.lock_reason or "",
            "registration_date": reg_date
        })
    return {"data": formatted_users}

# 2. API Thêm người dùng mới
@app.post("/api/users")
def add_user(item: UserCreate, db: Session = Depends(get_db)):
    last_user = db.query(User).filter(User.user_code.like("US%")).order_by(User.user_code.desc()).first()
    next_num = 1
    if last_user and last_user.user_code:
        try:
            num_part = last_user.user_code[2:] 
            next_num = int(num_part) + 1
        except ValueError:
            pass
            
    new_user_code = f"US{next_num:03d}" 
    
    new_user = User(
        user_code=new_user_code,
        username=item.username,
        full_name=item.full_name,
        email=item.email,
        role=item.role,
        status="Hoạt động",
        lock_reason=""
    )
    
    try:
        db.add(new_user)
        write_log(
          db,
          "Thêm người dùng",
          f"Đã tạo tài khoản {item.username}",
          "Người dùng")
        db.commit()
        return {"status": "success", "user_code": new_user_code}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi lưu cơ sở dữ liệu: {str(e)}")

# 3. API Thay đổi trạng thái khóa tài khoản (Đã đồng bộ kiểm tra trạng thái "Bị khóa")
@app.put("/api/users/{id}/status")
def update_user_status(id: int, item: UserUpdateStatus, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản người dùng")
    


    user.status = item.status
    user.lock_reason = item.lock_reason if item.status == "Bị khóa" else ""
    
    if item.status == "Bị khóa":
     write_log(
        db,
        "Khóa tài khoản",
        f"Tài khoản {user.username} bị khóa",
        "Người dùng"
    )
 
    elif item.status == "Hoạt động":
     write_log(
        db,
        "Mở khóa tài khoản",
        f"Tài khoản {user.username} được mở khóa",
        "Người dùng"
    )

    try:
        db.commit()
        return {"status": "success", "current_status": user.status}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Không thể cập nhật trạng thái do lỗi hệ thống")

# 4. API Xóa tài khoản
@app.delete("/api/users/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == id).first()
    if not user:
        return {"status": "error", "message": "Không tìm thấy người dùng trên hệ thống"}
    
    try:
       write_log(
        db,
        "Xóa người dùng",
        f"Đã xóa tài khoản {user.username}",
        "Người dùng")
       db.delete(user)
       db.commit()
       return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": "Không thể xóa do phát sinh lỗi ràng buộc dữ liệu"}


# --- API QUẢN LÝ SẢN PHẨM & KHO HÀNG ---
@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return {"data": products}

@app.post("/api/products")
def add_product(item: ProductCreate, db: Session = Depends(get_db)):
    clean_name = item.name.strip().capitalize()
    category_name = item.category.strip().capitalize() if item.category else "Chưa phân loại"
    
    CATEGORY_PREFIXES = {"Quần áo": "SPQA", "Nhu yếu phẩm": "SPNY", "Chưa phân loại": "SP"}
    prefix = CATEGORY_PREFIXES.get(category_name, "SP")
    
    last_product = db.query(Product).filter(Product.product_code.like(f"{prefix}%")).order_by(Product.id.desc()).first()
    next_num = 1
    if last_product and last_product.product_code:
        try:
            num_part = last_product.product_code[len(prefix):]
            next_num = int(num_part) + 1
        except ValueError:
            pass
            
    new_product_code = f"{prefix}{next_num:03d}"
    new_product = Product(
    product_code=new_product_code,
    name=clean_name,
    stock=item.stock,
    unit=item.unit,
    category=category_name
)

    new_log = InventoryLog(
    product_name=clean_name,
    category=category_name,
    action="Nhập kho",
    quantity=item.stock,
    user="Admin"
)

    db.add(new_product)
    db.add(new_log)
    write_log(
    db,
    "Nhập kho",
    f"Nhập {item.stock} {item.unit} {clean_name}",
    "Kho")
    db.commit()
    return {"status": "success", "product_code": new_product_code}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    campaign_count = db.query(Campaign).count()
    total_stock = db.query(Product).with_entities(Product.stock).sum() or 0
    return {"user_count": user_count, "campaign_count": campaign_count, "total_stock": total_stock}

# --- API CHIẾN DỊCH ---
@app.get("/api/campaigns")
def get_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).all()
    return {"data": campaigns}

@app.post("/api/campaigns")
async def add_campaign(request: Request, db: Session = Depends(get_db)):
    data = await request.json()

    new_camp = Campaign(
        title=data["title"],
        goal_amount=data["goal_amount"],
        status="Open"
    )

    db.add(new_camp)

    write_log(
        db,
        "Tạo chiến dịch",
        f"Tạo chiến dịch {data['title']}",
        "Chiến dịch"
    )

    db.commit()

    return {"status": "success"}



@app.put("/api/campaigns/{id}")
def update_campaign(id: int, item: dict, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.campaign_id == id).first()
    if not camp:
        return {"status": "error", "message": "Not found"}
    camp.title = item.get("title", camp.title)
    camp.goal_amount = item.get("goal_amount", camp.goal_amount)
    write_log(
    db,
    "Cập nhật chiến dịch",
    f"Cập nhật chiến dịch {camp.title}",
    "Chiến dịch"
)
    db.commit()
    return {"status": "success"}

@app.delete("/api/campaigns/{id}")
def delete_campaign(id: int, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.campaign_id == id).first()
    if camp:
        # 1. Ghi log trước khi xóa
        new_log = SystemLog(
            timestamp="2026-06-23 19:10", # Bạn có thể dùng datetime.now()
            action="Xóa chiến dịch",
            details=f"Đã xóa chiến dịch: {camp.title}",
            page="Chiến dịch",
            actor="Admin"
        )
        db.add(new_log)
        
        # 2. Xóa
        db.delete(camp)
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Not found"}


@app.post("/api/campaigns/{id}/close")
def close_campaign(id: int, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.campaign_id == id).first()
    if not camp:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch")
    
    # Cập nhật trạng thái
    camp.status = "Closed"
    write_log(
    db,
    "Đóng chiến dịch",
    f"Đã đóng chiến dịch {camp.title}",
    "Chiến dịch"
)
    try:
        db.commit()
        return {"status": "success", "message": "Chiến dịch đã đóng"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/inventory-logs")
def get_inventory_logs(db: Session = Depends(get_db)):
    logs = db.query(InventoryLog).all()

    return {
    "data": [
        {
            "timestamp": l.timestamp,
            "product_name": l.product_name,
            "category": l.category,
            "action": l.action,
            "quantity": l.quantity,
            "user": l.user
        }
        for l in logs
    ]
}


@app.get("/api/recipients")
def get_all_recipients(db: Session = Depends(get_db)):
    recipients = db.query(Recipient).all()
    return {"data": recipients}

@app.put("/api/recipients/{id}/approval")
async def update_recipient_approval(id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    recipient = db.query(Recipient).filter(Recipient.id == id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ")
    
    recipient.approval_status = data.get("approval_status")
    write_log(
    db,
    "Duyệt hồ sơ",
    f"Hồ sơ {recipient.name} chuyển sang {data.get('approval_status')}",
    "Người nhận"
)
    db.commit()
    return {"status": "success", "approval_status": recipient.approval_status}


# Thêm vào main.py
@app.get("/api/logs")
def get_logs(db: Session = Depends(get_db)):
    # Giả sử bạn có bảng SystemLog trong database.py
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).all()
    return {
        "data": [
            {
                "timestamp": l.timestamp,
                "action": l.action,
                "details": l.details,
                "page": l.page,
                "actor": l.actor
            } for l in logs
        ]
    }

# --- ĐỊNH TUYẾN FRONTEND ---
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)