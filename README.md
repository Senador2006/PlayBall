# PlayBall API - Sistema de Autenticação

API REST para sistema de treinamento de baseball com foco em autenticação e cadastro.

## 🚀 Características

- **Cadastro de Treinadores**: Qualquer pessoa pode se cadastrar como treinador
- **Cadastro de Jogadores**: Apenas treinadores podem cadastrar jogadores
- **Login Diferenciado**: Sistema de login que identifica tipo de usuário
- **Relacionamento**: Todo jogador tem um treinador responsável (quem o cadastrou)
- **Autenticação JWT**: Sistema seguro com tokens

## 📋 Requisitos

```bash
pip install -r requirements.txt
```

## 🏃‍♂️ Como Executar

1. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

2. **Executar a API:**
```bash
python run.py
```

3. **Testar os endpoints:**
```bash
python test_auth.py
```

## 🎯 Endpoints Disponíveis

### 1. Cadastro de Treinador
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "treinador_jose",
  "email": "jose@email.com", 
  "password": "senha123",
  "first_name": "José",
  "last_name": "Silva"
}
```

### 2. Cadastro de Jogador (apenas treinadores)
```http
POST /api/auth/register-player
Authorization: Bearer {token_do_treinador}
Content-Type: application/json

{
  "username": "jogador_pedro",
  "email": "pedro@email.com",
  "password": "senha123", 
  "first_name": "Pedro",
  "last_name": "Santos"
}
```

### 3. Login (treinadores e jogadores)
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "treinador_jose",
  "password": "senha123",
  "user_type": "trainer"  // ou "player"
}
```

### 4. Perfil do Usuário
```http
GET /api/auth/profile
Authorization: Bearer {token}
```

### 5. Validar Token
```http
GET /api/auth/validate-token
Authorization: Bearer {token}
```

## 📊 Estrutura do Banco

### Tabela Users
- `id`: Chave primária
- `username`: Nome de usuário único
- `email`: Email único  
- `password_hash`: Senha criptografada
- `user_type`: TRAINER ou PLAYER
- `first_name`, `last_name`: Nome completo
- `is_active`: Status da conta
- `created_at`: Data de criação

### Tabela Players
- `id`: Chave primária
- `user_id`: Referência para Users (único)
- `trainer_id`: Referência para o treinador responsável
- `created_at`: Data de criação

## 🔐 Regras de Negócio

1. **Cadastro Público**: Apenas treinadores podem se cadastrar publicamente
2. **Cadastro de Jogadores**: Só treinadores autenticados podem cadastrar jogadores
3. **Login Tipificado**: Usuário deve informar se é trainer ou player no login
4. **Responsabilidade**: Todo jogador fica vinculado ao treinador que o cadastrou
5. **Validação**: Senhas devem ter pelo menos 6 caracteres com letras e números

## 🧪 Testes

Execute `python test_auth.py` para testar todos os endpoints automaticamente.

O script de teste cria:
- 1 treinador (treinador_jose)
- 1 jogador vinculado ao treinador (jogador_pedro)
- Testa login de ambos
- Verifica perfis

## 📁 Estrutura do Projeto

```
projeto/
├── app/
│   ├── __init__.py          # Configuração da aplicação
│   ├── models.py            # Modelos de dados
│   └── routes/
│       └── auth.py          # Rotas de autenticação
├── requirements.txt         # Dependências
├── run.py                  # Arquivo principal
├── test_auth.py            # Testes automáticos
└── README.md               # Esta documentação
```

## 🎯 Próximos Passos

Esta é a base do sistema. Futuramente poderemos adicionar:
- Gestão de treinos
- Sistema de estatísticas
- Chat entre treinador e jogador
- Integração com IA
- Upload de arquivos #   P l a y B a l l  
 