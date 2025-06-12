from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os

# Inicializar extensões
db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__, static_folder='../static')
    
    # Configurações
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///playball.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Token não expira para desenvolvimento
    app.config['JWT_IDENTITY_CLAIM'] = 'sub'
    
    # Inicializar extensões com app
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins="*")
    
    # Registrar blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Rota para servir a interface
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # Criar tabelas
    with app.app_context():
        db.create_all()
    
    return app 