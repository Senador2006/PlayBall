import requests
import os
from typing import Dict, Optional
import json

class PerplexityAIService:
    def __init__(self):
        self.api_key = os.environ.get('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, prompt: str, system_message: str = None) -> Optional[str]:
        """Faz uma requisição para a API da Perplexity"""
        if not self.api_key:
            return "Erro: Chave da API Perplexity não configurada"
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            return f"Erro na requisição: {str(e)}"
        except KeyError as e:
            return f"Erro na resposta da API: {str(e)}"
    
    def analyze_player_performance(self, player_data: Dict) -> str:
        """Analisa o desempenho de um jogador usando AI"""
        system_message = """Você é um treinador especialista em baseball com mais de 20 anos de experiência. 
        Analise os dados do jogador fornecidos e dê uma análise detalhada sobre:
        1. Pontos fortes do jogador
        2. Áreas que precisam de melhoria
        3. Sugestões específicas de treino
        4. Progressão esperada
        
        Seja específico e técnico, mas também didático."""
        
        prompt = f"""
        Analise este jogador de baseball:
        
        Posição: {player_data.get('position', 'N/A')}
        Time: {player_data.get('team', 'N/A')}
        Pontos Fortes: {player_data.get('strengths', 'N/A')}
        Pontos Fracos: {player_data.get('weaknesses', 'N/A')}
        Batting Average: {player_data.get('batting_average', 'N/A')}
        ERA: {player_data.get('era', 'N/A')}
        Fielding Percentage: {player_data.get('fielding_percentage', 'N/A')}
        Altura: {player_data.get('height', 'N/A')}m
        Peso: {player_data.get('weight', 'N/A')}kg
        Notas Adicionais: {player_data.get('notes', 'N/A')}
        
        Forneça uma análise completa e sugestões de melhoria específicas para este jogador.
        """
        
        return self._make_request(prompt, system_message)
    
    def suggest_exercise_alternatives(self, exercise_name: str, player_position: str, 
                                   player_weaknesses: str = None) -> str:
        """Sugere exercícios alternativos baseados na posição e necessidades do jogador"""
        system_message = """Você é um especialista em condicionamento físico e treinos específicos de baseball.
        Sugira exercícios alternativos eficazes considerando a posição do jogador e suas necessidades específicas.
        Seja detalhado nas instruções e explique os benefícios de cada exercício."""
        
        prompt = f"""
        Um jogador de baseball na posição {player_position} está fazendo o exercício: "{exercise_name}"
        
        {f"Pontos fracos do jogador: {player_weaknesses}" if player_weaknesses else ""}
        
        Sugira 3-5 exercícios alternativos que trabalhem as mesmas habilidades ou músculos, 
        explicando:
        1. Como executar cada exercício
        2. Benefícios específicos para a posição
        3. Número de séries e repetições recomendadas
        4. Equipamentos necessários
        """
        
        return self._make_request(prompt, system_message)
    
    def create_training_plan(self, player_data: Dict, training_goals: str, 
                           duration_weeks: int = 4) -> str:
        """Cria um plano de treino personalizado usando AI"""
        system_message = """Você é um treinador de baseball profissional especializado em periodização de treinos.
        Crie planos de treino detalhados e progressivos considerando a posição, nível e objetivos do jogador."""
        
        prompt = f"""
        Crie um plano de treino de {duration_weeks} semanas para este jogador:
        
        Posição: {player_data.get('position', 'N/A')}
        Pontos Fortes: {player_data.get('strengths', 'N/A')}
        Pontos Fracos: {player_data.get('weaknesses', 'N/A')}
        Objetivos do Treino: {training_goals}
        
        O plano deve incluir:
        1. Periodização semanal
        2. Exercícios específicos por dia
        3. Volume e intensidade
        4. Progressão ao longo das semanas
        5. Dias de descanso e recuperação
        
        Foque em exercícios específicos para a posição e melhoria dos pontos fracos identificados.
        """
        
        return self._make_request(prompt, system_message)
    
    def analyze_csv_data(self, csv_content: str, player_position: str) -> str:
        """Analisa dados estatísticos de CSV do jogador"""
        system_message = """Você é um analista de dados esportivos especializado em baseball.
        Analise os dados estatísticos fornecidos e identifique padrões, tendências e áreas de melhoria."""
        
        prompt = f"""
        Analise estes dados estatísticos de um jogador de baseball na posição {player_position}:
        
        {csv_content}
        
        Forneça uma análise detalhada incluindo:
        1. Tendências de performance
        2. Comparação com médias da posição
        3. Pontos fortes evidenciados pelos dados
        4. Áreas que precisam de atenção
        5. Recomendações específicas de treino baseadas nos dados
        """
        
        return self._make_request(prompt, system_message)
    
    def generate_workout_tips(self, exercise_category: str, difficulty_level: str = "intermediate") -> str:
        """Gera dicas e técnicas para categorias específicas de exercícios"""
        system_message = """Você é um especialista em biomecânica do baseball e preparação física.
        Forneça dicas técnicas detalhadas e correções comuns para exercícios específicos."""
        
        prompt = f"""
        Forneça dicas técnicas detalhadas para exercícios de {exercise_category} no baseball 
        (nível {difficulty_level}):
        
        Inclua:
        1. Técnica correta de execução
        2. Erros mais comuns e como corrigi-los
        3. Variações para diferentes níveis
        4. Dicas de segurança
        5. Como integrar com outros exercícios
        """
        
        return self._make_request(prompt, system_message) 