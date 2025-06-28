from flask import Flask
import os
from .utils import create_directories

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key'  
    
    # 注册蓝图
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    create_directories()
    
    return app