from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, UserType, Training, Exercise, Player, MediaFile
from app.utils.file_utils import save_uploaded_file
from datetime import datetime

training_bp = Blueprint('training', __name__)

def check_trainer_permission():
    """Verifica se o usuário é um treinador"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.user_type != UserType.TRAINER:
        return False, None
    return True, user

@training_bp.route('/', methods=['POST'])
@jwt_required()
def create_training():
    """Cria um novo treino"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem criar treinos'}), 403
        
        data = request.get_json()
        
        # Validar campos obrigatórios
        required_fields = ['title', 'player_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Verificar se o jogador pertence ao treinador
        player = Player.query.filter_by(id=data['player_id'], trainer_id=trainer.id).first()
        if not player:
            return jsonify({'error': 'Jogador não encontrado ou não pertence a você'}), 404
        
        # Criar treino
        training = Training(
            title=data['title'],
            description=data.get('description'),
            trainer_id=trainer.id,
            player_id=player.id,
            scheduled_date=datetime.strptime(data['scheduled_date'], '%Y-%m-%d %H:%M:%S') if data.get('scheduled_date') else None,
            duration_minutes=data.get('duration_minutes')
        )
        
        db.session.add(training)
        db.session.flush()  # Para obter o ID do treino
        
        # Adicionar exercícios se fornecidos
        exercises_data = data.get('exercises', [])
        for i, exercise_data in enumerate(exercises_data):
            exercise = Exercise(
                training_id=training.id,
                name=exercise_data['name'],
                description=exercise_data.get('description'),
                category=exercise_data.get('category'),
                sets=exercise_data.get('sets'),
                reps=exercise_data.get('reps'),
                duration_minutes=exercise_data.get('duration_minutes'),
                rest_seconds=exercise_data.get('rest_seconds'),
                order_index=i
            )
            db.session.add(exercise)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Treino criado com sucesso',
            'training': training.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/<int:training_id>', methods=['GET'])
@jwt_required()
def get_training(training_id):
    """Retorna detalhes de um treino"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type == UserType.TRAINER:
            # Treinador pode ver treinos que criou
            training = Training.query.filter_by(id=training_id, trainer_id=user.id).first()
        elif user.user_type == UserType.PLAYER:
            # Jogador pode ver seus próprios treinos
            player = Player.query.filter_by(user_id=user.id).first()
            training = Training.query.filter_by(id=training_id, player_id=player.id).first()
        else:
            return jsonify({'error': 'Acesso negado'}), 403
        
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        return jsonify({'training': training.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/<int:training_id>', methods=['PUT'])
@jwt_required()
def update_training(training_id):
    """Atualiza um treino (apenas treinadores)"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem editar treinos'}), 403
        
        training = Training.query.filter_by(id=training_id, trainer_id=trainer.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        data = request.get_json()
        
        # Campos que podem ser atualizados
        updatable_fields = ['title', 'description', 'scheduled_date', 'duration_minutes']
        
        for field in updatable_fields:
            if field in data:
                if field == 'scheduled_date' and data[field]:
                    training.scheduled_date = datetime.strptime(data[field], '%Y-%m-%d %H:%M:%S')
                else:
                    setattr(training, field, data[field])
        
        # Atualizar exercícios se fornecidos
        if 'exercises' in data:
            # Remover exercícios existentes
            for exercise in training.exercises:
                db.session.delete(exercise)
            
            # Adicionar novos exercícios
            for i, exercise_data in enumerate(data['exercises']):
                exercise = Exercise(
                    training_id=training.id,
                    name=exercise_data['name'],
                    description=exercise_data.get('description'),
                    category=exercise_data.get('category'),
                    sets=exercise_data.get('sets'),
                    reps=exercise_data.get('reps'),
                    duration_minutes=exercise_data.get('duration_minutes'),
                    rest_seconds=exercise_data.get('rest_seconds'),
                    order_index=i
                )
                db.session.add(exercise)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Treino atualizado com sucesso',
            'training': training.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/<int:training_id>', methods=['DELETE'])
@jwt_required()
def delete_training(training_id):
    """Remove um treino (apenas treinadores)"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem deletar treinos'}), 403
        
        training = Training.query.filter_by(id=training_id, trainer_id=trainer.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        db.session.delete(training)
        db.session.commit()
        
        return jsonify({'message': 'Treino removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/<int:training_id>/exercises', methods=['POST'])
@jwt_required()
def add_exercise_to_training(training_id):
    """Adiciona um exercício a um treino"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem adicionar exercícios'}), 403
        
        training = Training.query.filter_by(id=training_id, trainer_id=trainer.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Nome do exercício é obrigatório'}), 400
        
        # Determinar ordem do exercício
        max_order = db.session.query(db.func.max(Exercise.order_index))\
            .filter_by(training_id=training.id).scalar() or 0
        
        exercise = Exercise(
            training_id=training.id,
            name=data['name'],
            description=data.get('description'),
            category=data.get('category'),
            sets=data.get('sets'),
            reps=data.get('reps'),
            duration_minutes=data.get('duration_minutes'),
            rest_seconds=data.get('rest_seconds'),
            order_index=max_order + 1
        )
        
        db.session.add(exercise)
        db.session.commit()
        
        return jsonify({
            'message': 'Exercício adicionado com sucesso',
            'exercise': exercise.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/exercises/<int:exercise_id>', methods=['PUT'])
@jwt_required()
def update_exercise(exercise_id):
    """Atualiza um exercício"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem editar exercícios'}), 403
        
        exercise = Exercise.query.join(Training).filter(
            Exercise.id == exercise_id,
            Training.trainer_id == trainer.id
        ).first()
        
        if not exercise:
            return jsonify({'error': 'Exercício não encontrado'}), 404
        
        data = request.get_json()
        
        # Campos que podem ser atualizados
        updatable_fields = ['name', 'description', 'category', 'sets', 'reps', 
                           'duration_minutes', 'rest_seconds', 'order_index']
        
        for field in updatable_fields:
            if field in data:
                setattr(exercise, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Exercício atualizado com sucesso',
            'exercise': exercise.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/exercises/<int:exercise_id>', methods=['DELETE'])
@jwt_required()
def delete_exercise(exercise_id):
    """Remove um exercício"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem deletar exercícios'}), 403
        
        exercise = Exercise.query.join(Training).filter(
            Exercise.id == exercise_id,
            Training.trainer_id == trainer.id
        ).first()
        
        if not exercise:
            return jsonify({'error': 'Exercício não encontrado'}), 404
        
        db.session.delete(exercise)
        db.session.commit()
        
        return jsonify({'message': 'Exercício removido com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/<int:training_id>/media', methods=['POST'])
@jwt_required()
def upload_training_media(training_id):
    """Upload de arquivos de mídia para um treino"""
    try:
        is_trainer, trainer = check_trainer_permission()
        if not is_trainer:
            return jsonify({'error': 'Acesso negado. Apenas treinadores podem fazer upload'}), 403
        
        training = Training.query.filter_by(id=training_id, trainer_id=trainer.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Salvar arquivo
        upload_folder = current_app.config['UPLOAD_FOLDER']
        file_info = save_uploaded_file(file, upload_folder)
        
        if not file_info:
            return jsonify({'error': 'Arquivo inválido'}), 400
        
        # Criar registro no banco
        media_file = MediaFile(
            training_id=training.id,
            filename=file_info['filename'],
            original_filename=file_info['original_filename'],
            file_path=file_info['file_path'],
            file_type=file_info['file_type'],
            file_size=file_info['file_size'],
            uploaded_by=trainer.id
        )
        
        db.session.add(media_file)
        db.session.commit()
        
        return jsonify({
            'message': 'Arquivo enviado com sucesso',
            'media_file': media_file.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@training_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_training_templates():
    """Retorna templates de treino pré-definidos"""
    try:
        # Templates básicos de treino por categoria
        templates = {
            'batting': {
                'name': 'Treino de Rebatida',
                'description': 'Foco no aprimoramento da técnica de rebatida',
                'exercises': [
                    {
                        'name': 'Aquecimento com Tee',
                        'description': 'Rebatidas no tee para aquecimento',
                        'category': 'batting',
                        'sets': 3,
                        'reps': 10,
                        'rest_seconds': 60
                    },
                    {
                        'name': 'Soft Toss',
                        'description': 'Rebatidas com lançamentos suaves',
                        'category': 'batting',
                        'sets': 3,
                        'reps': 15,
                        'rest_seconds': 90
                    },
                    {
                        'name': 'Batting Practice',
                        'description': 'Prática de rebatida com lançamentos variados',
                        'category': 'batting',
                        'sets': 5,
                        'reps': 20,
                        'rest_seconds': 120
                    }
                ]
            },
            'pitching': {
                'name': 'Treino de Arremesso',
                'description': 'Desenvolvimento da técnica e força do arremesso',
                'exercises': [
                    {
                        'name': 'Aquecimento de Braço',
                        'description': 'Movimentos circulares e alongamento',
                        'category': 'pitching',
                        'duration_minutes': 10
                    },
                    {
                        'name': 'Arremessos Curtos',
                        'description': 'Arremessos de curta distância',
                        'category': 'pitching',
                        'sets': 3,
                        'reps': 15,
                        'rest_seconds': 60
                    },
                    {
                        'name': 'Bullpen Session',
                        'description': 'Sessão de arremessos no monte',
                        'category': 'pitching',
                        'sets': 4,
                        'reps': 25,
                        'rest_seconds': 180
                    }
                ]
            },
            'fielding': {
                'name': 'Treino de Defesa',
                'description': 'Aprimoramento das habilidades defensivas',
                'exercises': [
                    {
                        'name': 'Ground Balls',
                        'description': 'Pegadas de bolas rasteiras',
                        'category': 'fielding',
                        'sets': 4,
                        'reps': 20,
                        'rest_seconds': 90
                    },
                    {
                        'name': 'Fly Balls',
                        'description': 'Pegadas de bolas aéreas',
                        'category': 'fielding',
                        'sets': 3,
                        'reps': 15,
                        'rest_seconds': 120
                    },
                    {
                        'name': 'Double Play Practice',
                        'description': 'Prática de jogadas duplas',
                        'category': 'fielding',
                        'sets': 5,
                        'reps': 10,
                        'rest_seconds': 150
                    }
                ]
            },
            'conditioning': {
                'name': 'Condicionamento Físico',
                'description': 'Treino focado no condicionamento físico geral',
                'exercises': [
                    {
                        'name': 'Corrida Base a Base',
                        'description': 'Sprints entre as bases',
                        'category': 'conditioning',
                        'sets': 4,
                        'reps': 8,
                        'rest_seconds': 90
                    },
                    {
                        'name': 'Agility Ladder',
                        'description': 'Treino de agilidade com escada',
                        'category': 'conditioning',
                        'duration_minutes': 15,
                        'rest_seconds': 60
                    },
                    {
                        'name': 'Pliometria',
                        'description': 'Exercícios pliométricos para potência',
                        'category': 'conditioning',
                        'sets': 3,
                        'reps': 12,
                        'rest_seconds': 120
                    }
                ]
            }
        }
        
        return jsonify({'templates': templates}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 