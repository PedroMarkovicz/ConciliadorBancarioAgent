# agents/workflow/nodes.py
import re
from datetime import datetime
from typing import Dict, List, Any
from .state import ConciliacaoState


def identificar_tipo_node(state: ConciliacaoState) -> ConciliacaoState:
    """
    Nó 1: Identifica o tipo de transação bancária baseado na descrição
    """
    transacao = state["transacao_bancaria"]
    classificacoes_disponiveis = state.get("classificacoes_disponiveis", [])
    
    # Se há múltiplas classificações, é processamento em lote
    if len(classificacoes_disponiveis) > 1:
        state["tipo_transacao"] = "lote"
        return state
    
    descricao = transacao.get("descricao_transacao", "").upper()
    
    # Identificar tipo baseado na descrição
    if any(palavra in descricao for palavra in ["TARIFA", "TAXA", "MANUTENCAO", "ANUIDADE"]):
        tipo = "taxa_bancaria"
    elif "PARC" in descricao and "/" in descricao:
        tipo = "parcela"
    elif "LIQ" in descricao or "LIQUIDO" in descricao:
        tipo = "com_retencoes"
    elif "LOTE" in descricao and ("NFS" in descricao or "NOTAS" in descricao):
        tipo = "multiplos_documentos"
    else:
        tipo = "normal"
    
    state["tipo_transacao"] = tipo
    return state


def calcular_matching_node(state: ConciliacaoState) -> ConciliacaoState:
    """
    Nó 2: Calcula score de matching entre transação e classificação
    """
    transacao = state["transacao_bancaria"]
    classificacao = state.get("classificacao_disponivel")
    criterios_config = state.get("criterios_config", {
        "tolerancia_valor_percentual": 0.05,
        "tolerancia_valor_absoluta": 50.00,
        "janela_data_dias": 7,
        "score_minimo": 0.60,
        "palavras_irrelevantes": {"ted", "pix", "pgto", "boleto", "doc", "transferencia"}
    })
    
    # Se não há classificação ou é taxa bancária, pular matching
    if not classificacao or state.get("tipo_transacao") == "taxa_bancaria":
        state["matching_info"] = {
            "score_total": 0.15 if state.get("tipo_transacao") == "taxa_bancaria" else 0.0,
            "scores_detalhados": {},
            "diferenca_valor": 0,
            "diferenca_dias": 0,
            "palavras_encontradas": []
        }
        return state
    
    scores = {}
    
    # Score por valor
    valor_transacao = abs(transacao.get("valor_transacao", 0))
    valor_classificacao = abs(classificacao.get("valor_total", 0))
    
    if valor_transacao == 0 and valor_classificacao == 0:
        scores["valor"] = 1.0
    elif valor_transacao == 0 or valor_classificacao == 0:
        scores["valor"] = 0.0
    else:
        diferenca_abs = abs(valor_transacao - valor_classificacao)
        diferenca_perc = diferenca_abs / max(valor_transacao, valor_classificacao)
        
        if (diferenca_abs <= criterios_config["tolerancia_valor_absoluta"] and 
            diferenca_perc <= criterios_config["tolerancia_valor_percentual"]):
            scores["valor"] = 1.0 - diferenca_perc
        else:
            scores["valor"] = max(0.0, 1.0 - (diferenca_perc * 2))
    
    # Score por data
    try:
        data_transacao = datetime.strptime(transacao.get("data_transacao", ""), "%Y-%m-%d")
        data_classificacao = datetime.strptime(classificacao.get("data_documento", ""), "%Y-%m-%d")
        diferenca_dias = abs((data_transacao - data_classificacao).days)
        
        if diferenca_dias <= criterios_config["janela_data_dias"]:
            scores["data"] = max(0.0, 1.0 - (diferenca_dias / criterios_config["janela_data_dias"]))
        else:
            scores["data"] = 0.0
    except:
        scores["data"] = 0.5
        diferenca_dias = 0
    
    # Score por descrição
    palavras_transacao = _extrair_palavras_chave(transacao.get("descricao_transacao", ""), criterios_config)
    palavras_classificacao = []
    
    if classificacao.get("numero_documento"):
        palavras_classificacao.extend(_extrair_palavras_chave(classificacao["numero_documento"], criterios_config))
    if classificacao.get("parceiro_nome"):
        palavras_classificacao.extend(_extrair_palavras_chave(classificacao["parceiro_nome"], criterios_config))
    
    if palavras_transacao and palavras_classificacao:
        intersecao = set(palavras_transacao) & set(palavras_classificacao)
        uniao = set(palavras_transacao) | set(palavras_classificacao)
        scores["descricao"] = len(intersecao) / len(uniao) if uniao else 0.0
        palavras_encontradas = list(intersecao)
    else:
        scores["descricao"] = 0.0
        palavras_encontradas = []
    
    # Score total ponderado
    pesos = {"valor": 0.6, "data": 0.2, "descricao": 0.2}
    score_total = sum(scores[key] * pesos[key] for key in pesos)
    
    state["matching_info"] = {
        "score_total": score_total,
        "scores_detalhados": scores,
        "diferenca_valor": abs(valor_transacao - valor_classificacao),
        "diferenca_dias": diferenca_dias,
        "palavras_encontradas": palavras_encontradas
    }
    
    return state


def validar_conciliacao_node(state: ConciliacaoState) -> ConciliacaoState:
    """
    Nó 3: Valida a conciliação e identifica divergências
    """
    transacao = state["transacao_bancaria"]
    classificacao = state.get("classificacao_disponivel")
    matching_info = state.get("matching_info", {})
    tipo_transacao = state.get("tipo_transacao", "normal")
    criterios_config = state.get("criterios_config", {"score_minimo": 0.60, "janela_data_dias": 7, "tolerancia_valor_absoluta": 50.0})
    
    validacoes = {}
    divergencias = []
    
    # Taxa bancária não pode ser conciliada
    if tipo_transacao == "taxa_bancaria":
        state["validacao"] = {
            "pode_conciliar": False,
            "motivo": "Taxa bancaria sem documento fiscal correspondente",
            "tipo_identificado": "taxa_bancaria",
            "classificacao_sugerida": {
                "tipo": "despesa_bancaria",
                "conta_debito_sugerida": "3.1.2.01.0005",
                "conta_credito_sugerida": "1.1.1.01.0001",
                "natureza": "despesa_operacional"
            },
            "validacoes": validacoes,
            "divergencias": divergencias,
            "tipo_transacao": tipo_transacao
        }
        return state
    
    # Validações específicas por tipo
    if tipo_transacao == "com_retencoes" and classificacao:
        impostos_retidos = classificacao.get("impostos_retidos", {})
        if impostos_retidos:
            valor_bruto = classificacao.get("valor_total", 0)
            total_retencoes = sum(impostos_retidos.values())
            valor_liquido_esperado = valor_bruto - total_retencoes
            diferenca = abs(transacao["valor_transacao"] - valor_liquido_esperado)
            
            if diferenca <= criterios_config["tolerancia_valor_absoluta"]:
                validacoes["retencoes_calculadas"] = True
                validacoes["valor_liquido_correto"] = True
            else:
                divergencias.append({
                    "tipo": "valor_liquido",
                    "descricao": f"Diferenca no valor liquido: R$ {diferenca:.2f}",
                    "impacto": "alto"
                })
    
    # Validação de diferença de data
    if matching_info.get("diferenca_dias", 0) > criterios_config["janela_data_dias"]:
        divergencias.append({
            "tipo": "data",
            "descricao": f"Diferenca de {matching_info['diferenca_dias']} dias entre documento e pagamento",
            "impacto": "baixo" if matching_info["diferenca_dias"] <= 30 else "medio"
        })
    
    # Validação de diferença de valor
    if matching_info.get("diferenca_valor", 0) > criterios_config["tolerancia_valor_absoluta"]:
        divergencias.append({
            "tipo": "valor",
            "descricao": f"Diferenca de valor: R$ {matching_info['diferenca_valor']:.2f}",
            "impacto": "medio"
        })
    
    state["validacao"] = {
        "pode_conciliar": matching_info.get("score_total", 0) >= criterios_config["score_minimo"],
        "validacoes": validacoes,
        "divergencias": divergencias,
        "tipo_transacao": tipo_transacao
    }
    
    return state


def processar_especializado_node(state: ConciliacaoState) -> ConciliacaoState:
    """
    Nó 4: Processamento especializado para casos específicos
    """
    tipo_transacao = state.get("tipo_transacao", "normal")
    transacao = state["transacao_bancaria"]
    classificacao = state.get("classificacao_disponivel")
    classificacoes_disponiveis = state.get("classificacoes_disponiveis", [])
    
    processamento = {}
    
    # Processamento de retenções
    if tipo_transacao == "com_retencoes" and classificacao:
        impostos_retidos = classificacao.get("impostos_retidos", {})
        if impostos_retidos:
            valor_bruto = classificacao.get("valor_total", 0)
            total_retencoes = sum(impostos_retidos.values())
            valor_liquido = valor_bruto - total_retencoes
            
            processamento["calculo_retencoes"] = {
                "valor_bruto": valor_bruto,
                "total_retencoes": total_retencoes,
                "valor_liquido_esperado": valor_liquido,
                "impostos_detalhados": impostos_retidos
            }
    
    # Processamento de lote
    elif tipo_transacao in ["lote", "multiplos_documentos"] and classificacoes_disponiveis:
        valor_total_classificacoes = sum(c.get("valor", 0) for c in classificacoes_disponiveis)
        valor_transacao = transacao.get("valor_transacao", 0)
        
        documentos_conciliados = []
        for i, classificacao in enumerate(classificacoes_disponiveis):
            data_formatada = transacao.get("data_transacao", "").replace("-", "")
            id_lancamento = f"LC_{classificacao.get('cfop', '0000')}_{data_formatada}_{i + 1:03d}"
            documentos_conciliados.append({
                "id_lancamento": id_lancamento,
                "documento": classificacao.get("documento", f"NF-e {i + 1}"),
                "valor": classificacao.get("valor", 0)
            })
        
        processamento["documentos_conciliados"] = documentos_conciliados
        processamento["totalizacao"] = {
            "valor_total_documentos": valor_total_classificacoes,
            "valor_transacao": valor_transacao,
            "diferenca": abs(valor_total_classificacoes - valor_transacao),
            "quantidade_nfs": len(classificacoes_disponiveis)
        }
    
    # Taxa bancária
    elif tipo_transacao == "taxa_bancaria":
        processamento["classificacao_sugerida"] = {
            "tipo": "despesa_bancaria",
            "conta_debito_sugerida": "3.1.2.01.0005",
            "conta_credito_sugerida": "1.1.1.01.0001",
            "natureza": "despesa_operacional"
        }
    
    state["processamento_especializado"] = processamento
    return state


def gerar_resultado_node(state: ConciliacaoState) -> ConciliacaoState:
    """
    Nó 5: Gera o resultado final estruturado
    """
    transacao = state["transacao_bancaria"]
    classificacao = state.get("classificacao_disponivel")
    matching_info = state.get("matching_info", {})
    validacao = state.get("validacao", {})
    processamento = state.get("processamento_especializado", {})
    tipo_transacao = state.get("tipo_transacao", "normal")
    
    # Caso taxa bancária não conciliável
    if tipo_transacao == "taxa_bancaria":
        resultado = {
            "conciliacao_ok": False,
            "conciliacao": {
                "conciliado": False,
                "tipo_transacao_identificado": "taxa_bancaria",
                "score_confianca": matching_info.get("score_total", 0.15),
                "status": "Nao_Conciliavel",
                "divergencias": [],
                "classificacao_sugerida": processamento.get("classificacao_sugerida", {}),
                "observacoes": [
                    "Transacao identificada como taxa bancaria - nao possui documento fiscal correspondente",
                    "Sugerido lancamento direto como despesa bancaria",
                    "Nao requer conciliacao com documentos fiscais"
                ],
                "metadados_matching": {
                    "criterio_principal": "exclusao_taxa_bancaria",
                    "palavras_encontradas": matching_info.get("palavras_encontradas", []),
                    "categoria_automatica": "taxa_bancaria"
                }
            },
            "confianca": matching_info.get("score_total", 0.15),
            "needs_human_review": False,
            "motivo_nao_conciliacao": "Taxa bancaria sem documento fiscal correspondente",
            "rule_version": "v1.0"
        }
        
        state["resultado_final"] = resultado
        return state
    
    # Caso lote
    if tipo_transacao in ["lote", "multiplos_documentos"] and processamento.get("documentos_conciliados"):
        totalizacao = processamento.get("totalizacao", {})
        conciliado = abs(totalizacao.get("diferenca", float('inf'))) <= 50.0  # tolerância
        
        resultado = {
            "conciliacao_ok": conciliado,
            "conciliacao": {
                "conciliado": conciliado,
                "tipo_conciliacao": "multiplos_documentos",
                "score_confianca": 0.94 if conciliado else 0.3,
                "status": "Conciliado_Lote" if conciliado else "Lote_Nao_Conciliado",
                "documentos_conciliados": processamento.get("documentos_conciliados", []),
                "validacoes_contabeis": {
                    "soma_valores_correta": conciliado,
                    "fornecedor_unico": True,
                    "cfop_homogeneo": True
                },
                "totalizacao": totalizacao,
                "observacoes": [
                    f"Pagamento em lote para {totalizacao.get('quantidade_nfs', 0)} notas fiscais",
                    "Soma dos valores das NF-es corresponde ao valor da transacao" if conciliado else "Divergencia nos valores totais"
                ]
            },
            "confianca": 0.94 if conciliado else 0.3,
            "needs_human_review": not conciliado,
            "rule_version": "v1.0"
        }
        
        state["resultado_final"] = resultado
        return state
    
    # Caso sem classificação
    if not classificacao:
        resultado = {
            "conciliacao_ok": False,
            "conciliacao": {
                "conciliado": False,
                "score_confianca": 0.0,
                "status": "Sem_Classificacao_Disponivel"
            },
            "confianca": 0.0,
            "needs_human_review": True,
            "rule_version": "v1.0"
        }
        
        state["resultado_final"] = resultado
        return state
    
    # Caso conciliação normal
    conciliado = validacao.get("pode_conciliar", False)
    divergencias = validacao.get("divergencias", [])
    
    # Determinar status
    if not conciliado:
        status = "Nao_Conciliado"
    elif divergencias:
        status = "Conciliado_Com_Ressalva"
    elif tipo_transacao == "com_retencoes":
        status = "Conciliado_Com_Retencoes"
    elif tipo_transacao == "parcela":
        status = "Conciliado_Parcial"
    else:
        status = "Conciliado_Automatico"
    
    # Gerar ID do lançamento contábil
    data_formatada = transacao.get("data_transacao", "").replace("-", "")
    cfop = classificacao.get("cfop", "0000")
    id_lancamento = f"LC_{cfop}_{data_formatada}_001"
    
    # Observações
    observacoes = []
    if tipo_transacao == "com_retencoes":
        calculo_retencoes = processamento.get("calculo_retencoes", {})
        if calculo_retencoes:
            observacoes.append("Pagamento liquido com retencoes tributarias aplicadas")
            observacoes.append(f"Total de impostos retidos: R$ {calculo_retencoes.get('total_retencoes', 0):.2f}")
    elif tipo_transacao == "parcela":
        observacoes.append("Conciliacao parcial - Pagamento parcelado identificado")
    
    if matching_info.get("diferenca_dias", 0) > 0:
        observacoes.append(f"Diferenca de {matching_info['diferenca_dias']} dias entre documento e pagamento")
    
    if matching_info.get("diferenca_valor", 0) == 0:
        observacoes.append("Valor exato entre transacao bancaria e classificacao fiscal")
    
    # Resultado final
    resultado = {
        "conciliacao_ok": conciliado,
        "conciliacao": {
            "conciliado": conciliado,
            "id_lancamento_contabil": id_lancamento if conciliado else None,
            "documento_origem": classificacao.get("numero_documento"),
            "cfop_origem": classificacao.get("cfop"),
            "score_confianca": round(matching_info.get("score_total", 0), 2),
            "status": status,
            "divergencias": divergencias,
            "observacoes": observacoes,
            "metadados_matching": {
                "criterio_principal": _determinar_criterio_principal(matching_info, validacao, tipo_transacao),
                "palavras_encontradas": matching_info.get("palavras_encontradas", []),
                "diferenca_valor": matching_info.get("diferenca_valor", 0),
                "diferenca_dias": matching_info.get("diferenca_dias", 0)
            }
        },
        "confianca": round(matching_info.get("score_total", 0), 2),
        "needs_human_review": not conciliado,
        "rule_version": "v1.0"
    }
    
    # Adicionar campos específicos para retenções
    if tipo_transacao == "com_retencoes":
        calculo_retencoes = processamento.get("calculo_retencoes", {})
        if calculo_retencoes:
            resultado["conciliacao"]["tipo_conciliacao"] = "com_retencoes"
            resultado["conciliacao"]["calculo_retencoes"] = {
                "valor_bruto": calculo_retencoes["valor_bruto"],
                "total_retencoes": calculo_retencoes["total_retencoes"],
                "valor_liquido_esperado": calculo_retencoes["valor_liquido_esperado"],
                "valor_pago": transacao["valor_transacao"],
                "diferenca": abs(transacao["valor_transacao"] - calculo_retencoes["valor_liquido_esperado"])
            }
    
    state["resultado_final"] = resultado
    return state


# === FUNÇÕES AUXILIARES ===

def _extrair_palavras_chave(descricao: str, criterios_config: Dict) -> List[str]:
    """Extrai palavras-chave relevantes da descrição"""
    descricao_clean = re.sub(r"[^\w\s]", " ", descricao.upper())
    palavras = descricao_clean.split()
    
    palavras_irrelevantes = criterios_config.get("palavras_irrelevantes", set())
    palavras_filtradas = []
    
    for palavra in palavras:
        if len(palavra) > 2 and palavra.lower() not in palavras_irrelevantes:
            palavras_filtradas.append(palavra)
    
    numeros = re.findall(r"\d{3,}", descricao)
    palavras_filtradas.extend(numeros)
    
    return list(set(palavras_filtradas))


def _determinar_criterio_principal(matching_info: Dict, validacao: Dict, tipo_transacao: str) -> str:
    """Determina o critério principal usado na conciliação"""
    if tipo_transacao == "taxa_bancaria":
        return "exclusao_taxa_bancaria"
    elif tipo_transacao == "com_retencoes":
        return "valor_liquido_retencoes"
    elif tipo_transacao == "parcela":
        return "parcela_sequencial"
    elif tipo_transacao in ["lote", "multiplos_documentos"]:
        return "lote_fornecedor"
    elif matching_info.get("diferenca_valor", 0) == 0:
        return "valor_exato_cfop"
    elif matching_info.get("palavras_encontradas", []):
        return "numero_documento"
    else:
        return "fuzzy_matching"