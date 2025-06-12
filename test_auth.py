import requests
import json

BASE_URL = "http://localhost:5000/api/auth"

def test_register_trainer():
    """Testa o cadastro de treinador"""
    print("🧪 Testando cadastro de treinador...")
    
    data = {
        "username": "treinador_carlos",
        "email": "carlos@email.com",
        "password": "senha123",
        "first_name": "Carlos",
        "last_name": "Silva"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 201:
            return response.json()['access_token']
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_login_trainer():
    """Testa o login de treinador"""
    print("\n🧪 Testando login de treinador...")
    
    data = {
        "username": "treinador_carlos",
        "password": "senha123",
        "user_type": "trainer"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            return response.json()['access_token']
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None

def test_register_player(token):
    """Testa o cadastro de jogador pelo treinador"""
    print("\n🧪 Testando cadastro de jogador...")
    
    data = {
        "username": "jogador_lucas",
        "email": "lucas@email.com",
        "password": "senha123",
        "first_name": "Lucas",
        "last_name": "Santos"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(f"{BASE_URL}/register-player", json=data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 201
    except Exception as e:
        print(f"Erro: {e}")
        return False

def test_login_player():
    """Testa o login de jogador"""
    print("\n🧪 Testando login de jogador...")
    
    data = {
        "username": "jogador_lucas",
        "password": "senha123",
        "user_type": "player"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erro: {e}")
        return False

def test_profile(token, user_type):
    """Testa o endpoint de perfil"""
    print(f"\n🧪 Testando perfil do {user_type}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/profile", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Erro: {e}")
        return False

def main():
    print("🎯 Iniciando testes da API PlayBall")
    print("=" * 50)
    
    # 1. Cadastrar treinador
    trainer_token = test_register_trainer()
    if not trainer_token:
        print("❌ Falha no cadastro do treinador")
        return
    
    # 2. Login treinador
    trainer_token = test_login_trainer()
    if not trainer_token:
        print("❌ Falha no login do treinador")
        return
    
    # 3. Cadastrar jogador
    if not test_register_player(trainer_token):
        print("❌ Falha no cadastro do jogador")
        return
    
    # 4. Login jogador
    if not test_login_player():
        print("❌ Falha no login do jogador")
        return
    
    # 5. Testar perfil do treinador
    test_profile(trainer_token, "treinador")
    
    print("\n✅ Todos os testes concluídos!")

if __name__ == "__main__":
    main() 