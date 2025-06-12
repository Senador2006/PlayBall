from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, UserType, AIAnalysis
from app.services.ai_service import PerplexityAIService

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/workout-tips', methods=['POST'])
@jwt_required()
def get_workout_tips():
    """Retorna dicas de treino da AI para uma categoria específica"""
    try:
        data = request.get_json()
        
        if not data.get('category'):
            return jsonify({'error': 'Categoria é obrigatória'}), 400
        
        category = data['category']
        difficulty_level = data.get('difficulty_level', 'intermediate')
        
        # Validar categoria
        valid_categories = ['batting', 'pitching', 'fielding', 'conditioning', 'base_running']
        if category not in valid_categories:
            return jsonify({'error': f'Categoria inválida. Use: {", ".join(valid_categories)}'}), 400
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Obter dicas da AI
        tips = ai_service.generate_workout_tips(category, difficulty_level)
        
        return jsonify({
            'category': category,
            'difficulty_level': difficulty_level,
            'tips': tips
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/exercise-suggestions', methods=['POST'])
@jwt_required()
def get_exercise_suggestions():
    """Sugere exercícios alternativos com base em um exercício específico"""
    try:
        data = request.get_json()
        
        if not data.get('exercise_name'):
            return jsonify({'error': 'Nome do exercício é obrigatório'}), 400
        
        exercise_name = data['exercise_name']
        position = data.get('position', 'general')
        weaknesses = data.get('weaknesses', '')
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Obter sugestões da AI
        suggestions = ai_service.suggest_exercise_alternatives(
            exercise_name=exercise_name,
            player_position=position,
            player_weaknesses=weaknesses
        )
        
        return jsonify({
            'original_exercise': exercise_name,
            'position': position,
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/general-advice', methods=['POST'])
@jwt_required()
def get_general_advice():
    """Chat geral com AI para conselhos de baseball"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not data.get('question'):
            return jsonify({'error': 'Pergunta é obrigatória'}), 400
        
        question = data['question']
        context = data.get('context', 'general')
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Preparar contexto baseado no tipo de usuário
        if user.user_type == UserType.PLAYER:
            from app.models import Player
            player = Player.query.filter_by(user_id=user.id).first()
            if player:
                user_context = f"""
                Usuário: Jogador de baseball
                Nome: {user.first_name} {user.last_name}
                Posição: {player.position.value if player.position else 'Não especificada'}
                Pontos Fortes: {player.strengths or 'Não informado'}
                Pontos Fracos: {player.weaknesses or 'Não informado'}
                """
            else:
                user_context = f"Usuário: Jogador de baseball - {user.first_name} {user.last_name}"
        else:
            user_context = f"Usuário: Treinador de baseball - {user.first_name} {user.last_name}"
        
        # Criar prompt contextualizado
        system_message = f"""Você é um especialista em baseball com vasta experiência em treinamento e desenvolvimento de jogadores.
        Responda de forma educativa, prática e motivadora.
        
        Contexto do usuário:
        {user_context}
        
        Adapte suas respostas ao nível e função do usuário (jogador ou treinador).
        Seja específico e forneça conselhos acionáveis."""
        
        # Fazer requisição para AI
        advice = ai_service._make_request(question, system_message)
        
        return jsonify({
            'question': question,
            'advice': advice,
            'context': context
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/injury-prevention', methods=['POST'])
@jwt_required()
def get_injury_prevention_advice():
    """Dicas de prevenção de lesões específicas do baseball"""
    try:
        data = request.get_json()
        
        position = data.get('position', 'general')
        injury_concern = data.get('injury_concern', 'general')
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Criar prompt específico para prevenção de lesões
        prompt = f"""
        Forneça dicas específicas de prevenção de lesões para um jogador de baseball:
        
        Posição: {position}
        Preocupação específica: {injury_concern}
        
        Inclua:
        1. Exercícios de aquecimento específicos
        2. Técnicas de fortalecimento preventivo
        3. Sinais de alerta para evitar lesões
        4. Dicas de recuperação
        5. Cuidados específicos da posição (se aplicável)
        """
        
        system_message = """Você é um fisioterapeuta esportivo especializado em baseball.
        Forneça conselhos seguros e baseados em evidências científicas.
        Sempre recomende consultar profissionais de saúde para casos específicos."""
        
        advice = ai_service._make_request(prompt, system_message)
        
        return jsonify({
            'position': position,
            'injury_concern': injury_concern,
            'prevention_advice': advice
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/nutrition-advice', methods=['POST'])
@jwt_required()
def get_nutrition_advice():
    """Conselhos nutricionais para jogadores de baseball"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        goal = data.get('goal', 'general')  # performance, weight_gain, weight_loss, recovery
        training_phase = data.get('training_phase', 'in_season')  # pre_season, in_season, off_season
        
        # Obter informações do jogador se disponível
        user_info = ""
        if user.user_type == UserType.PLAYER:
            from app.models import Player
            player = Player.query.filter_by(user_id=user.id).first()
            if player:
                user_info = f"""
                Posição: {player.position.value if player.position else 'Não especificada'}
                Altura: {player.height}m
                Peso: {player.weight}kg
                """ if player.height and player.weight else f"Posição: {player.position.value if player.position else 'Não especificada'}"
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Criar prompt específico para nutrição
        prompt = f"""
        Forneça conselhos nutricionais específicos para um jogador de baseball:
        
        {user_info}
        Objetivo: {goal}
        Fase do treinamento: {training_phase}
        
        Inclua:
        1. Plano alimentar geral
        2. Nutrição pré-treino
        3. Nutrição pós-treino
        4. Hidratação
        5. Suplementação (se necessária)
        6. Timing das refeições
        7. Alimentos específicos para o objetivo
        """
        
        system_message = """Você é um nutricionista esportivo especializado em esportes de alta performance.
        Forneça conselhos seguros e baseados em evidências científicas.
        Sempre recomende consultar um nutricionista para planos personalizados."""
        
        advice = ai_service._make_request(prompt, system_message)
        
        return jsonify({
            'goal': goal,
            'training_phase': training_phase,
            'nutrition_advice': advice
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/mental-training', methods=['POST'])
@jwt_required()
def get_mental_training_advice():
    """Conselhos de preparação mental para baseball"""
    try:
        data = request.get_json()
        
        focus_area = data.get('focus_area', 'general')  # confidence, concentration, pressure, visualization
        situation = data.get('situation', 'general')  # at_bat, pitching, fielding, game_situation
        
        # Inicializar serviço de AI
        ai_service = PerplexityAIService()
        
        # Criar prompt específico para preparação mental
        prompt = f"""
        Forneça técnicas de preparação mental específicas para baseball:
        
        Área de foco: {focus_area}
        Situação específica: {situation}
        
        Inclua:
        1. Técnicas de respiração
        2. Exercícios de visualização
        3. Estratégias de concentração
        4. Controle de ansiedade
        5. Construção de confiança
        6. Rotinas pré-jogo/pré-situação
        7. Como lidar com erros
        """
        
        system_message = """Você é um psicólogo esportivo especializado em baseball.
        Forneça técnicas práticas e aplicáveis baseadas na psicologia esportiva moderna.
        Foque em estratégias que podem ser implementadas imediatamente."""
        
        advice = ai_service._make_request(prompt, system_message)
        
        return jsonify({
            'focus_area': focus_area,
            'situation': situation,
            'mental_training_advice': advice
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@ai_bp.route('/analysis-history', methods=['GET'])
@jwt_required()
def get_analysis_history():
    """Retorna histórico de análises de AI do usuário"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type == UserType.TRAINER:
            # Treinadores veem análises que criaram
            analyses = AIAnalysis.query.filter_by(trainer_id=user.id)\
                .order_by(AIAnalysis.created_at.desc()).limit(20).all()
        elif user.user_type == UserType.PLAYER:
            # Jogadores veem análises sobre eles
            from app.models import Player
            player = Player.query.filter_by(user_id=user.id).first()
            if player:
                analyses = AIAnalysis.query.filter_by(player_id=player.id)\
                    .order_by(AIAnalysis.created_at.desc()).limit(20).all()
            else:
                analyses = []
        else:
            analyses = []
        
        return jsonify({
            'analyses': [analysis.to_dict() for analysis in analyses]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 