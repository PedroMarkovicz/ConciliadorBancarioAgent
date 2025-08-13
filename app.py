import streamlit as st
import json
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Adicionar diretório raiz ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.conciliador_bancario import ConciliadorBancarioAgent

def validar_json_transacao(data: Dict) -> tuple[bool, str]:
    """Valida se o JSON contém os campos obrigatórios de uma transação bancária."""
    campos_obrigatorios = ["data_transacao", "valor_transacao", "descricao_transacao", "tipo_transacao"]
    
    for campo in campos_obrigatorios:
        if campo not in data:
            return False, f"Campo obrigatório '{campo}' não encontrado"
    
    # Validação de tipos
    try:
        float(data["valor_transacao"])
        datetime.strptime(data["data_transacao"], "%Y-%m-%d")
    except (ValueError, TypeError):
        return False, "Formato inválido para 'valor_transacao' ou 'data_transacao'"
    
    return True, "Válido"

def processar_json(json_data: Dict) -> Dict[str, Any]:
    """Processa o JSON e executa a conciliação bancária."""
    agente = ConciliadorBancarioAgent()
    
    # Criar estado global baseado no JSON de entrada
    estado_global = {
        "transacao_bancaria": json_data.get("transacao_bancaria", {}),
        "classificacao_disponivel": json_data.get("classificacao_disponivel"),
        "classificacoes_disponiveis": json_data.get("classificacoes_disponiveis", [])
    }
    
    resultado = agente.conciliar(estado_global)
    return resultado

def exibir_resultado(resultado: Dict[str, Any]):
    """Exibe o resultado da conciliação de forma organizada."""
    conciliacao = resultado.get("conciliacao", {})
    
    # Status principal
    status = conciliacao.get("status", "Desconhecido")
    conciliado = conciliacao.get("conciliado", False)
    
    if conciliado:
        st.success(f"✅ **Status: {status}**")
    else:
        st.error(f"❌ **Status: {status}**")
    
    # Métricas principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        score = conciliacao.get("score_confianca", 0)
        st.metric("Score de Confiança", f"{score:.2f}", f"{score * 100:.0f}%")
    
    with col2:
        needs_review = resultado.get("needs_human_review", False)
        review_text = "Sim" if needs_review else "Não"
        st.metric("Revisão Manual", review_text)
    
    with col3:
        if conciliacao.get("id_lancamento_contabil"):
            st.metric("ID Lançamento", conciliacao["id_lancamento_contabil"])
    
    # Detalhes da conciliação
    st.subheader("📋 Detalhes da Conciliação")
    
    if conciliacao.get("documento_origem"):
        st.write(f"**Documento Origem:** {conciliacao['documento_origem']}")
    
    if conciliacao.get("cfop_origem"):
        st.write(f"**CFOP:** {conciliacao['cfop_origem']}")
    
    # Divergências
    divergencias = conciliacao.get("divergencias", [])
    if divergencias:
        st.subheader("⚠️ Divergências Identificadas")
        for div in divergencias:
            impacto_color = {"baixo": "info", "medio": "warning", "alto": "error"}
            cor = impacto_color.get(div.get("impacto", "info"), "info")
            getattr(st, cor)(f"**{div.get('tipo', 'N/A')}:** {div.get('descricao', 'N/A')}")
    
    # Observações
    observacoes = conciliacao.get("observacoes", [])
    if observacoes:
        st.subheader("📝 Observações")
        for obs in observacoes:
            st.write(f"• {obs}")
    
    # Metadados do matching
    metadados = conciliacao.get("metadados_matching", {})
    if metadados:
        st.subheader("🔍 Metadados do Matching")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Critério Principal:** {metadados.get('criterio_principal', 'N/A')}")
            st.write(f"**Diferença de Valor:** R$ {metadados.get('diferenca_valor', 0):.2f}")
        
        with col2:
            st.write(f"**Diferença de Dias:** {metadados.get('diferenca_dias', 0)}")
            palavras = metadados.get("palavras_encontradas", [])
            if palavras:
                st.write(f"**Palavras Encontradas:** {', '.join(palavras)}")
    
    # Informações específicas por tipo de conciliação
    if conciliacao.get("calculo_retencoes"):
        st.subheader("💰 Cálculo de Retenções")
        ret = conciliacao["calculo_retencoes"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Valor Bruto", f"R$ {ret.get('valor_bruto', 0):.2f}")
        with col2:
            st.metric("Total Retenções", f"R$ {ret.get('total_retencoes', 0):.2f}")
        with col3:
            st.metric("Valor Líquido", f"R$ {ret.get('valor_liquido_esperado', 0):.2f}")
    
    if conciliacao.get("documentos_conciliados"):
        st.subheader("📄 Documentos Conciliados (Lote)")
        docs = conciliacao["documentos_conciliados"]
        
        for doc in docs:
            st.write(f"• **{doc.get('documento', 'N/A')}** - R$ {doc.get('valor', 0):.2f} (ID: {doc.get('id_lancamento', 'N/A')})")
    
    # JSON completo (expandível)
    with st.expander("🔧 JSON Completo do Resultado"):
        st.json(resultado)

def main():
    st.set_page_config(
        page_title="Conciliação Bancária Inteligente",
        page_icon="🏦",
        layout="wide"
    )
    
    st.title("🏦 Conciliação Bancária Inteligente")
    st.markdown("**Sistema de Conciliação Automatizada com IA**")
    
    st.markdown("""
    Este aplicativo utiliza o agente `ConciliadorBancarioAgent` para processar transações bancárias 
    e realizar conciliações inteligentes com documentos fiscais.
    """)
    
    # Seção de entrada de dados
    st.header("📥 Entrada de Dados")
    
    input_method = st.radio(
        "Escolha o método de entrada:",
        ["Upload de arquivo JSON", "Inserção manual de JSON"],
        horizontal=True
    )
    
    json_data = None
    
    if input_method == "Upload de arquivo JSON":
        uploaded_file = st.file_uploader(
            "Selecione um arquivo JSON",
            type=["json"],
            help="Faça upload de um arquivo JSON contendo os dados da transação bancária"
        )
        
        if uploaded_file is not None:
            try:
                json_data = json.load(uploaded_file)
                st.success("✅ Arquivo carregado com sucesso!")
            except json.JSONDecodeError as e:
                st.error(f"❌ Erro ao decodificar JSON: {e}")
    
    else:  # Inserção manual
        st.markdown("**Cole o JSON da transação no campo abaixo:**")
        
        # Exemplo de JSON para ajudar o usuário
        with st.expander("📋 Ver exemplo de JSON"):
            exemplo_json = {
                "transacao_bancaria": {
                    "data_transacao": "2025-07-29",
                    "valor_transacao": 15.00,
                    "descricao_transacao": "PIX VENDA MERC PRODUTO A PRODUTO B",
                    "tipo_transacao": "Crédito",
                    "conta_bancaria": "341-12345-6"
                },
                "classificacao_disponivel": {
                    "cfop": "5102",
                    "natureza_operacao": "interna",
                    "conta_debito": "1.1.3.01.0001",
                    "conta_credito": "3.1.1.02.0001",
                    "valor_total": 15.00,
                    "data_documento": "2025-07-29",
                    "numero_documento": "NF-e 001",
                    "parceiro_nome": "Cliente ABC"
                }
            }
            st.code(json.dumps(exemplo_json, indent=2, ensure_ascii=False), language="json")
        
        json_input = st.text_area(
            "JSON da Transação",
            height=300,
            placeholder="Cole aqui o JSON com os dados da transação bancária..."
        )
        
        if json_input.strip():
            try:
                json_data = json.loads(json_input)
                st.success("✅ JSON validado com sucesso!")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON inválido: {e}")
    
    # Processamento
    if json_data is not None:
        # Validação dos dados
        if "transacao_bancaria" in json_data:
            is_valid, message = validar_json_transacao(json_data["transacao_bancaria"])
            
            if is_valid:
                st.info("✅ Dados da transação validados")
                
                # Botão para processar
                if st.button("🚀 Processar Conciliação", type="primary"):
                    with st.spinner("Processando conciliação..."):
                        try:
                            resultado = processar_json(json_data)
                            
                            st.header("📊 Resultado da Conciliação")
                            exibir_resultado(resultado)
                            
                        except Exception as e:
                            st.error(f"❌ Erro durante o processamento: {e}")
                            st.exception(e)
            else:
                st.error(f"❌ Erro na validação: {message}")
        else:
            st.warning("⚠️ O JSON deve conter pelo menos o campo 'transacao_bancaria'")
    
    # Sidebar com informações
    with st.sidebar:
        st.header("ℹ️ Informações")
        
        st.subheader("Status Possíveis")
        st.write("• **Conciliado_Automatico**: Conciliação perfeita")
        st.write("• **Conciliado_Com_Ressalva**: Com pequenas divergências")
        st.write("• **Conciliado_Com_Retencoes**: Com impostos retidos")
        st.write("• **Conciliado_Parcial**: Pagamento parcelado")
        st.write("• **Conciliado_Lote**: Múltiplos documentos")
        st.write("• **Nao_Conciliado**: Não foi possível conciliar")
        st.write("• **Nao_Conciliavel**: Taxa bancária ou similar")
        
        st.subheader("📋 Campos Obrigatórios")
        st.write("• data_transacao (YYYY-MM-DD)")
        st.write("• valor_transacao (número)")
        st.write("• descricao_transacao (texto)")
        st.write("• tipo_transacao (Débito/Crédito)")
        
        st.subheader("🔧 Versão")
        st.write("Agente: v1.0")
        st.write("Interface: Streamlit")

if __name__ == "__main__":
    main()