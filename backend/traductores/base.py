from abc import ABC, abstractmethod

class TraductorBase(ABC):
    @abstractmethod
    def traducir_lote(self, segmentos, contexto_previo=''):
        """
        Traduce un lote de segmentos manteniendo contexto.

        Args:
            segmentos: lista de {'inicio': float, 'fin': float, 'texto': str}
            contexto_previo: texto del lote anterior para mantener coherencia

        Returns:
            (traducidos, contexto_salida)
            traducidos: lista de {'inicio': float, 'fin': float, 'texto': str}
            contexto_salida: string para pasar como contexto_previo al siguiente lote
        """
        pass

    @property
    @abstractmethod
    def nombre(self):
        pass
