# models/conciliacao.py
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class TransacaoBancaria:
    data_transacao: str
    valor_transacao: float
    descricao_transacao: str
    tipo_transacao: str  # "Débito" ou "Crédito"
    conta_bancaria: str
    codigo_banco: str


@dataclass
class ResultadoConciliacao:
    conciliado: bool
    id_lancamento_contabil: Optional[str]
    documento_origem: Optional[str]
    score_confianca: float
    status: str
    divergencias: List[Dict]
    observacoes: List[str]
    metadados_matching: Dict
    needs_human_review: bool
    timestamp: datetime
