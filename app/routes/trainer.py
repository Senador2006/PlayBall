from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Player, UserType, Position
from app.utils.file_utils import process_player_csv, validate_csv_structure, format_csv_for_ai_analysis
from app.services.ai_service import PerplexityAIService
from datetime import datetime
import json

trainer_bp = Blueprint('trainer', __name__)

def check_trainer_permission():
    """Verifica se o usuário é um treinador"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.user_type != UserType.TRAINER:
        return False, None
    return True, user

@trainer_bp.route('/players', methods=['GET'])
@jwt_required()
def get_my_players():
    """Retorna todos os jogadores do treinador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        players = Player.query.filter_by(trainer_id=trainer.id).all()
        players_data = []
        
        for player in players:
            player_dict = player.to_dict()
            player_dict['user_info'] = player.user.to_dict()
            players_data.append(player_dict)
        
        return jsonify({'players': players_data}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/players', methods=['POST'])
@jwt_required()
def create_player():
    """Cadastra um novo jogador com formulário completo"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'position']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Validar posição
        try:
            position = Position(data['position'].lower())
        except ValueError:
            return jsonify({'error': 'Posição inválida'}), 400
        
        # Verificar se username ou email já existem
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Username ou email já existe'}), 409
        
        # Criar usuário jogador
        user = User(
            username=data['username'],
            email=data['email'],
            user_type=UserType.PLAYER,
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Para obter o ID do usuário
        
        # Criar perfil do jogador
        player = Player(
            user_id=user.id,
            trainer_id=trainer.id,
            position=position,
            team=data.get('team'),
            jersey_number=data.get('jersey_number'),
            height=data.get('height'),
            weight=data.get('weight'),
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date() if data.get('birth_date') else None,
            strengths=data.get('strengths'),
            weaknesses=data.get('weaknesses'),
            batting_average=data.get('batting_average'),
            era=data.get('era'),
            fielding_percentage=data.get('fielding_percentage'),
            notes=data.get('notes')
        )
        
        db.session.add(player)
        db.session.commit()
        
        # Retornar dados completos
        player_dict = player.to_dict()
        player_dict['user_info'] = user.to_dict()
        
        return jsonify({
            'message': 'Jogador cadastrado com sucesso',
            'player': player_dict
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/players/<int:player_id>/csv-upload', methods=['POST'])
@jwt_required()
def upload_player_csv(player_id):
    """Upload de arquivo CSV com dados estatísticos do jogador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        # Verificar se o jogador pertence ao treinador
        player = Player.query.filter_by(id=player_id, trainer_id=trainer.id).first()
        if not player:
            return jsonify({'error': 'Jogador não encontrado ou não pertence a você'}), 404
        
        # Verificar se foi enviado um arquivo
        if 'csv_file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo CSV enviado'}), 400
        
        csv_file = request.files['csv_file']
        
        if csv_file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if not csv_file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'Arquivo deve ser um CSV'}), 400
        
        # Validar estrutura do CSV
        is_valid, validation_message = validate_csv_structure(csv_file)
        if not is_valid:
            return jsonify({'error': validation_message}), 400
        
        # Processar CSV
        try:
            processed_data, csv_content = process_player_csv(csv_file)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Atualizar dados do jogador com informações do CSV
        player.csv_data = json.dumps(processed_data)
        
        # Atualizar estatísticas específicas se disponíveis
        baseball_stats = processed_data.get('baseball_statistics', {})
        if 'batting_average' in baseball_stats:
            player.batting_average = baseball_stats['batting_average']['latest']
        if 'era' in baseball_stats:
            player.era = baseball_stats['era']['latest']
        if 'fielding_percentage' in baseball_stats:
            player.fielding_percentage = baseball_stats['fielding_percentage']['latest']
        
        db.session.commit()
        
        return jsonify({
            'message': 'CSV processado com sucesso',
            'processed_data': processed_data,
            'player': player.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/players/<int:player_id>', methods=['PUT'])
@jwt_required()
def update_player(player_id):
    """Atualiza informações de um jogador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        # Verificar se o jogador pertence ao treinador
        player = Player.query.filter_by(id=player_id, trainer_id=trainer.id).first()
        if not player:
            return jsonify({'error': 'Jogador não encontrado ou não pertence a você'}), 404
        
        data = request.get_json()
        
        # Campos que podem ser atualizados
        updatable_fields = [
            'position', 'team', 'jersey_number', 'height', 'weight', 
            'birth_date', 'strengths', 'weaknesses', 'batting_average', 
            'era', 'fielding_percentage', 'notes'
        ]
        
        for field in updatable_fields:
            if field in data:
                if field == 'position':
                    try:
                        position = Position(data['position'].lower())
                        player.position = position
                    except ValueError:
                        return jsonify({'error': 'Posição inválida'}), 400
                elif field == 'birth_date' and data[field]:
                    player.birth_date = datetime.strptime(data[field], '%Y-%m-%d').date()
                else:
                    setattr(player, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Jogador atualizado com sucesso',
            'player': player.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/players/<int:player_id>', methods=['GET'])
@jwt_required()
def get_player_details(player_id):
    """Retorna detalhes completos de um jogador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        # Verificar se o jogador pertence ao treinador
        player = Player.query.filter_by(id=player_id, trainer_id=trainer.id).first()
        if not player:
            return jsonify({'error': 'Jogador não encontrado ou não pertence a você'}), 404
        
        player_dict = player.to_dict()
        player_dict['user_info'] = player.user.to_dict()
        
        # Incluir dados do CSV se existirem
        if player.csv_data:
            player_dict['csv_analysis'] = json.loads(player.csv_data)
        
        # Incluir histórico de treinos
        player_dict['trainings'] = [training.to_dict() for training in player.trainings]
        
        return jsonify({'player': player_dict}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/players/<int:player_id>/ai-analysis', methods=['POST'])
@jwt_required()
def request_ai_analysis(player_id):
    """Solicita análise de AI para um jogador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        # Verificar se o jogador pertence ao treinador
        player = Player.query.filter_by(id=player_id, trainer_id=trainer.id).first()
        if not player:
            return jsonify({'error': 'Jogador não encontrado ou não pertence a você'}), 404
        
        data = request.get_json()
        analysis_type = data.get('analysis_type', 'performance')
        
        # Preparar dados do jogador para análise
        player_data = player.to_dict()
        
        # Incluir dados do CSV se disponíveis
        if player.csv_data:
            csv_data = json.loads(player.csv_data)
            formatted_csv = format_csv_for_ai_analysis(csv_data)
        else:
            formatted_csv = None
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Realizar análise baseada no tipo
        if analysis_type == 'performance':
            ai_response = ai_service.analyze_player_performance(player_data)
        elif analysis_type == 'csv_analysis' and formatted_csv:
            ai_response = ai_service.analyze_csv_data(formatted_csv, player_data.get('position', ''))
        elif analysis_type == 'training_plan':
            training_goals = data.get('training_goals', 'Melhoria geral de performance')
            duration_weeks = data.get('duration_weeks', 4)
            ai_response = ai_service.create_training_plan(player_data, training_goals, duration_weeks)
        else:
            return jsonify({'error': 'Tipo de análise inválido ou dados insuficientes'}), 400
        
        # Salvar análise no banco (opcional)
        from app.models import AIAnalysis
        analysis = AIAnalysis(
            player_id=player.id,
            trainer_id=trainer.id,
            analysis_type=analysis_type,
            prompt=f"Análise {analysis_type} para jogador {player.user.first_name} {player.user.last_name}",
            response=ai_response
        )
        
        db.session.add(analysis)
        db.session.commit()
        
        return jsonify({
            'analysis': ai_response,
            'analysis_id': analysis.id,
            'analysis_type': analysis_type
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@trainer_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_trainer_dashboard():
    """Retorna dados do dashboard do treinador"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem acessar'}), 403
        
        # Estatísticas básicas
        total_players = Player.query.filter_by(trainer_id=trainer.id).count()
        
        # Contagem por posição
        from sqlalchemy import func
        position_counts = db.session.query(
            Player.position, func.count(Player.id)
        ).filter_by(trainer_id=trainer.id).group_by(Player.position).all()
        
        position_stats = {pos.value: count for pos, count in position_counts}
        
        # Treinos recentes
        from app.models import Training
        recent_trainings = Training.query.filter_by(trainer_id=trainer.id)\
            .order_by(Training.created_at.desc()).limit(5).all()
        
        return jsonify({
            'total_players': total_players,
            'position_distribution': position_stats,
            'recent_trainings': [training.to_dict() for training in recent_trainings],
            'trainer_info': trainer.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 