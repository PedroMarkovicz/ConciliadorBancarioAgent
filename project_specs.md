# Projeto de Automação Contábil Inteligente – Especificações Técnicas

## 📋 Visão Geral do Projeto

### Objetivo Principal
Este projeto implementa uma solução completa de automação contábil inteligente baseada em agentes autônomos orquestrados por LangGraph. O sistema processa documentos fiscais (como NF-e) e executa, de forma escalável e auditável:

- Classificação fiscal automatizada
- Cálculo de retenções tributárias
- Validações contábeis especializadas
- Determinação de competências
- **Conciliações bancárias inteligentes**

### Arquitetura do Sistema

#### Modelagem como Grafo de Estados
O processo de automação contábil é modelado como um grafo direcionado onde cada nó representa um estado específico do processamento. A transição entre estados é determinada por condições lógicas baseadas nos resultados obtidos em cada etapa.

**Nós Principais do Grafo:**
- **START**: Recebe documento fiscal de entrada e extrai informações básicas
- **ClassificadorContabil**: Classificação inicial da operação e enriquecimento de contexto
- **Roteamento Condicional**: Direciona fluxo para agentes especializados
- **Processamento Especializado**: Agentes de retenção, validação setorial, conciliação bancária
- **Consolidação**: Agrega resultados e prepara lançamento contábil final
- **END**: Gera output estruturado para inserção no ERP

#### Estrutura do Código
```
contabilidade_agentes/
├── agents/
│   ├── classificador_contabil.py
│   ├── retencao_tributaria.py
│   ├── especialista_setorial.py
│   ├── aprendizagem_contabil.py
│   ├── validador_contabil.py
│   ├── gestor_competencia.py
│   └── conciliador_bancario.py
├── data_sources/
│   ├── cfop_ncm_mapping.csv
│   ├── parametros_parceiro.csv
│   ├── regime_tributario.csv
│   └── [outras bases de dados]
├── models/
│   ├── documento_fiscal.py
│   ├── lancamento_contabil.py
│   └── estado_processamento.py
├── graph/
│   ├── workflow.py
│   └── state_definitions.py
└── utils/
    ├── data_loader.py
    └── validators.py
```

#### Estado Global Compartilhado
O LangGraph utiliza um estado global compartilhado entre todos os agentes, contendo todas as informações necessárias para o processamento da operação fiscal.

---

## 🏦 ConciliadorBancarioAgent - Especificação Detalhada

### Propósito e Funcionamento
O ConciliadorBancarioAgent opera em fluxo paralelo/assíncrono, processando extratos bancários e identificando transações que correspondem aos lançamentos contábeis gerados. Utiliza técnicas de **fuzzy matching** para associar descrições bancárias com documentos fiscais processados.

### Algoritmo de Conciliação

#### Critérios de Matching
1. **Fuzzy matching** na descrição da transação
2. **Busca por valor** com tolerância configurável
3. **Janela temporal** para correspondência de datas
4. **Validação cruzada** com contas a pagar/receber
5. **Scoring de confiança** da conciliação

#### Parâmetros de Configuração
```python
{
    "criterios_busca": {
        "valor_exato": float,
        "tolerancia_valor": float,    # Em R$ ou %
        "janela_data": int,           # Em dias
        "palavras_chave": list,       # Extraídas da descrição
        "score_minimo": float         # Threshold de confiança
    }
}
```

### Estrutura de Dados

#### Input do Agente
```python
{
    "data_transacao": "2025-07-29",
    "valor_transacao": 5200.00,
    "descricao_transacao": "PGTO NF 1234 FORNECEDOR XYZ LTDA",
    "tipo_transacao": "Débito",
    "conta_bancaria": "001-12345-6",
    "codigo_banco": "341"
}
```

#### Output do Agente
```python
{
    "conciliado": true,
    "id_lancamento_contabil": "LC12345",
    "documento_origem": "NF-e 1234",
    "fornecedor": "XYZ COMERCIO LTDA",
    "score_confianca": 0.88,
    "status": "Baixado",
    "divergencias": [],
    "observacoes": [
        "Conciliação automática baseada em NF-e",
        "Valor e data dentro da tolerância estabelecida"
    ],
    "metadados_matching": {
        "criterio_principal": "numero_documento",
        "palavras_encontradas": ["NF", "1234", "XYZ"],
        "diferenca_valor": 0.00,
        "diferenca_dias": 1
    }
}
```

### Casos de Uso e Exemplos

#### Exemplo 1: Conciliação Automática Bem-Sucedida
**Transação Bancária:**
```
Data: 15/01/2025
Valor: R$ 1.450,00 (Débito)
Descrição: "TED NF-E 000123 EMPRESA ABC LTDA"
```

**Resultado:**
- Match encontrado com NF-e 123
- Score: 0.95
- Status: Conciliado automaticamente

#### Exemplo 2: Conciliação com Divergência de Valor
**Transação Bancária:**
```
Data: 20/01/2025
Valor: R$ 2.980,00 (Débito)
Descrição: "PGTO FORN XYZ REF NF 456"
```

**NF-e Correspondente:**
- Valor: R$ 3.000,00
- Diferença: R$ 20,00

**Resultado:**
- Match encontrado com tolerância
- Score: 0.82
- Status: Conciliado com ressalva
- Divergência: Diferença de valor registrada

#### Exemplo 3: Conciliação Manual Necessária
**Transação Bancária:**
```
Data: 25/01/2025  
Valor: R$ 850,00 (Débito)
Descrição: "DOC PAGAMENTO DIVERSOS"
```

**Resultado:**
- Nenhum match automático
- Score: 0.23 (abaixo do threshold)
- Status: Pendente de análise manual
- Sugestões: Lista de possíveis correspondências

#### Exemplo 4: Conciliação Baseada em Classificação Real (CFOP 5102)
**Contexto de Entrada:**
```json
{
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
    "itens": [
      {"descricao": "Produto A", "ncm": "12345678", "valor": 10.0},
      {"descricao": "Produto B", "ncm": "87654321", "valor": 5.0}
    ]
  }
}
```

**Output Completo do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": true,
  "conciliacao": {
    "conciliado": true,
    "id_lancamento_contabil": "LC_5102_20250729_001",
    "documento_origem": "NF-e CFOP 5102",
    "cfop_origem": "5102",
    "natureza_operacao": "interna",
    "score_confianca": 0.92,
    "status": "Conciliado_Automatico",
    "divergencias": [],
    "validacoes_contabeis": {
      "valor_conferido": true,
      "contas_validadas": true,
      "natureza_operacao_compativel": true
    },
    "observacoes": [
      "Conciliação automática baseada em CFOP 5102 - Venda interna",
      "Valor exato entre transação bancária (R$ 15,00) e classificação fiscal",
      "Produtos identificados: Produto A (NCM: 12345678), Produto B (NCM: 87654321)"
    ],
    "metadados_matching": {
      "criterio_principal": "valor_exato_cfop",
      "palavras_encontradas": ["VENDA", "MERC", "PRODUTO"],
      "diferenca_valor": 0.00,
      "diferenca_dias": 0,
      "ncm_relacionados": ["12345678", "87654321"],
      "conta_debito_aplicada": "1.1.3.01.0001",
      "conta_credito_aplicada": "3.1.1.02.0001"
    }
  },
  "conciliacao_needs_review": false,
  "conciliacao_review_reason": null,
  "human_review_pending": false,
  "confianca": 0.92,
  "needs_human_review": false,
  "review_reason": null,
  "rule_version": "v1.0"
}
```

**Análise do Resultado:**
- **Match perfeito**: Valor da transação bancária (R$ 15,00) corresponde exatamente ao valor total da classificação
- **Score alto (0.92)**: Indicadores fortes de correspondência (valor, produtos, natureza da operação)
- **Validação contábil completa**: Contas débito/crédito validadas conforme CFOP 5102
- **Rastreabilidade**: Mantém referência ao CFOP e NCMs dos itens para auditoria

#### Exemplo 5: Pagamento Parcelado - Primeira Parcela
**Contexto de Entrada:**
```json
{
  "transacao_bancaria": {
    "data_transacao": "2025-08-15",
    "valor_transacao": 2500.00,
    "descricao_transacao": "BOLETO FORNEC ABC LTDA PARC 1/3 NF 987654",
    "tipo_transacao": "Débito",
    "conta_bancaria": "237-67890-1"
  },
  "classificacao_disponivel": {
    "cfop": "1102",
    "natureza_operacao": "compra",
    "valor_total": 7500.00,
    "condicao_pagamento": "30/60/90 dias",
    "parcelas": 3
  }
}
```

**Output do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": true,
  "conciliacao": {
    "conciliado": true,
    "id_lancamento_contabil": "LC_1102_20250815_001",
    "documento_origem": "NF-e 987654",
    "cfop_origem": "1102",
    "tipo_conciliacao": "parcial",
    "score_confianca": 0.89,
    "status": "Conciliado_Parcial",
    "divergencias": [],
    "validacoes_contabeis": {
      "parcela_identificada": true,
      "valor_parcela_correto": true,
      "sequencia_parcela": "1/3"
    },
    "observacoes": [
      "Conciliação parcial - Primeira parcela de pagamento parcelado",
      "Valor da parcela (R$ 2.500,00) representa 33,33% do total da NF (R$ 7.500,00)",
      "Restam 2 parcelas pendentes de conciliação"
    ],
    "metadados_matching": {
      "criterio_principal": "parcela_sequencial",
      "palavras_encontradas": ["BOLETO", "FORNEC", "ABC", "PARC", "1/3"],
      "valor_total_documento": 7500.00,
      "valor_parcela_atual": 2500.00,
      "parcelas_restantes": 2
    }
  },
  "confianca": 0.89,
  "needs_human_review": false,
  "rule_version": "v1.0"
}
```

#### Exemplo 6: Pagamento com Retenção de Impostos
**Contexto de Entrada:**
```json
{
  "transacao_bancaria": {
    "data_transacao": "2025-08-20",
    "valor_transacao": 9030.00,
    "descricao_transacao": "PGTO SERVICO TI COMPANY XYZ LIQ NF 555123",
    "tipo_transacao": "Débito",
    "conta_bancaria": "104-11111-2"
  },
  "classificacao_disponivel": {
    "cfop": "5933",
    "natureza_operacao": "prestacao_servico",
    "valor_total": 10000.00,
    "impostos_retidos": {
      "irrf": 150.00,
      "pis": 65.00,
      "cofins": 300.00,
      "csll": 100.00,
      "iss": 355.00
    }
  }
}
```

**Output do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": true,
  "conciliacao": {
    "conciliado": true,
    "id_lancamento_contabil": "LC_5933_20250820_001",
    "documento_origem": "NF-e 555123",
    "cfop_origem": "5933",
    "tipo_conciliacao": "com_retencoes",
    "score_confianca": 0.95,
    "status": "Conciliado_Com_Retencoes",
    "divergencias": [],
    "validacoes_contabeis": {
      "valor_liquido_correto": true,
      "retencoes_calculadas": true,
      "impostos_validados": true
    },
    "calculo_retencoes": {
      "valor_bruto": 10000.00,
      "total_retencoes": 970.00,
      "valor_liquido_esperado": 9030.00,
      "valor_pago": 9030.00,
      "diferenca": 0.00
    },
    "observacoes": [
      "Pagamento líquido com retenções tributárias aplicadas",
      "Total de impostos retidos: R$ 970,00 (IRRF + PIS + COFINS + CSLL + ISS)",
      "Valor líquido pago conforme legislação tributária"
    ],
    "metadados_matching": {
      "criterio_principal": "valor_liquido_retencoes",
      "palavras_encontradas": ["PGTO", "SERVICO", "TI", "COMPANY", "LIQ"],
      "impostos_identificados": ["IRRF", "PIS", "COFINS", "CSLL", "ISS"]
    }
  },
  "confianca": 0.95,
  "needs_human_review": false,
  "rule_version": "v1.0"
}
```

#### Exemplo 7: Transferência PIX com Divergência de Data
**Contexto de Entrada:**
```json
{
  "transacao_bancaria": {
    "data_transacao": "2025-08-25",
    "valor_transacao": 3200.00,
    "descricao_transacao": "PIX RECEBIDO CLIENTE DEF COMERCIO REF VENDA AGOSTO",
    "tipo_transacao": "Crédito",
    "conta_bancaria": "033-99999-5"
  },
  "classificacao_disponivel": {
    "cfop": "5102",
    "data_documento": "2025-08-20",
    "valor_total": 3200.00,
    "cliente": "DEF COMERCIO LTDA"
  }
}
```

**Output do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": true,
  "conciliacao": {
    "conciliado": true,
    "id_lancamento_contabil": "LC_5102_20250825_002",
    "documento_origem": "Venda DEF COMERCIO",
    "cfop_origem": "5102",
    "tipo_conciliacao": "com_divergencia_data",
    "score_confianca": 0.82,
    "status": "Conciliado_Com_Ressalva",
    "divergencias": [
      {
        "tipo": "data",
        "descricao": "Diferença de 5 dias entre data do documento (20/08) e pagamento (25/08)",
        "impacto": "baixo"
      }
    ],
    "validacoes_contabeis": {
      "valor_conferido": true,
      "cliente_identificado": true,
      "janela_temporal_aceitavel": true
    },
    "observacoes": [
      "PIX recebido com 5 dias de diferença da data do documento",
      "Cliente DEF COMERCIO identificado na transação",
      "Valor exato da venda conciliado"
    ],
    "metadados_matching": {
      "criterio_principal": "cliente_valor",
      "palavras_encontradas": ["PIX", "CLIENTE", "DEF", "COMERCIO", "VENDA"],
      "diferenca_dias": 5,
      "janela_tolerancia": 7
    }
  },
  "confianca": 0.82,
  "needs_human_review": false,
  "rule_version": "v1.0"
}
```

#### Exemplo 8: Taxa Bancária Não Conciliável
**Contexto de Entrada:**
```json
{
  "transacao_bancaria": {
    "data_transacao": "2025-08-30",
    "valor_transacao": 25.90,
    "descricao_transacao": "TARIFA MANUTENCAO CONTA CORRENTE",
    "tipo_transacao": "Débito",
    "conta_bancaria": "341-12345-6"
  }
}
```

**Output do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": false,
  "conciliacao": {
    "conciliado": false,
    "tipo_transacao_identificado": "taxa_bancaria",
    "score_confianca": 0.15,
    "status": "Nao_Conciliavel",
    "divergencias": [],
    "classificacao_sugerida": {
      "tipo": "despesa_bancaria",
      "conta_debito_sugerida": "3.1.2.01.0005",
      "conta_credito_sugerida": "1.1.1.01.0001",
      "natureza": "despesa_operacional"
    },
    "observacoes": [
      "Transação identificada como taxa bancária - não possui documento fiscal correspondente",
      "Sugerido lançamento direto como despesa bancária",
      "Não requer conciliação com documentos fiscais"
    ],
    "metadados_matching": {
      "criterio_principal": "exclusao_taxa_bancaria",
      "palavras_encontradas": ["TARIFA", "MANUTENCAO", "CONTA"],
      "categoria_automatica": "taxa_bancaria"
    }
  },
  "confianca": 0.15,
  "needs_human_review": false,
  "motivo_nao_conciliacao": "Taxa bancária sem documento fiscal correspondente",
  "rule_version": "v1.0"
}
```

#### Exemplo 9: Múltiplas NF-es em Uma Transação (TED)
**Contexto de Entrada:**
```json
{
  "transacao_bancaria": {
    "data_transacao": "2025-09-05",
    "valor_transacao": 8750.00,
    "descricao_transacao": "TED PGTO LOTE FORNECEDOR GHI LTDA NFS 001 002 003",
    "tipo_transacao": "Débito",
    "conta_bancaria": "237-55555-8"
  },
  "classificacoes_disponiveis": [
    {
      "documento": "NF-e 001",
      "cfop": "1102",
      "valor": 2500.00,
      "fornecedor": "GHI LTDA"
    },
    {
      "documento": "NF-e 002", 
      "cfop": "1102",
      "valor": 3250.00,
      "fornecedor": "GHI LTDA"
    },
    {
      "documento": "NF-e 003",
      "cfop": "1102", 
      "valor": 3000.00,
      "fornecedor": "GHI LTDA"
    }
  ]
}
```

**Output do ConciliadorBancarioAgent:**
```json
{
  "conciliacao_ok": true,
  "conciliacao": {
    "conciliado": true,
    "tipo_conciliacao": "multiplos_documentos",
    "score_confianca": 0.94,
    "status": "Conciliado_Lote",
    "documentos_conciliados": [
      {
        "id_lancamento": "LC_1102_20250905_001",
        "documento": "NF-e 001",
        "valor": 2500.00
      },
      {
        "id_lancamento": "LC_1102_20250905_002", 
        "documento": "NF-e 002",
        "valor": 3250.00
      },
      {
        "id_lancamento": "LC_1102_20250905_003",
        "documento": "NF-e 003", 
        "valor": 3000.00
      }
    ],
    "validacoes_contabeis": {
      "soma_valores_correta": true,
      "fornecedor_unico": true,
      "cfop_homogeneo": true
    },
    "totalizacao": {
      "valor_total_documentos": 8750.00,
      "valor_transacao": 8750.00,
      "diferenca": 0.00,
      "quantidade_nfs": 3
    },
    "observacoes": [
      "Pagamento em lote para 3 notas fiscais do mesmo fornecedor",
      "Soma dos valores das NF-es corresponde exatamente ao valor da transação",
      "CFOP homogêneo (1102) para todas as notas"
    ],
    "metadados_matching": {
      "criterio_principal": "lote_fornecedor",
      "palavras_encontradas": ["TED", "LOTE", "FORNECEDOR", "GHI", "NFS"],
      "documentos_identificados": ["001", "002", "003"]
    }
  },
  "confianca": 0.94,
  "needs_human_review": false,
  "rule_version": "v1.0"
}
```

### Implementação Técnica

#### Funções Principais
1. **`extrair_palavras_chave()`** - Extração de tokens relevantes da descrição
2. **`calcular_score_matching()`** - Algoritmo de scoring fuzzy
3. **`buscar_candidatos()`** - Busca por possíveis correspondências
4. **`validar_conciliacao()`** - Validação final e scoring
5. **`gerar_output_estruturado()`** - Formatação do resultado

#### Integração com LangGraph
O agente deve ser implementado como uma função compatível com LangGraph, recebendo o estado global e retornando o estado atualizado com informações de conciliação.

### Métricas e Monitoramento
- **Taxa de conciliação automática**
- **Distribuição de scores de confiança**
- **Tempo médio de processamento**
- **Tipos de divergências mais frequentes**
- **Acurácia das conciliações validadas**