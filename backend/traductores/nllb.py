from .base import TraductorBase

class TraductorNLLB(TraductorBase):
    def __init__(self):
        self._modelo = None

    @property
    def nombre(self):
        return 'NLLB-200'

    def _cargar_modelo(self):
        if self._modelo is None:
            import ctranslate2
            self._modelo = ctranslate2.TranslationModel(
                'facebook/nllb-200-distilled-600M',
                compute_type='int8'
            )

    def traducir_lote(self, segmentos, contexto_previo=''):
        if not segmentos:
            return [], ''

        self._cargar_modelo()

        textos = [s['texto'] for s in segmentos]

        if contexto_previo:
            textos_con_ctx = [contexto_previo + ' ||| ' + t for t in textos]
        else:
            textos_con_ctx = textos

        traducciones = self._modelo.translate_batch(
            textos_con_ctx,
            src_lang='eng_Latn',
            tgt_lang='spa_Latn',
            beam_size=5
        )

        resultado = []
        for i, seg in enumerate(segmentos):
            texto_traducido = traducciones[i][0] if i < len(traducciones) else seg['texto']
            resultado.append({
                'inicio': seg['inicio'],
                'fin': seg['fin'],
                'texto': texto_traducido
            })

        contexto_salida = resultado[-1]['texto'] if resultado else ''
        return resultado, contexto_salida
