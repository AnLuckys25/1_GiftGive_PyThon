import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Xác định thư mục chứa file database.py này
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Kết nối database nằm ngay tại thư mục backend
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'giftgive.db')}"


engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Bảng Sản phẩm (Kho hàng) - Đã có sẵn trong dự án của bạn
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    stock = Column(Integer)
    category = Column(String, default="Chưa phân loại") # Bổ sung cho nghiệp vụ kho

# Bảng Người dùng
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    role = Column(String) # Admin, Donor, Recipient

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
    receipt_url = Column(String) # Lưu link minh chứng online
    created_at = Column(DateTime, default=datetime.utcnow)

# Tạo tất cả các bảng
Base.metadata.create_all(bind=engine)