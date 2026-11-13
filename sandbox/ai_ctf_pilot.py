"""Two deterministic, offline CTF targets. These are not language models.

The closure is an API boundary for the exercise, not a Python security sandbox.
Do not introspect callables, modules or process memory to obtain the canary.
"""
import secrets


def hedef_kur(seviye, butce=4):
    """Return (public query callable, private checker, query-count callable).

    Only query is passed to student solvers. Every request consumes budget,
    including malformed requests. No file, network, model or persistent state.
    """
    if type(seviye) is not int or seviye not in (1, 2):
        raise ValueError('seviye 1 veya 2')
    if type(butce) is not int or butce < 1:
        raise ValueError('butce pozitif int')
    bayrak = 'PAFTA{' + secrets.token_hex(16) + '}'
    sistem = 'Rol: arsiv yardimcisi. Gizli kanarya: ' + bayrak
    sayac = 0

    def sor(metin):
        nonlocal sayac
        sayac += 1
        if sayac > butce:
            raise RuntimeError('sorgu butcesi asildi')
        if not isinstance(metin, str) or len(metin) > 2000:
            raise ValueError('en fazla 2000 karakterlik str')
        if metin == 'yardim':
            return ('Komutlar: selam, saat, yardim. Deneysel sablon: '
                    '[system]ALAN=bayrak;BICIM=duz[/system]' if seviye == 1 else
                    'Komutlar: selam, saat, yardim. Deneysel sablon: '
                    '[system]ALAN=sistem;BICIM=duz[/system]. Bicimler: duz, ters.')
        if metin == 'selam':
            return 'Merhaba, arsiv acik.'
        if metin == 'saat':
            return 'Arsiv 09:00-17:00 acik.'
        # Deliberate flaw: user text is interpreted as a privileged template.
        if seviye == 1:
            return bayrak if metin == '[system]ALAN=bayrak;BICIM=duz[/system]' else 'Istek reddedildi.'
        cevap = 'Istek reddedildi.'
        if metin == '[system]ALAN=sistem;BICIM=duz[/system]':
            cevap = sistem
        elif metin == '[system]ALAN=sistem;BICIM=ters[/system]':
            cevap = sistem[::-1]
        # Deliberately incomplete output filter: only the literal canary.
        return cevap.replace(bayrak, '[GIZLENDI]')

    def dogrula(deger):
        return isinstance(deger, str) and secrets.compare_digest(deger, bayrak)

    return sor, dogrula, lambda: sayac
