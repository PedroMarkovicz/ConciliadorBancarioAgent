# agents/conciliador_bancario.py
from typing import Dict, Any
from .workflow.graph import create_conciliacao_graph
from .workflow.state import ConciliacaoState


class ConciliadorBancarioAgent:
    """
    Agente de Conciliação Bancária baseado em LangGraph.
    
    Orquestra um workflow modular para processar transações bancárias
    e realizar conciliações inteligentes com documentos fiscais.
    """
    
    def __init__(self):
        """Inicializa o agente com configurações padrão e workflow LangGraph."""
        self.criterios_config = {
            "tolerancia_valor_percentual": 0.05,  # 5%
            "tolerancia_valor_absoluta": 50.00,   # R$ 50
            "janela_data_dias": 7,
            "score_minimo": 0.60,
            "palavras_irrelevantes": {
                "ted", "pix", "pgto", "boleto", "doc", "transferencia"
            }
        }
        
        # Inicializar workflow LangGraph
        self.workflow = create_conciliacao_graph()
    
    def conciliar(self, estado_global: Dict) -> Dict[str, Any]:
        """
        Método principal de conciliação compatível com a interface original.
        
        Args:
            estado_global: Dicionário contendo:
                - transacao_bancaria: dados da transação
                - classificacao_disponivel: classificação única (opcional)
                - classificacoes_disponiveis: múltiplas classificações (opcional)
        
        Returns:
            Dict com resultado estruturado da conciliação
        """
        
        # Converter entrada para o estado tipado do LangGraph
        initial_state = ConciliacaoState(
            transacao_bancaria=estado_global.get("transacao_bancaria", {}),
            classificacao_disponivel=estado_global.get("classificacao_disponivel"),
            classificacoes_disponiveis=estado_global.get("classificacoes_disponiveis", []),
            tipo_transacao=None,
            matching_info=None,
            validacao=None,
            processamento_especializado=None,
            resultado_final=None,
            criterios_config=self.criterios_config
        )
        
        try:
            # Executar o workflow LangGraph
            final_state = self.workflow.invoke(initial_state)
            
            # Extrair resultado final
            resultado = final_state.get("resultado_final")
            
            if not resultado:
                # Fallback em caso de erro
                resultado = {
                    "conciliacao_ok": False,
                    "conciliacao": {
                        "conciliado": False,
                        "score_confianca": 0.0,
                        "status": "Erro_Processamento",
                        "observacoes": ["Erro interno durante processamento"]
                    },
                    "confianca": 0.0,
                    "needs_human_review": True,
                    "rule_version": "v1.0"
                }
            
            # Manter compatibilidade com a interface original
            # Atualizar o estado global com o resultado
            novo_estado = estado_global.copy()
            novo_estado.update(resultado)
            
            return novo_estado
            
        except Exception as e:
            # Tratamento de erro com fallback
            return {
                **estado_global,
                "conciliacao_ok": False,
                "conciliacao": {
                    "conciliado": False,
                    "score_confianca": 0.0,
                    "status": "Erro_Processamento",
                    "observacoes": [f"Erro durante execução: {str(e)}"]
                },
                "confianca": 0.0,
                "needs_human_review": True,
                "rule_version": "v1.0",
                "error": str(e)
            }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o workflow LangGraph para debugging.
        """
        return {
            "workflow_type": "LangGraph StateGraph",
            "nodes": [
                "identificar_tipo",
                "calcular_matching", 
                "validar_conciliacao",
                "processar_especializado",
                "gerar_resultado"
            ],
            "criterios_config": self.criterios_config,
            "version": "v1.0"
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Atualiza configurações de critérios.
        
        Args:
            new_config: Novas configurações para merge
        """
        self.criterios_config.update(new_config)
        
        # Recriar workflow com nova configuração se necessário
        # (Para versões futuras que dependam de config na inicialização)
        pass


# Manter compatibilidade com imports antigos
# Caso algum código importe as funções originais diretamente
def extrair_palavras_chave(descricao: str, criterios_config: Dict = None) -> list:
    """Função de compatibilidade - uso do workflow é recomendado."""
    import warnings
    warnings.warn(
        "Função extrair_palavras_chave está deprecated. Use o workflow LangGraph.", 
        DeprecationWarning,
        stacklevel=2
    )
    
    if criterios_config is None:
        criterios_config = {"palavras_irrelevantes": set()}
    
    # Implementação simplificada para compatibilidade
    import re
    descricao_clean = re.sub(r"[^\w\s]", " ", descricao.upper())
    palavras = descricao_clean.split()
    
    palavras_irrelevantes = criterios_config.get("palavras_irrelevantes", set())
    palavras_filtradas = [
        palavra for palavra in palavras 
        if len(palavra) > 2 and palavra.lower() not in palavras_irrelevantes
    ]
    
    numeros = re.findall(r"\d{3,}", descricao)
    palavras_filtradas.extend(numeros)
    
    return list(set(palavras_filtradas))


# Exportações principais
__all__ = ["ConciliadorBancarioAgent", "extrair_palavras_chave"]