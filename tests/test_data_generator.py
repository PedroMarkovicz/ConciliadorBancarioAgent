# tests/test_data_generator.py
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict
from decimal import Decimal, ROUND_HALF_UP


class GeradorDadosConciliacao:
    """Gera dados sintéticos mais realistas para teste do ConciliadorBancarioAgent"""

    def __init__(self):
        self.fornecedores = [
            "ABC COMERCIO LTDA",
            "XYZ INDUSTRIA SA",
            "DEF SERVICOS EIRELI",
            "GHI TRANSPORTES LTDA",
        ]
        self.cfops_compra = ["1102", "1202", "2102"]
        self.cfops_venda = ["5102", "6102", "5933"]
        self.bancos_codigos = {
            "341": "Itaú",
            "237": "Bradesco",
            "001": "Banco do Brasil",
            "104": "Caixa Econômica Federal",
            "033": "Santander",
        }

    def _valor_realista(self, minimo=100, maximo=10000) -> Decimal:
        return Decimal(random.uniform(minimo, maximo)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _conta_bancaria_realista(self, codigo_banco: str) -> str:
        return f"{codigo_banco}-{random.randint(10000, 99999)}-{random.randint(0, 9)}"

    def gerar_transacao_bancaria(self, tipo_caso: str = "normal") -> Dict:
        base_date = datetime.now() - timedelta(days=random.randint(0, 30))
        fornecedor = random.choice(self.fornecedores)
        valor_base = self._valor_realista()

        codigo_banco = random.choice(list(self.bancos_codigos.keys()))
        conta_bancaria = self._conta_bancaria_realista(codigo_banco)

        if tipo_caso == "normal":
            return {
                "data_transacao": base_date.strftime("%Y-%m-%d"),
                "valor_transacao": float(valor_base),
                "descricao_transacao": f"PGTO NF {random.randint(1000, 9999)} {fornecedor}",
                "tipo_transacao": "Débito",
                "conta_bancaria": conta_bancaria,
                "codigo_banco": codigo_banco,
            }

        elif tipo_caso == "parcela":
            total_parcelas = 3
            parcela_num = random.randint(1, total_parcelas)
            valor_parcela = (valor_base / total_parcelas).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            return {
                "data_transacao": base_date.strftime("%Y-%m-%d"),
                "valor_transacao": float(valor_parcela),
                "descricao_transacao": f"BOLETO {fornecedor} PARC {parcela_num}/{total_parcelas} NF {random.randint(1000, 9999)}",
                "tipo_transacao": "Débito",
                "conta_bancaria": conta_bancaria,
                "codigo_banco": codigo_banco,
                "numero_parcela": parcela_num,
                "total_parcelas": total_parcelas,
            }

        elif tipo_caso == "retencao":
            valor_bruto = valor_base
            # gerar retenções que fechem diferença
            retencoes = {
                "irrf": (valor_bruto * Decimal("0.015")).quantize(Decimal("0.01")),
                "pis": (valor_bruto * Decimal("0.0065")).quantize(Decimal("0.01")),
                "cofins": (valor_bruto * Decimal("0.03")).quantize(Decimal("0.01")),
                "csll": (valor_bruto * Decimal("0.01")).quantize(Decimal("0.01")),
                "iss": (valor_bruto * Decimal("0.035")).quantize(Decimal("0.01")),
            }
            valor_liquido = (valor_bruto - sum(retencoes.values())).quantize(
                Decimal("0.01")
            )
            return {
                "data_transacao": base_date.strftime("%Y-%m-%d"),
                "valor_transacao": float(valor_liquido),
                "descricao_transacao": f"PGTO SERVICO {fornecedor} LIQ NF {random.randint(100000, 999999)}",
                "tipo_transacao": "Débito",
                "conta_bancaria": conta_bancaria,
                "codigo_banco": codigo_banco,
                "impostos_retidos": {k: float(v) for k, v in retencoes.items()},
            }

        elif tipo_caso == "lote":
            documentos = [f"NF-e {random.randint(1000, 9999)}" for _ in range(3)]
            valor_total = (valor_base * 3).quantize(Decimal("0.01"))
            return {
                "data_transacao": base_date.strftime("%Y-%m-%d"),
                "valor_transacao": float(valor_total),
                "descricao_transacao": f"TED PGTO LOTE {fornecedor} {' '.join(doc[-4:] for doc in documentos)}",
                "tipo_transacao": "Débito",
                "conta_bancaria": conta_bancaria,
                "codigo_banco": codigo_banco,
                "documentos_do_lote": documentos,
            }

        elif tipo_caso == "divergencia":
            valor_divergente = (valor_base + Decimal(random.uniform(-50, 50))).quantize(
                Decimal("0.01")
            )
            return {
                "data_transacao": (base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
                "valor_transacao": float(valor_divergente),
                "descricao_transacao": f"PIX RECEBIDO {fornecedor} REF VENDA",
                "tipo_transacao": "Crédito",
                "conta_bancaria": conta_bancaria,
                "codigo_banco": codigo_banco,
            }

    def gerar_classificacao_fiscal(
        self, transacao: Dict, compativel: bool = True
    ) -> Dict:
        import re

        nf_match = re.search(r"NF[E\-\s]*(\d+)", transacao["descricao_transacao"])
        numero_nf = nf_match.group(1) if nf_match else str(random.randint(1000, 9999))

        fornecedor = next(
            (f for f in self.fornecedores if f in transacao["descricao_transacao"]),
            random.choice(self.fornecedores),
        )

        if compativel:
            valor_total = Decimal(str(transacao["valor_transacao"]))
            data_doc = transacao["data_transacao"]
        else:
            valor_total = (
                Decimal(str(transacao["valor_transacao"]))
                + Decimal(random.uniform(100, 1000))
            ).quantize(Decimal("0.01"))
            data_doc = (
                datetime.strptime(transacao["data_transacao"], "%Y-%m-%d")
                - timedelta(days=random.randint(10, 30))
            ).strftime("%Y-%m-%d")

        if (
            "SERVICO" in transacao["descricao_transacao"]
            and "impostos_retidos" in transacao
        ):
            valor_total = (
                valor_total
                + sum(Decimal(str(v)) for v in transacao["impostos_retidos"].values())
            ).quantize(Decimal("0.01"))

        natureza = "compra" if transacao["tipo_transacao"] == "Débito" else "venda"
        cfop = random.choice(
            self.cfops_compra if natureza == "compra" else self.cfops_venda
        )

        classificacao = {
            "numero_documento": f"NF-e {numero_nf}",
            "cfop": cfop,
            "data_documento": data_doc,
            "valor_total": float(valor_total),
            "parceiro_nome": fornecedor,
            "natureza_operacao": natureza,
            "contas_validadas": True,
            "conta_debito": "1.1.3.01.0001",
            "conta_credito": "3.1.1.02.0001",
        }

        if "impostos_retidos" in transacao:
            classificacao["impostos_retidos"] = transacao["impostos_retidos"]

        if "documentos_do_lote" in transacao:
            classificacao["documentos_do_lote"] = transacao["documentos_do_lote"]

        if "numero_parcela" in transacao:
            classificacao["numero_parcela"] = transacao["numero_parcela"]
            classificacao["total_parcelas"] = transacao["total_parcelas"]

        return classificacao

    def gerar_conjunto_teste(self, tamanho: int = 100) -> List[Dict]:
        casos_teste = []
        distribuicao = {
            "normal": int(tamanho * 0.4),
            "parcela": int(tamanho * 0.15),
            "retencao": int(tamanho * 0.15),
            "lote": int(tamanho * 0.1),
            "divergencia": int(tamanho * 0.2),
        }
        for tipo_caso, quantidade in distribuicao.items():
            for _ in range(quantidade):
                transacao = self.gerar_transacao_bancaria(tipo_caso)
                compativel = random.random() < 0.8
                classificacao = self.gerar_classificacao_fiscal(transacao, compativel)
                casos_teste.append(
                    {
                        "transacao_bancaria": transacao,
                        "classificacao_disponivel": classificacao,
                    }
                )
        return casos_teste

    def gerar_arquivos_dados(self, pasta_destino: str = "exemplos"):
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tipos_transacao = {
            "normal": "transacoes_normais",
            "parcela": "transacoes_parceladas",
            "retencao": "transacoes_retencao",
            "lote": "transacoes_lote",
            "divergencia": "transacoes_divergencias",
        }
        arquivos_criados = []
        for tipo_caso, nome_arquivo in tipos_transacao.items():
            dados = []
            for _ in range(20):
                transacao = self.gerar_transacao_bancaria(tipo_caso)
                compativel = tipo_caso != "divergencia"
                classificacao = self.gerar_classificacao_fiscal(transacao, compativel)
                dados.append(
                    {
                        "transacao_bancaria": transacao,
                        "classificacao_disponivel": classificacao,
                    }
                )
            nome_arquivo_completo = f"{nome_arquivo}_{timestamp}.json"
            caminho_arquivo = os.path.join(pasta_destino, nome_arquivo_completo)
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            arquivos_criados.append(caminho_arquivo)
            print(f"Arquivo criado: {caminho_arquivo}")
        return arquivos_criados


if __name__ == "__main__":
    print("=== Gerador de Dados Sintéticos Realistas para Conciliação Bancária ===")
    gerador = GeradorDadosConciliacao()
    arquivos = gerador.gerar_arquivos_dados()
    print(f"\nConcluído! {len(arquivos)} arquivos criados.")
