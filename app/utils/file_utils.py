import csv
import os
import uuid
from werkzeug.utils import secure_filename
from typing import Dict, List, Tuple
import pandas as pd
from io import StringIO

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'xls'}
ALLOWED_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determina o tipo de arquivo baseado na extensão"""
    if not filename:
        return 'unknown'
    
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    elif ext in ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    elif ext in ALLOWED_DOCUMENT_EXTENSIONS:
        return 'document'
    else:
        return 'unknown'

def generate_unique_filename(filename):
    """Gera um nome único para o arquivo"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return unique_filename

def save_uploaded_file(file, upload_folder):
    """Salva um arquivo enviado e retorna informações sobre ele"""
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Criar diretório se não existir
        os.makedirs(upload_folder, exist_ok=True)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_type = get_file_type(original_filename)
        
        return {
            'filename': unique_filename,
            'original_filename': original_filename,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': file_type
        }
    return None

def process_player_csv(csv_file) -> Tuple[Dict, str]:
    """
    Processa um arquivo CSV com dados do jogador
    Retorna um dicionário com os dados processados e uma string com o conteúdo para análise
    """
    try:
        # Ler o conteúdo do arquivo CSV
        csv_content = csv_file.read().decode('utf-8')
        csv_file.seek(0)  # Reset para poder ler novamente se necessário
        
        # Parse do CSV
        df = pd.read_csv(StringIO(csv_content))
        
        # Dicionário para armazenar dados processados
        processed_data = {
            'raw_csv_content': csv_content,
            'columns': df.columns.tolist(),
            'row_count': len(df),
            'statistics': {}
        }
        
        # Processar estatísticas básicas para colunas numéricas
        numeric_columns = df.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            processed_data['statistics'][col] = {
                'mean': float(df[col].mean()) if not df[col].empty else 0,
                'max': float(df[col].max()) if not df[col].empty else 0,
                'min': float(df[col].min()) if not df[col].empty else 0,
                'std': float(df[col].std()) if not df[col].empty else 0
            }
        
        # Identificar possíveis campos importantes do baseball
        baseball_fields = {
            'batting_average': ['batting_avg', 'avg', 'ba', 'batting_average'],
            'era': ['era', 'earned_run_average'],
            'fielding_percentage': ['fielding_pct', 'fielding_percentage', 'fpct'],
            'home_runs': ['hr', 'home_runs', 'homeruns'],
            'rbi': ['rbi', 'runs_batted_in'],
            'stolen_bases': ['sb', 'stolen_bases'],
            'strikeouts': ['so', 'strikeouts', 'k'],
            'walks': ['bb', 'walks', 'base_on_balls'],
            'hits': ['h', 'hits'],
            'runs': ['r', 'runs'],
            'doubles': ['2b', 'doubles'],
            'triples': ['3b', 'triples']
        }
        
        # Mapear campos do CSV para campos do baseball
        mapped_fields = {}
        for standard_name, possible_names in baseball_fields.items():
            for col in df.columns:
                if col.lower().replace('_', '').replace(' ', '') in [name.replace('_', '').replace(' ', '') for name in possible_names]:
                    if standard_name not in mapped_fields:  # Evitar duplicatas
                        mapped_fields[standard_name] = col
                        break
        
        processed_data['mapped_fields'] = mapped_fields
        
        # Extrair estatísticas específicas do baseball se disponíveis
        baseball_stats = {}
        for standard_name, csv_column in mapped_fields.items():
            if csv_column in df.columns and df[csv_column].dtype in ['int64', 'float64']:
                baseball_stats[standard_name] = {
                    'latest': float(df[csv_column].iloc[-1]) if not df[csv_column].empty else 0,
                    'average': float(df[csv_column].mean()) if not df[csv_column].empty else 0,
                    'best': float(df[csv_column].max()) if not df[csv_column].empty else 0,
                    'trend': calculate_trend(df[csv_column].tolist()) if len(df[csv_column]) > 1 else 'stable'
                }
        
        processed_data['baseball_statistics'] = baseball_stats
        
        return processed_data, csv_content
        
    except Exception as e:
        raise ValueError(f"Erro ao processar CSV: {str(e)}")

def calculate_trend(values: List[float]) -> str:
    """Calcula a tendência dos valores (ascending, descending, stable)"""
    if len(values) < 2:
        return 'stable'
    
    # Calcular a diferença média entre valores consecutivos
    diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
    avg_diff = sum(diffs) / len(diffs)
    
    # Definir limiar para determinar tendência
    threshold = abs(sum(values) / len(values)) * 0.05  # 5% da média
    
    if avg_diff > threshold:
        return 'ascending'
    elif avg_diff < -threshold:
        return 'descending'
    else:
        return 'stable'

def validate_csv_structure(csv_file, required_columns: List[str] = None) -> Tuple[bool, str]:
    """
    Valida a estrutura de um arquivo CSV
    """
    try:
        csv_content = csv_file.read().decode('utf-8')
        csv_file.seek(0)
        
        df = pd.read_csv(StringIO(csv_content))
        
        if df.empty:
            return False, "CSV está vazio"
        
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return False, f"Colunas obrigatórias faltando: {missing_columns}"
        
        return True, "CSV válido"
        
    except Exception as e:
        return False, f"Erro ao validar CSV: {str(e)}"

def format_csv_for_ai_analysis(processed_data: Dict) -> str:
    """
    Formata os dados do CSV para análise da AI
    """
    analysis_text = "ANÁLISE DE DADOS ESTATÍSTICOS DO JOGADOR\n"
    analysis_text += "=" * 50 + "\n\n"
    
    # Informações básicas
    analysis_text += f"Total de registros: {processed_data['row_count']}\n"
    analysis_text += f"Colunas disponíveis: {', '.join(processed_data['columns'])}\n\n"
    
    # Estatísticas de baseball identificadas
    if processed_data.get('baseball_statistics'):
        analysis_text += "ESTATÍSTICAS DE BASEBALL IDENTIFICADAS:\n"
        analysis_text += "-" * 40 + "\n"
        
        for stat_name, stat_data in processed_data['baseball_statistics'].items():
            analysis_text += f"\n{stat_name.upper().replace('_', ' ')}:\n"
            analysis_text += f"  Valor atual: {stat_data['latest']:.3f}\n"
            analysis_text += f"  Média histórica: {stat_data['average']:.3f}\n"
            analysis_text += f"  Melhor marca: {stat_data['best']:.3f}\n"
            analysis_text += f"  Tendência: {stat_data['trend']}\n"
    
    # Outras estatísticas numéricas
    if processed_data.get('statistics'):
        analysis_text += "\n\nOUTRAS ESTATÍSTICAS NUMÉRICAS:\n"
        analysis_text += "-" * 40 + "\n"
        
        for col_name, stats in processed_data['statistics'].items():
            if col_name not in processed_data.get('mapped_fields', {}).values():
                analysis_text += f"\n{col_name}:\n"
                analysis_text += f"  Média: {stats['mean']:.3f}\n"
                analysis_text += f"  Máximo: {stats['max']:.3f}\n"
                analysis_text += f"  Mínimo: {stats['min']:.3f}\n"
                analysis_text += f"  Desvio padrão: {stats['std']:.3f}\n"
    
    return analysis_text 