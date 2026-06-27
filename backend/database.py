import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "giftgive.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Bảng Nhật ký hệ thống (Lưu trữ tất cả các hành động quan trọng của admin)
class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    action = Column(String)
    details = Column(String)
    page = Column(String)
    actor = Column(String)


# Bảng quy định hệ thống (Quản lý luật doanh nghiệp động)
class SystemRegulation(Base):
    __tablename__ = "system_regulations"

    id = Column(Integer, primary_key=True, index=True)
    rule_group = Column(String, index=True)   # Nhóm quy định: LOCK_USER, INVENTORY_CRITERIA...
    rule_code = Column(String, unique=True, index=True) # Mã quy định (Ví dụ: QD-001)
    rule_name = Column(String, nullable=False) # Nội dung chi tiết luật
    value = Column(String, nullable=True)      # Tham số đi kèm nếu có
    is_active = Column(Boolean, default=True)  # Trạng thái áp dụng

# Bảng Sản phẩm (Kho hàng)
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String, unique=True, index=True) 
    name = Column(String)
    stock = Column(Integer)
    unit = Column(String, default="cái")
    category = Column(String, default="Chưa phân loại")

# Bảng Người dùng (Đã bổ sung cột lock_reason)
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    user_code = Column(String, unique=True, index=True)   
    username = Column(String, unique=True)
    full_name = Column(String)
    email = Column(String, unique=True)
    role = Column(String)
    status = Column(String, default="Hoạt động")
    lock_reason = Column(String, nullable=True, default="") # <-- Cột lưu lý do kỷ luật tài khoản
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Bảng Chiến dịch
class Campaign(Base):
    __tablename__ = "campaigns"
    campaign_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    goal_amount = Column(Float)
    status = Column(String, default="Open")

# Bảng Giao dịch/Minh chứng
class Donation(Base):
    __tablename__ = "donations"
    donation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    amount = Column(Float)
    receipt_url = Column(String) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Bảng Người nhận cứu trợ
class Recipient(Base):
    __tablename__ = "recipients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)             
    address = Column(String)          
    description = Column(Text)        
    status = Column(String)           
    approval_status = Column(String, default="Pending") 
    proof_url = Column(String)        
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Nhật ký Kho hàng
class InventoryLog(Base):
    __tablename__ = "inventory_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    product_name = Column(String)
    category = Column(String)
    action = Column(String) 
    quantity = Column(Integer)
    user = Column(String)

# Tạo tất cả các bảng vào file giftgive.db
Base.metadata.create_all(bind=engine)