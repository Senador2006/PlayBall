from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from app.models import User, Player, UserType
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    """Valida formato do email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """Valida se a senha é forte o suficiente"""
    if len(password) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"
    if not re.search(r'[A-Za-z]', password):
        return False, "Senha deve conter pelo menos uma letra"
    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos um número"
    return True, "Senha válida"

@auth_bp.route('/register', methods=['POST'])
def register_trainer():
    """Registra um novo TREINADOR (apenas treinadores podem se cadastrar)"""
    try:
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Validar email
        if not is_valid_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        # Validar senha
        is_valid, message = is_strong_password(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Verificar se username ou email já existem
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            if existing_user.username == data['username']:
                return jsonify({'error': 'Username já existe'}), 409
            else:
                return jsonify({'error': 'Email já está em uso'}), 409
        
        # Criar novo TREINADOR
        user = User(
            username=data['username'],
            email=data['email'],
            user_type=UserType.TRAINER,  # Sempre TRAINER no cadastro público
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Criar token de acesso
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Treinador registrado com sucesso',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/register-player', methods=['POST'])
@jwt_required()
def register_player():
    """Registra um novo JOGADOR (apenas treinadores podem cadastrar jogadores)"""
    try:
        # Verificar se quem está fazendo a requisição é um treinador
        current_user_id = int(get_jwt_identity())
        trainer = User.query.get(current_user_id)
        
        if not trainer or trainer.user_type != UserType.TRAINER:
            return jsonify({'error': 'Apenas treinadores podem cadastrar jogadores'}), 403
        
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Validar email
        if not is_valid_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        # Validar senha
        is_valid, message = is_strong_password(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Verificar se username ou email já existem
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            if existing_user.username == data['username']:
                return jsonify({'error': 'Username já existe'}), 409
            else:
                return jsonify({'error': 'Email já está em uso'}), 409
        
        # Criar novo JOGADOR
        user = User(
            username=data['username'],
            email=data['email'],
            user_type=UserType.PLAYER,  # Sempre PLAYER
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Para obter o ID do usuário
        
        # Criar perfil de jogador vinculado ao treinador
        player = Player(
            user_id=user.id,
            trainer_id=trainer.id  # O treinador que cadastrou vira responsável
        )
        
        db.session.add(player)
        db.session.commit()
        
        return jsonify({
            'message': 'Jogador cadastrado com sucesso',
            'user': user.to_dict(),
            'player': player.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login para TREINADORES e JOGADORES"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password') or not data.get('user_type'):
            return jsonify({'error': 'Username, senha e tipo de usuário são obrigatórios'}), 400
        
        # Validar tipo de usuário
        user_type = data['user_type'].lower()
        if user_type not in ['trainer', 'player']:
            return jsonify({'error': 'Tipo de usuário deve ser "trainer" ou "player"'}), 400
        
        # Buscar usuário por username ou email
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Credenciais inválidas'}), 401
        
        # Verificar se o tipo de usuário bate
        if user.user_type.value != user_type:
            return jsonify({'error': f'Usuário não é um {user_type}'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Conta desativada'}), 403
        
        # Criar token de acesso
        access_token = create_access_token(identity=str(user.id))
        
        # Informações extras para jogadores
        extra_info = {}
        if user.user_type == UserType.PLAYER:
            player = Player.query.filter_by(user_id=user.id).first()
            if player:
                extra_info['player_info'] = player.to_dict()
                extra_info['trainer_info'] = player.trainer.to_dict() if player.trainer else None
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'access_token': access_token,
            **extra_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Retorna o perfil do usuário autenticado"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        response_data = {'user': user.to_dict()}
        
        # Adicionar informações extras para jogadores
        if user.user_type == UserType.PLAYER:
            player = Player.query.filter_by(user_id=user.id).first()
            if player:
                response_data['player_info'] = player.to_dict()
                response_data['trainer_info'] = player.trainer.to_dict() if player.trainer else None
        
        # Adicionar informações extras para treinadores
        elif user.user_type == UserType.TRAINER:
            players = Player.query.filter_by(trainer_id=user.id).all()
            response_data['my_players'] = [p.to_dict() for p in players]
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Atualiza o perfil do usuário autenticado"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        # Campos que podem ser atualizados
        updatable_fields = ['first_name', 'last_name', 'email']
        
        for field in updatable_fields:
            if field in data:
                if field == 'email':
                    # Validar novo email
                    if not is_valid_email(data['email']):
                        return jsonify({'error': 'Email inválido'}), 400
                    
                    # Verificar se email já está em uso por outro usuário
                    existing_user = User.query.filter(
                        User.email == data['email'],
                        User.id != user_id
                    ).first()
                    
                    if existing_user:
                        return jsonify({'error': 'Email já está em uso'}), 409
                
                setattr(user, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Altera a senha do usuário"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
        
        # Verificar senha atual
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Senha atual incorreta'}), 401
        
        # Validar nova senha
        is_valid, message = is_strong_password(data['new_password'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Atualizar senha
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Senha alterada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/validate-token', methods=['GET'])
@jwt_required()
def validate_token():
    """Valida se o token está válido e retorna informações básicas do usuário"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Token inválido'}), 401
        
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 