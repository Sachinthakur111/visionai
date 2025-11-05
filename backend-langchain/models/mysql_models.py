from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from database.mysql_db import Base
import enum
from datetime import datetime

# User roles enum
class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    ANALYST = "analyst"

# Order status enum  
class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed" 
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

# User model for authentication
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Customer model
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(50), index=True)
    state = Column(String(50), index=True)
    country = Column(String(50), index=True, default="USA")
    postal_code = Column(String(10))
    customer_since = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with orders
    orders = relationship("Order", back_populates="customer")

# Order model
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    order_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_amount = Column(Numeric(10, 2), nullable=False, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    product_name = Column(String(200), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), index=True)
    sales_rep = Column(String(100), index=True)
    region = Column(String(50), index=True)
    payment_method = Column(String(50), index=True)
    shipping_address = Column(Text)
    notes = Column(Text)
    shipped_date = Column(DateTime, index=True)
    delivered_date = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with customer
    customer = relationship("Customer", back_populates="orders")