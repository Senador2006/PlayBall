from app import create_app
import os

app = create_app()  # Necessário para o Gunicorn

if __name__ == '__main__':
    # Configuração para desenvolvimento
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Iniciando PlayBall API...")
    print(f"📍 URL: http://localhost:{port}")
    print("📚 Endpoints disponíveis:")
    print("   POST /api/auth/register - Cadastro de treinadores")
    print("   POST /api/auth/register-player - Cadastro de jogadores (só treinadores)")
    print("   POST /api/auth/login - Login (treinadores e jogadores)")
    print("   GET  /api/auth/profile - Perfil do usuário logado")
    print("   GET  /api/auth/validate-token - Validar token")
    
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=port
    ) 