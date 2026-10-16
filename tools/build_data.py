#!/usr/bin/env python3
"""Gera os arquivos de dados do site, cifrados com a senha do site.

Uso:
    python tools/build_data.py caminho/para/dataset_corinthians_1910-2026.zip
    python tools/build_data.py caminho/para/pasta_com_os_csvs

Lê jogos.csv, escalacoes.csv, gols.csv, cartoes.csv e conferencia.csv e escreve:
    data/jogos.json        todos os jogos, com gols, cartões e escalação do Corinthians
    data/adv/<decada>.json escalação e técnico do adversário, carregados sob demanda

Os arquivos saem cifrados (AES-256-GCM). A senha é pedida no terminal, ou lida da
variável de ambiente BANDO_SENHA. Nenhum arquivo em texto aberto é gravado.

Requer Python 3.8+ e:  python -m pip install cryptography
"""
import csv
import io
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cripto  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")

FAMILIAS = [
    ("Paulista", {"Paulista", "Paulista (LAF)", "Paulista Extra", "Supercampeonato Paulista"}),
    ("Brasileirão", {"Brasileirão", "Brasileirão - Série B", "Taça de Prata"}),
    ("Copa do Brasil", {"Copa do Brasil"}),
    ("Libertadores", {"Libertadores"}),
    ("Sul-Americana", {"Sul-Americana", "Copa Sul-Americana"}),
    ("Rio-São Paulo", {"Torneio Rio-São Paulo"}),
    ("Amistosos", {"Amistosos", "Jogo varzeano"}),
]
OUTROS = "Outros torneios"
STATUS = {
    "confere": "ok",
    "autores incompletos na fonte": "inc",
    "sem autores dos gols do adversário": "sem",
    "placar desconhecido": "desc",
    "divergente": "div",
}


def ler_tabelas(src):
    nomes = ["jogos.csv", "escalacoes.csv", "gols.csv", "cartoes.csv", "conferencia.csv"]
    out = {}
    if os.path.isdir(src):
        for n in nomes:
            with open(os.path.join(src, n), encoding="utf-8-sig", newline="") as f:
                out[n] = list(csv.DictReader(f))
    else:
        with zipfile.ZipFile(src) as z:
            for n in nomes:
                txt = z.read(n).decode("utf-8-sig")
                out[n] = list(csv.DictReader(io.StringIO(txt, newline="")))
    return out


def base_competicao(label):
    return re.sub(r"\s*\d{4}(\s*[-/]\s*\d{2,4})?\s*$", "", label or "").strip()


def familia(label):
    b = base_competicao(label)
    for nome, bases in FAMILIAS:
        if b in bases:
            return nome
    return OUTROS


def inteiro(v):
    v = (v or "").strip()
    return int(v) if re.fullmatch(r"-?\d+", v) else None


def main(src):
    t = ler_tabelas(src)
    jogos = t["jogos.csv"]
    status = {r["id_jogo"]: STATUS.get(r["status_gols"], r["status_gols"]) for r in t["conferencia.csv"]}

    # Jogadores do Corinthians (ID do jogador -> índice)
    apelidos = defaultdict(Counter)
    nome_completo = {}
    for r in t["escalacoes.csv"]:
        if r["lado"] == "Corinthians" and r["jogador_id"]:
            apelidos[r["jogador_id"]][r["jogador"]] += 1
            if r["nome_completo"]:
                nome_completo[r["jogador_id"]] = r["nome_completo"]
    ids = sorted(apelidos)
    idx = {pid: i for i, pid in enumerate(ids)}
    jogadores = [[pid, apelidos[pid].most_common(1)[0][0], nome_completo.get(pid, "")] for pid in ids]

    esc_cor = defaultdict(list)
    esc_adv = defaultdict(list)
    for r in sorted(t["escalacoes.csv"], key=lambda r: (int(r["id_jogo"]), r["lado"], int(r["ordem"] or 0))):
        jid = int(r["id_jogo"])
        tit = 1 if r["titular"] == "1" else 0
        if r["lado"] == "Corinthians":
            quem = idx[r["jogador_id"]] if r["jogador_id"] else r["jogador"]
            esc_cor[jid].append([quem, tit, r["entrou_no_lugar_de"], inteiro(r["gols"]) or 0,
                                 inteiro(r["amarelos"]) or 0, inteiro(r["vermelhos"]) or 0])
        else:
            esc_adv[jid].append([r["jogador"], tit, r["entrou_no_lugar_de"]])

    lado = {"Corinthians": "C", "Adversário": "A"}
    gols = defaultdict(list)
    for r in t["gols.csv"]:
        gols[int(r["id_jogo"])].append([
            lado.get(r["lado"], "?"), r["jogador"], inteiro(r["gols"]) or 1, 1 if r["gol_contra"] == "1" else 0,
            r["tipo"], r["minutos"], r["tempo"], idx.get(r["jogador_id"], -1)])
    cartoes = defaultdict(list)
    for r in t["cartoes.csv"]:
        cartoes[int(r["id_jogo"])].append([lado.get(r["lado"], "?"), r["jogador"], r["cartao"], inteiro(r["qtd"]) or 1])

    saida = []
    adv_por_decada = defaultdict(dict)
    for r in sorted(jogos, key=lambda r: (r["data"], int(r["id_jogo"]))):
        jid = int(r["id_jogo"])
        gf, ga = inteiro(r["gols_corinthians"]), inteiro(r["gols_adversario"])
        m = {
            "id": jid,
            "d": r["data"],
            "t": r["hora"],
            "c": r["competicao"],
            "f": familia(r["competicao"]),
            "ph": r["fase_rodada"],
            "am": 1 if r["amistoso"] == "1" else 0,
            "h": 1 if r["corinthians_mandante"] == "1" else 0,
            "o": r["adversario"],
            "gf": gf,
            "ga": ga,
            "s": r["estadio"],
            "ci": r["cidade"],
            "uf": r["uf"],
            "pa": r["pais"],
            "ar": r["arbitro"],
            "as": r["assistentes"],
            "va": r["var"],
            "tc": r["tecnico_corinthians"],
            "pu": inteiro(r["publico"]),
            "pp": inteiro(r["publico_pagante"]),
            "pr": inteiro(r["publico_presente"]),
            "re": r["renda"],
            "n": [inteiro(r["confronto_n"]), inteiro(r["confronto_total"])],
            "st": status.get(r["id_jogo"], ""),
            "gs": gols.get(jid, []),
            "cs": cartoes.get(jid, []),
            "L": esc_cor.get(jid, []),
        }
        if m["st"] not in ("ok", ""):
            m["gx"] = r["gols_texto"]
        if r["penaltis_texto"]:
            m["pe"] = r["penaltis_texto"]
        m = {k: v for k, v in m.items() if v not in ("", None, [])}
        saida.append(m)
        dec = r["data"][:3] + "0"
        if esc_adv.get(jid) or r["tecnico_adversario"]:
            adv_por_decada[dec][jid] = {"ta": r["tecnico_adversario"], "A": esc_adv.get(jid, [])}

    datas = [m["d"] for m in saida]
    doc = {
        "gerado": date.today().isoformat(),
        "periodo": [datas[0], datas[-1]],
        "familias": [n for n, _ in FAMILIAS[:-1]] + [OUTROS, "Amistosos"],
        "jogadores": jogadores,
        "jogos": saida,
    }
    senha = cripto.pedir_senha("Senha do site")
    sal = cripto.novo_sal()
    chave = cripto.derivar_chave(senha, sal)
    cripto.gravar(os.path.join(OUT, "jogos.json"), doc, chave, sal)
    for dec, d in adv_por_decada.items():
        cripto.gravar(os.path.join(OUT, "adv", f"{dec}.json"), {str(k): v for k, v in d.items()}, chave, sal)

    print(f"{len(saida)} jogos | {len(jogadores)} jogadores | {len(adv_por_decada)} arquivos de adversário")
    print("data/jogos.json (cifrado):", round(os.path.getsize(os.path.join(OUT, "jogos.json")) / 1e6, 2), "MB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
