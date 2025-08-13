# agents/workflow/state.py
from typing import Dict, List, Optional, TypedDict, Any


class ConciliacaoState(TypedDict):
    """
    Estado global compartilhado do workflow de conciliação bancária.
    Utilizado pelo LangGraph para manter dados entre nós.
    """
    # === ENTRADAS PRINCIPAIS ===
    transacao_bancaria: Dict[str, Any]
    """Dados da transação bancária a ser conciliada"""
    
    classificacao_disponivel: Optional[Dict[str, Any]]
    """Classificação fiscal única disponível para matching"""
    
    classificacoes_disponiveis: List[Dict[str, Any]]
    """Lista de classificações para processamento em lote"""
    
    # === DADOS DE PROCESSAMENTO ===
    tipo_transacao: Optional[str]
    """Tipo identificado: normal, taxa_bancaria, lote, parcela, com_retencoes"""
    
    matching_info: Optional[Dict[str, Any]]
    """Informações de scoring e matching fuzzy"""
    
    validacao: Optional[Dict[str, Any]]
    """Resultados da validação contábil e identificação de divergências"""
    
    processamento_especializado: Optional[Dict[str, Any]]
    """Dados específicos para casos especiais (retenções, lote, etc.)"""
    
    # === SAÍDA FINAL ===
    resultado_final: Optional[Dict[str, Any]]
    """Resultado estruturado da conciliação"""
    
    # === METADADOS ===
    criterios_config: Optional[Dict[str, Any]]
    """Configurações de critérios para conciliação"""


class MatchingInfo(TypedDict):
    """Estrutura para informações de matching"""
    score_total: float
    scores_detalhados: Dict[str, float]
    diferenca_valor: float
    diferenca_dias: int
    palavras_encontradas: List[str]


class ValidacaoInfo(TypedDict):
    """Estrutura para informações de validação"""
    pode_conciliar: bool
    validacoes: Dict[str, bool]
    divergencias: List[Dict[str, Any]]
    tipo_transacao: str
    motivo: Optional[str]


class ProcessamentoEspecializado(TypedDict, total=False):
    """Estrutura para processamento especializado"""
    calculo_retencoes: Optional[Dict[str, Any]]
    documentos_conciliados: Optional[List[Dict[str, Any]]]
    totalizacao: Optional[Dict[str, Any]]
    classificacao_sugerida: Optional[Dict[str, Any]]