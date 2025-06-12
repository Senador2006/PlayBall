from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Player, UserType, ChatMessage
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Retorna todas as conversas do usuário"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type == UserType.TRAINER:
            # Para treinadores, mostrar conversas com todos os seus jogadores
            conversations = []
            players = Player.query.filter_by(trainer_id=user.id).all()
            
            for player in players:
                # Buscar última mensagem da conversa
                last_message = ChatMessage.query.filter(
                    ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == player.user_id)) |
                    ((ChatMessage.sender_id == player.user_id) & (ChatMessage.receiver_id == user.id))
                ).order_by(ChatMessage.timestamp.desc()).first()
                
                # Contar mensagens não lidas
                unread_count = ChatMessage.query.filter_by(
                    sender_id=player.user_id,
                    receiver_id=user.id,
                    is_read=False
                ).count()
                
                conversations.append({
                    'participant': {
                        'id': player.user.id,
                        'name': f"{player.user.first_name} {player.user.last_name}",
                        'user_type': 'player',
                        'position': player.position.value if player.position else None
                    },
                    'last_message': last_message.to_dict() if last_message else None,
                    'unread_count': unread_count
                })
        
        elif user.user_type == UserType.PLAYER:
            # Para jogadores, mostrar apenas conversa com o treinador
            player = Player.query.filter_by(user_id=user.id).first()
            conversations = []
            
            if player and player.trainer:
                # Buscar última mensagem da conversa
                last_message = ChatMessage.query.filter(
                    ((ChatMessage.sender_id == user.id) & (ChatMessage.receiver_id == player.trainer_id)) |
                    ((ChatMessage.sender_id == player.trainer_id) & (ChatMessage.receiver_id == user.id))
                ).order_by(ChatMessage.timestamp.desc()).first()
                
                # Contar mensagens não lidas
                unread_count = ChatMessage.query.filter_by(
                    sender_id=player.trainer_id,
                    receiver_id=user.id,
                    is_read=False
                ).count()
                
                conversations.append({
                    'participant': {
                        'id': player.trainer.id,
                        'name': f"{player.trainer.first_name} {player.trainer.last_name}",
                        'user_type': 'trainer'
                    },
                    'last_message': last_message.to_dict() if last_message else None,
                    'unread_count': unread_count
                })
        
        return jsonify({'conversations': conversations}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@chat_bp.route('/messages/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_messages(other_user_id):
    """Retorna mensagens de uma conversa específica"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        other_user = User.query.get(other_user_id)
        
        if not other_user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Verificar se a conversa é permitida
        if user.user_type == UserType.TRAINER:
            # Treinador só pode conversar com seus jogadores
            player = Player.query.filter_by(user_id=other_user_id, trainer_id=user.id).first()
            if not player:
                return jsonify({'error': 'Você só pode conversar com seus jogadores'}), 403
        elif user.user_type == UserType.PLAYER:
            # Jogador só pode conversar com seu treinador
            player = Player.query.filter_by(user_id=user.id).first()
            if not player or player.trainer_id != other_user_id:
                return jsonify({'error': 'Você só pode conversar com seu treinador'}), 403
        
        # Buscar mensagens da conversa
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        messages = ChatMessage.query.filter(
            ((ChatMessage.sender_id == user_id) & (ChatMessage.receiver_id == other_user_id)) |
            ((ChatMessage.sender_id == other_user_id) & (ChatMessage.receiver_id == user_id))
        ).order_by(ChatMessage.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Marcar mensagens como lidas
        ChatMessage.query.filter_by(
            sender_id=other_user_id,
            receiver_id=user_id,
            is_read=False
        ).update({'is_read': True})
        db.session.commit()
        
        return jsonify({
            'messages': [msg.to_dict() for msg in reversed(messages.items)],
            'pagination': {
                'page': messages.page,
                'pages': messages.pages,
                'per_page': messages.per_page,
                'total': messages.total,
                'has_next': messages.has_next,
                'has_prev': messages.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@chat_bp.route('/messages', methods=['POST'])
@jwt_required()
def send_message():
    """Envia uma nova mensagem"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not data.get('receiver_id') or not data.get('message'):
            return jsonify({'error': 'ID do destinatário e mensagem são obrigatórios'}), 400
        
        receiver_id = data['receiver_id']
        receiver = User.query.get(receiver_id)
        
        if not receiver:
            return jsonify({'error': 'Destinatário não encontrado'}), 404
        
        # Verificar se a conversa é permitida
        if user.user_type == UserType.TRAINER:
            # Treinador só pode conversar com seus jogadores
            player = Player.query.filter_by(user_id=receiver_id, trainer_id=user.id).first()
            if not player:
                return jsonify({'error': 'Você só pode conversar com seus jogadores'}), 403
        elif user.user_type == UserType.PLAYER:
            # Jogador só pode conversar com seu treinador
            player = Player.query.filter_by(user_id=user.id).first()
            if not player or player.trainer_id != receiver_id:
                return jsonify({'error': 'Você só pode conversar com seu treinador'}), 403
        
        # Criar mensagem
        message = ChatMessage(
            sender_id=user_id,
            receiver_id=receiver_id,
            message=data['message']
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'message': 'Mensagem enviada com sucesso',
            'chat_message': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@chat_bp.route('/messages/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_message_read(message_id):
    """Marca uma mensagem como lida"""
    try:
        user_id = get_jwt_identity()
        
        message = ChatMessage.query.filter_by(
            id=message_id,
            receiver_id=user_id
        ).first()
        
        if not message:
            return jsonify({'error': 'Mensagem não encontrada'}), 404
        
        message.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Mensagem marcada como lida'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@chat_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Retorna o total de mensagens não lidas"""
    try:
        user_id = get_jwt_identity()
        
        unread_count = ChatMessage.query.filter_by(
            receiver_id=user_id,
            is_read=False
        ).count()
        
        return jsonify({'unread_count': unread_count}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500 