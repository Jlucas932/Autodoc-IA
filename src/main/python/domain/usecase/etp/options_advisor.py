"""
Options Advisor - Detecta ambiguidade de caminho e sugere opções de contratação.
Quando a necessidade não deixa claro se é compra, locação, comodato, etc.,
este módulo sugere as opções relevantes com prós, contras e orientações.
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OptionsAdvisor:
    """
    Analisa a necessidade e sugere opções de caminho de contratação quando ambíguo.
    """
    
    # Palavras-chave que indicam caminho específico
    COMPRA_KEYWORDS = [
        'comprar', 'compra', 'aquisição', 'adquirir', 'propriedade',
        'patrimônio', 'incorporar ao patrimônio', 'posse definitiva'
    ]
    
    LOCACAO_KEYWORDS = [
        'alugar', 'aluguel', 'locação', 'locar', 'arrendar', 'arrendamento',
        'leasing', 'frota', 'temporário', 'período determinado'
    ]
    
    COMODATO_KEYWORDS = [
        'comodato', 'empréstimo', 'cessão gratuita', 'sem custo',
        'fornecedor cede', 'disponibilização gratuita'
    ]
    
    SERVICO_KEYWORDS = [
        'serviço', 'prestação de serviço', 'contratação de empresa',
        'terceirização', 'mão de obra'
    ]
    
    def __init__(self):
        pass
    
    def detect_path_from_necessity(self, necessity: str) -> Optional[str]:
        """
        Detecta se a necessidade já indica um caminho específico.
        
        Args:
            necessity: Texto da necessidade
        
        Returns:
            str: "compra", "locacao", "comodato", "servico" ou None se ambíguo
        """
        if not necessity:
            return None
        
        necessity_lower = necessity.lower()
        
        # Contar matches por categoria
        compra_count = sum(1 for kw in self.COMPRA_KEYWORDS if kw in necessity_lower)
        locacao_count = sum(1 for kw in self.LOCACAO_KEYWORDS if kw in necessity_lower)
        comodato_count = sum(1 for kw in self.COMODATO_KEYWORDS if kw in necessity_lower)
        servico_count = sum(1 for kw in self.SERVICO_KEYWORDS if kw in necessity_lower)
        
        # Se um caminho tem claramente mais matches, retornar
        max_count = max(compra_count, locacao_count, comodato_count, servico_count)
        
        if max_count == 0:
            # Nenhuma palavra-chave encontrada = ambíguo
            return None
        
        # Se há empate ou diferença pequena, considerar ambíguo
        counts = [compra_count, locacao_count, comodato_count, servico_count]
        counts_sorted = sorted(counts, reverse=True)
        
        if counts_sorted[0] > 0 and counts_sorted[0] == counts_sorted[1]:
            # Empate = ambíguo
            return None
        
        # Retornar o caminho com mais matches
        if compra_count == max_count:
            return "compra"
        elif locacao_count == max_count:
            return "locacao"
        elif comodato_count == max_count:
            return "comodato"
        elif servico_count == max_count:
            return "servico"
        
        return None
    
    def is_ambiguous(self, necessity: str, requirements: List[Dict]) -> bool:
        """
        Verifica se a necessidade é ambígua quanto ao caminho de contratação.
        
        Args:
            necessity: Texto da necessidade
            requirements: Lista de requisitos sugeridos
        
        Returns:
            bool: True se ambíguo, False se caminho está claro
        """
        detected_path = self.detect_path_from_necessity(necessity)
        
        if detected_path:
            # Caminho detectado = não ambíguo
            logger.info(f"Caminho detectado na necessidade: {detected_path}")
            return False
        
        # Verificar se requisitos indicam caminho
        requirements_text = " ".join([req.get('text', '') for req in requirements])
        detected_in_reqs = self.detect_path_from_necessity(requirements_text)
        
        if detected_in_reqs:
            logger.info(f"Caminho detectado nos requisitos: {detected_in_reqs}")
            return False
        
        # Ambíguo
        logger.info("Caminho de contratação ambíguo, sugerindo opções")
        return True
    
    def suggest_options(self, necessity: str, requirements: List[Dict]) -> List[Dict]:
        """
        Sugere opções de caminho de contratação com prós, contras e orientações.
        
        Args:
            necessity: Texto da necessidade
            requirements: Lista de requisitos sugeridos
        
        Returns:
            List[Dict]: Lista de opções com estrutura padronizada
        """
        # Detectar tipo de objeto (veículo, equipamento, software, etc.)
        object_type = self._detect_object_type(necessity)
        
        options = []
        
        # Opção 1: Compra
        options.append({
            "id": "opt_compra",
            "label": "Compra (Aquisição)",
            "pros": [
                "Bem incorporado ao patrimônio público",
                "Controle total sobre o bem",
                "Sem custos recorrentes após aquisição",
                "Possibilidade de revenda ou remanejamento"
            ],
            "cons": [
                "Investimento inicial alto",
                "Responsabilidade por manutenção e depreciação",
                "Risco de obsolescência (especialmente tecnologia)",
                "Necessidade de espaço para armazenamento"
            ],
            "quando_faz_sentido": self._get_compra_guidance(object_type),
            "observacoes": "Recomendado quando há previsão de uso prolongado (5+ anos) e recursos disponíveis para investimento inicial."
        })
        
        # Opção 2: Locação
        options.append({
            "id": "opt_locacao",
            "label": "Locação (Aluguel)",
            "pros": [
                "Sem investimento inicial alto",
                "Flexibilidade para ajustar quantidade conforme demanda",
                "Manutenção geralmente incluída no contrato",
                "Facilita atualização tecnológica"
            ],
            "cons": [
                "Custo recorrente mensal/anual",
                "Não incorpora ao patrimônio",
                "Dependência do fornecedor",
                "Custo total pode superar compra no longo prazo"
            ],
            "quando_faz_sentido": self._get_locacao_guidance(object_type),
            "observacoes": "Recomendado quando há incerteza sobre demanda futura, necessidade temporária ou orçamento limitado para investimento."
        })
        
        # Opção 3: Comodato (se aplicável)
        if self._is_comodato_applicable(object_type):
            options.append({
                "id": "opt_comodato",
                "label": "Comodato (Cessão Gratuita)",
                "pros": [
                    "Sem custo de aquisição ou locação",
                    "Fornecedor pode incluir manutenção",
                    "Flexibilidade para devolução"
                ],
                "cons": [
                    "Dependência total do fornecedor",
                    "Geralmente vinculado a consumo de insumos",
                    "Controle limitado sobre o bem",
                    "Disponibilidade pode ser restrita"
                ],
                "quando_faz_sentido": "Quando há fornecedor disposto a ceder equipamento gratuitamente (comum em impressoras, máquinas de café, dispensers) em troca de contrato de fornecimento de insumos.",
                "observacoes": "Avaliar custo total incluindo insumos obrigatórios. Pode ser vantajoso para equipamentos de baixo valor com alto consumo de insumos."
            })
        
        return options
    
    def _detect_object_type(self, necessity: str) -> str:
        """
        Detecta o tipo de objeto na necessidade.
        
        Returns:
            str: "veiculo", "equipamento", "software", "mobiliario", "generico"
        """
        necessity_lower = necessity.lower()
        
        if any(kw in necessity_lower for kw in ['veículo', 'carro', 'caminhão', 'van', 'ônibus', 'moto']):
            return "veiculo"
        elif any(kw in necessity_lower for kw in ['computador', 'notebook', 'servidor', 'impressora', 'scanner']):
            return "equipamento_ti"
        elif any(kw in necessity_lower for kw in ['software', 'sistema', 'licença', 'aplicativo']):
            return "software"
        elif any(kw in necessity_lower for kw in ['mesa', 'cadeira', 'armário', 'estante', 'mobília']):
            return "mobiliario"
        elif any(kw in necessity_lower for kw in ['máquina', 'equipamento', 'ferramenta']):
            return "equipamento"
        
        return "generico"
    
    def _get_compra_guidance(self, object_type: str) -> str:
        """Retorna orientação específica para compra baseada no tipo de objeto."""
        guidance_map = {
            "veiculo": "Uso intensivo (mais de 3 anos), necessidade de personalização ou adaptação, frota própria estabelecida.",
            "equipamento_ti": "Equipamentos de uso contínuo, necessidade de customização, ciclo de vida longo (5+ anos).",
            "software": "Licenças perpétuas quando há certeza de uso prolongado e estabilidade da solução.",
            "mobiliario": "Necessidade permanente, especificações customizadas, durabilidade esperada de 10+ anos.",
            "equipamento": "Uso frequente, necessidade de controle total, especificações técnicas específicas.",
            "generico": "Uso prolongado previsto, necessidade de controle total, recursos disponíveis para investimento."
        }
        return guidance_map.get(object_type, guidance_map["generico"])
    
    def _get_locacao_guidance(self, object_type: str) -> str:
        """Retorna orientação específica para locação baseada no tipo de objeto."""
        guidance_map = {
            "veiculo": "Necessidade temporária, demanda sazonal, manutenção terceirizada desejada, renovação frequente da frota.",
            "equipamento_ti": "Tecnologia que evolui rapidamente, projeto com prazo definido, teste antes de aquisição.",
            "software": "Modelo SaaS/assinatura, atualizações frequentes necessárias, escalabilidade de licenças.",
            "mobiliario": "Evento temporário, escritório provisório, necessidade de curto prazo (menos de 2 anos).",
            "equipamento": "Projeto específico com prazo definido, demanda sazonal, teste de viabilidade.",
            "generico": "Necessidade temporária, incerteza sobre demanda futura, orçamento limitado para investimento."
        }
        return guidance_map.get(object_type, guidance_map["generico"])
    
    def _is_comodato_applicable(self, object_type: str) -> bool:
        """Verifica se comodato é aplicável ao tipo de objeto."""
        # Comodato é comum para equipamentos de baixo valor com insumos
        applicable_types = ["equipamento_ti", "equipamento"]
        return object_type in applicable_types
    
    def format_options_for_response(self, options: List[Dict]) -> Dict:
        """
        Formata opções para resposta da API.
        
        Args:
            options: Lista de opções
        
        Returns:
            Dict: Resposta formatada
        """
        return {
            "options": options,
            "message": "Identifiquei que sua necessidade pode ser atendida por diferentes caminhos. "
                      "Analise as opções abaixo e escolha a mais adequada ao seu contexto:",
            "next_action": "pick_option"
        }
