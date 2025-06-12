from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Player, UserType, Training
from app.services.ai_service import PerplexityAIService
from datetime import datetime

player_bp = Blueprint('player', __name__)

def check_player_permission():
    """Verifica se o usuário é um jogador"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.user_type != UserType.PLAYER:
        return False, None, None
    
    player = Player.query.filter_by(user_id=user_id).first()
    if not player:
        return False, None, None
    
    return True, user, player

@player_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_my_profile():
    """Retorna o perfil do jogador"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        player_dict = player.to_dict()
        player_dict['user_info'] = user.to_dict()
        
        # Incluir informações do treinador se houver
        if player.trainer:
            player_dict['trainer_info'] = {
                'id': player.trainer.id,
                'name': f"{player.trainer.first_name} {player.trainer.last_name}",
                'email': player.trainer.email
            }
        
        return jsonify({'player': player_dict}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/trainings', methods=['GET'])
@jwt_required()
def get_my_trainings():
    """Retorna todos os treinos do jogador"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        # Filtros opcionais
        status = request.args.get('status')  # 'completed', 'pending'
        limit = request.args.get('limit', type=int)
        
        query = Training.query.filter_by(player_id=player.id)
        
        # Aplicar filtros
        if status == 'completed':
            query = query.filter_by(is_completed=True)
        elif status == 'pending':
            query = query.filter_by(is_completed=False)
        
        # Ordenar por data de criação (mais recentes primeiro)
        query = query.order_by(Training.created_at.desc())
        
        # Aplicar limite se especificado
        if limit:
            query = query.limit(limit)
        
        trainings = query.all()
        trainings_data = [training.to_dict() for training in trainings]
        
        return jsonify({'trainings': trainings_data}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/trainings/<int:training_id>', methods=['GET'])
@jwt_required()
def get_training_details(training_id):
    """Retorna detalhes de um treino específico"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        training = Training.query.filter_by(id=training_id, player_id=player.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        return jsonify({'training': training.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/trainings/<int:training_id>/complete', methods=['POST'])
@jwt_required()
def mark_training_complete(training_id):
    """Marca um treino como completo"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        training = Training.query.filter_by(id=training_id, player_id=player.id).first()
        if not training:
            return jsonify({'error': 'Treino não encontrado'}), 404
        
        data = request.get_json()
        
        training.is_completed = True
        training.completion_date = datetime.utcnow()
        
        # Atualizar notas do jogador se fornecidas
        if data and data.get('notes'):
            # Adicionar notas aos exercícios específicos ou ao treino geral
            exercise_notes = data.get('exercise_notes', {})
            for exercise in training.exercises:
                if str(exercise.id) in exercise_notes:
                    exercise.notes = exercise_notes[str(exercise.id)]
                    exercise.is_completed = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Treino marcado como completo',
            'training': training.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/exercises/<int:exercise_id>/ai-suggestions', methods=['POST'])
@jwt_required()
def get_exercise_ai_suggestions(exercise_id):
    """Solicita sugestões de exercícios alternativos da AI"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        # Buscar o exercício e verificar se pertence ao jogador
        from app.models import Exercise
        exercise = Exercise.query.join(Training).filter(
            Exercise.id == exercise_id,
            Training.player_id == player.id
        ).first()
        
        if not exercise:
            return jsonify({'error': 'Exercício não encontrado'}), 404
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Solicitar sugestões de exercícios alternativos
        suggestions = ai_service.suggest_exercise_alternatives(
            exercise_name=exercise.name,
            player_position=player.position.value,
            player_weaknesses=player.weaknesses
        )
        
        return jsonify({
            'exercise': exercise.to_dict(),
            'ai_suggestions': suggestions
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/ai-chat', methods=['POST'])
@jwt_required()
def ai_chat():
    """Chat com AI para dúvidas sobre exercícios e treinos"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        data = request.get_json()
        
        if not data.get('message'):
            return jsonify({'error': 'Mensagem é obrigatória'}), 400
        
        message = data['message']
        context = data.get('context', 'general')  # general, exercise, training
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Preparar contexto do jogador
        player_context = f"""
        Jogador: {user.first_name} {user.last_name}
        Posição: {player.position.value}
        Pontos Fortes: {player.strengths or 'Não informado'}
        Pontos Fracos: {player.weaknesses or 'Não informado'}
        """
        
        # Criar prompt contextualizado
        if context == 'exercise':
            system_prompt = f"""Você é um assistente de treino de baseball especializado em exercícios.
            Responda às perguntas do jogador de forma didática e prática.
            
            Contexto do jogador:
            {player_context}
            
            Foque em dar instruções claras e seguras para exercícios."""
        elif context == 'training':
            system_prompt = f"""Você é um assistente de treino de baseball especializado em planejamento de treinos.
            Ajude o jogador com dúvidas sobre seu programa de treinamento.
            
            Contexto do jogador:
            {player_context}
            
            Foque em explicar a importância dos exercícios e como executá-los corretamente."""
        else:
            system_prompt = f"""Você é um assistente especializado em baseball.
            Responda às perguntas do jogador de forma educativa e motivadora.
            
            Contexto do jogador:
            {player_context}
            
            Seja didático e incentive a melhoria contínua."""
        
        # Fazer requisição para AI
        ai_response = ai_service._make_request(message, system_prompt)
        
        return jsonify({
            'message': message,
            'ai_response': ai_response,
            'context': context
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@player_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_player_dashboard():
    """Retorna dados do dashboard do jogador"""
    try:
        is_player, user, player = check_player_permission()
        if not is_player:
            return jsonify({'error': 'Acesso negado. Apenas jogadores podem acessar'}), 403
        
        # Estatísticas de treinos
        total_trainings = Training.query.filter_by(player_id=player.id).count()
        completed_trainings = Training.query.filter_by(player_id=player.id, is_completed=True).count()
        pending_trainings = total_trainings - completed_trainings
        
        # Últimos treinos
        recent_trainings = Training.query.filter_by(player_id=player.id)\
            .order_by(Training.created_at.desc()).limit(5).all()
        
        # Próximos treinos agendados
        from datetime import datetime
        upcoming_trainings = Training.query.filter(
            Training.player_id == player.id,
            Training.scheduled_date > datetime.utcnow(),
            Training.is_completed == False
        ).order_by(Training.scheduled_date.asc()).limit(3).all()
        
        return jsonify({
            'player_info': player.to_dict(),
            'training_stats': {
                'total': total_trainings,
                'completed': completed_trainings,
                'pending': pending_trainings,
                'completion_rate': (completed_trainings / total_trainings * 100) if total_trainings > 0 else 0
            },
            'recent_trainings': [training.to_dict() for training in recent_trainings],
            'upcoming_trainings': [training.to_dict() for training in upcoming_trainings],
            'trainer_info': {
                'name': f"{player.trainer.first_name} {player.trainer.last_name}",
                'email': player.trainer.email
            } if player.trainer else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 