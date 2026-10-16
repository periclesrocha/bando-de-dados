#!/usr/bin/env python3
"""Troca a senha do site sem precisar do dataset original.

Uso (na pasta do site):
    python tools/trocar_senha.py

Pede a senha atual e a nova, e regrava data/jogos.json e data/adv/*.json
cifrados com a nova senha. Depois, publique a pasta data/ de novo.
Quem tinha a senha antiga deixa de conseguir abrir os dados.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cripto  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    arquivos = [os.path.join(ROOT, "data", "jogos.json")] + sorted(glob.glob(os.path.join(ROOT, "data", "adv", "*.json")))
    envs = []
    for a in arquivos:
        with open(a, encoding="utf-8") as f:
            envs.append(json.load(f))
    if not all(isinstance(e, dict) and e.get("enc") == "AES-256-GCM" for e in envs):
        sys.exit("Os arquivos em data/ não estão cifrados. Gere-os com tools/build_data.py.")

    atual = cripto.pedir_senha("Senha atual", confirmar=False, usar_env=False)
    chaves = {}
    conteudos = []
    try:
        for e in envs:
            k = (e["salt"], e["iter"])
            if k not in chaves:
                chaves[k] = cripto.derivar_chave(atual, cripto.unb64(e["salt"]), e["iter"])
            conteudos.append(cripto.decifrar(e, chaves[k]))
    except Exception:
        sys.exit("Senha atual incorreta. Nada foi alterado.")

    nova = cripto.pedir_senha("Nova senha", confirmar=True, usar_env=False)
    sal = cripto.novo_sal()
    chave = cripto.derivar_chave(nova, sal)
    for a, obj in zip(arquivos, conteudos):
        cripto.gravar(a, obj, chave, sal)
    print(f"Senha trocada em {len(arquivos)} arquivos. Publique a pasta data/ novamente.")


if __name__ == "__main__":
    main()
