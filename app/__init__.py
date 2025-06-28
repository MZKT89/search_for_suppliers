from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'  # 生产环境请更换为安全的密钥
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app