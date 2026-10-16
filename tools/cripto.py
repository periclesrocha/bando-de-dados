"""Criptografia dos arquivos de dados do site.

Cada arquivo em data/ é um JSON compactado com gzip e cifrado com AES-256-GCM.
A chave vem da senha do site via PBKDF2-SHA256 (600.000 iterações), o mesmo
esquema que o navegador usa (Web Crypto) para abrir os dados em index.html.
A senha nunca é gravada em nenhum arquivo.

Requer:  python -m pip install cryptography
"""
import base64
import getpass
import gzip
import hashlib
import json
import os
import sys

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover
    sys.exit("Falta a biblioteca 'cryptography'. Instale com:  python -m pip install cryptography")

ITERACOES = 600_000
MIN_SENHA = 12


def b64(b):
    return base64.b64encode(b).decode("ascii")


def unb64(s):
    return base64.b64decode(s)


def pedir_senha(rotulo="Senha do site", confirmar=True, usar_env=True):
    """Lê a senha da variável BANDO_SENHA ou pergunta no terminal (sem exibir)."""
    s = os.environ.get("BANDO_SENHA") if usar_env else None
    if not s:
        s = getpass.getpass(f"{rotulo}: ")
        if confirmar and getpass.getpass("Repita a senha: ") != s:
            sys.exit("As senhas não conferem.")
    if confirmar and len(s) < MIN_SENHA:
        sys.exit(f"Use uma senha com pelo menos {MIN_SENHA} caracteres.")
    return s


def novo_sal():
    return os.urandom(16)


def derivar_chave(senha, sal, iteracoes=ITERACOES):
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, iteracoes, dklen=32)


def cifrar(obj, chave, sal, iteracoes=ITERACOES):
    dados = gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0)
    iv = os.urandom(12)
    ct = AESGCM(chave).encrypt(iv, dados, None)  # texto cifrado + tag de 16 bytes, como no Web Crypto
    return {"enc": "AES-256-GCM", "zip": "gzip", "kdf": "PBKDF2-SHA256", "iter": iteracoes,
            "salt": b64(sal), "iv": b64(iv), "ct": b64(ct)}


def decifrar(env, chave):
    pt = AESGCM(chave).decrypt(unb64(env["iv"]), unb64(env["ct"]), None)
    return json.loads(gzip.decompress(pt).decode("utf-8"))


def gravar(caminho, obj, chave, sal):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(cifrar(obj, chave, sal), f, separators=(",", ":"))
