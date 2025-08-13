# agents/workflow/graph.py
from langgraph.graph import StateGraph, END
from .state import ConciliacaoState
from .nodes import (
    identificar_tipo_node,
    calcular_matching_node,
    validar_conciliacao_node,
    processar_especializado_node,
    gerar_resultado_node
)


def create_conciliacao_graph():
    """
    Cria e configura o workflow LangGraph para conciliação bancária.
    
    Fluxo:
    START → identificar_tipo → calcular_matching → validar_conciliacao 
          → processar_especializado → gerar_resultado → END
          
    Com roteamento condicional baseado no tipo de transação identificado.
    """
    
    # Criar o grafo com o estado tipado
    workflow = StateGraph(ConciliacaoState)
    
    # Adicionar todos os nós funcionais
    workflow.add_node("identificar_tipo", identificar_tipo_node)
    workflow.add_node("calcular_matching", calcular_matching_node)
    workflow.add_node("validar_conciliacao", validar_conciliacao_node)
    workflow.add_node("processar_especializado", processar_especializado_node)
    workflow.add_node("gerar_resultado", gerar_resultado_node)
    
    # Definir ponto de entrada
    workflow.set_entry_point("identificar_tipo")
    
    # Fluxo sequencial principal
    workflow.add_edge("identificar_tipo", "calcular_matching")
    workflow.add_edge("calcular_matching", "validar_conciliacao")
    workflow.add_edge("validar_conciliacao", "processar_especializado")
    workflow.add_edge("processar_especializado", "gerar_resultado")
    
    # Conectar ao fim
    workflow.add_edge("gerar_resultado", END)
    
    # Compilar o grafo
    return workflow.compile()


def route_by_type(state: ConciliacaoState) -> str:
    """
    Função de roteamento condicional baseada no tipo de transação.
    Atualmente não utilizada, mas disponível para extensões futuras.
    """
    tipo = state.get("tipo_transacao", "normal")
    
    # Mapeamento de tipos para próximos nós (para uso futuro)
    routing_map = {
        "taxa_bancaria": "gerar_resultado",  # Pula matching
        "lote": "processar_especializado",   # Pula validação individual  
        "normal": "calcular_matching",       # Fluxo padrão
        "com_retencoes": "calcular_matching", # Fluxo padrão com processamento especial
        "parcela": "calcular_matching"       # Fluxo padrão
    }
    
    return routing_map.get(tipo, "calcular_matching")


def create_advanced_conciliacao_graph():
    """
    Versão avançada com roteamento condicional.
    Disponível para uso futuro quando necessário otimizar o fluxo.
    """
    workflow = StateGraph(ConciliacaoState)
    
    # Adicionar nós
    workflow.add_node("identificar_tipo", identificar_tipo_node)
    workflow.add_node("calcular_matching", calcular_matching_node)
    workflow.add_node("validar_conciliacao", validar_conciliacao_node)
    workflow.add_node("processar_especializado", processar_especializado_node)
    workflow.add_node("gerar_resultado", gerar_resultado_node)
    
    # Ponto de entrada
    workflow.set_entry_point("identificar_tipo")
    
    # Roteamento condicional após identificação
    workflow.add_conditional_edges(
        "identificar_tipo",
        route_by_type,
        {
            "taxa_bancaria": "gerar_resultado",
            "lote": "processar_especializado", 
            "calcular_matching": "calcular_matching"
        }
    )
    
    # Fluxo normal
    workflow.add_edge("calcular_matching", "validar_conciliacao")
    workflow.add_edge("validar_conciliacao", "processar_especializado")
    workflow.add_edge("processar_especializado", "gerar_resultado")
    
    # Fim
    workflow.add_edge("gerar_resultado", END)
    
    return workflow.compile()


# Exportar a função principal
__all__ = ["create_conciliacao_graph", "create_advanced_conciliacao_graph"]