-- Initialize MySQL database for Order Analytics System
CREATE DATABASE IF NOT EXISTS order_analytics;
USE order_analytics;

-- Grant permissions
GRANT ALL PRIVILEGES ON order_analytics.* TO 'analytics_user'@'%';
GRANT ALL PRIVILEGES ON order_analytics.* TO 'root'@'%';
FLUSH PRIVILEGES;

-- The tables will be created by SQLAlchemy when the application starts