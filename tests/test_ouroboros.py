from motor.ouroboros import achar_ciclos, visivel_para


def _rodar(pix, **kw):
    o, d, t, v = zip(*pix)
    return achar_ciclos(o, d, t, v, **kw)


def test_acha_ciclo_de_4_saltos_com_valor_encolhendo():
    pix = [(1, 2, 0, 1000), (2, 3, 5, 950), (3, 4, 9, 900), (4, 1, 20, 870)]
    assert _rodar(pix) == [[0, 1, 2, 3]]


def test_ignora_ciclo_fora_de_ordem_no_tempo():
    pix = [(1, 2, 0, 1000), (2, 3, 5, 950), (3, 4, 4, 900), (4, 1, 20, 870)]
    assert _rodar(pix) == []


def test_ignora_ciclo_que_estoura_a_janela():
    pix = [(1, 2, 0, 1000), (2, 3, 50, 950), (3, 4, 100, 900), (4, 1, 130, 870)]
    assert _rodar(pix, janela_h=120) == []


def test_ignora_valor_que_cresce_ou_despenca():
    cresce = [(1, 2, 0, 1000), (2, 3, 5, 1500), (3, 1, 9, 1400)]
    despenca = [(1, 2, 0, 1000), (2, 3, 5, 300), (3, 1, 9, 290)]
    assert _rodar(cresce) == [] and _rodar(despenca) == []


def test_ida_e_volta_de_2_saltos_nao_conta():
    assert _rodar([(1, 2, 0, 1000), (2, 1, 3, 990)]) == []


def test_ciclo_contado_uma_vez_so():
    pix = [(1, 2, 0, 1000), (2, 3, 5, 950), (3, 1, 9, 900)]
    assert len(_rodar(pix)) == 1


def test_ciclo_entre_bancos_so_fecha_no_consorcio():
    o, d = [1, 2, 3], [2, 3, 1]
    inst = {1: "A", 2: "B", 3: "C"}
    soz, cons = visivel_para([0, 1, 2], o, d, inst, membros={"A", "B", "C"})
    assert soz == [] and cons
    # sem C no consórcio, o Pix B -> C ainda toca B; o ciclo fecha
    assert visivel_para([0, 1, 2], o, d, inst, membros={"A", "B"})[1]
    # só A no consórcio: B -> C não toca membro
    assert not visivel_para([0, 1, 2], o, d, inst, membros={"A"})[1]
