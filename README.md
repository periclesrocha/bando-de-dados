# Bando de Dados

Every Corinthians first-team match since 10 September 1910, as a static website: results by season, head-to-head records against every opponent, player rankings and careers, and the full match report (*ficha técnica*) for each game. The site is in Portuguese.

- 6,348 matches (1910–2026), 1,520 Corinthians players
- Both line-ups, scorers, cards, referee, attendance, ticket revenue and coaches, where the source records them
- Filters for period, competition and home/away apply to every page
- No build step, no framework, no server: one `index.html` plus JSON files in `data/`
- **The data is encrypted.** Visitors see a password screen; without the password the files in `data/` are unreadable, both on the site and in the repository

## Privacy: what the password protects

Every file in `data/` is gzip-compressed and encrypted with AES-256-GCM. The key is derived from the site password with PBKDF2-SHA256 (600,000 iterations). The browser decrypts the data locally after the password is entered. The password is not stored anywhere in the repository or the site.

- **Protected:** anyone without the password, including people who browse or clone the public repository, sees only encrypted text.
- **Not protected:** anyone you give the password to can read everything the site shows and copy it. No website can prevent that. Share the password only with people you trust.
- **Revoking access:** change the password (below) and publish `data/` again. The old password stops working.
- **Remember option:** "Lembrar neste navegador" keeps the decryption key in that browser's storage. "Bloquear este navegador" in the footer removes it.
- Search engines are asked not to index the site (`noindex`).

If you need per-person logins that you can revoke individually, host the same folder on a service with real authentication in front of it, such as Azure Static Web Apps (built-in login and invitations) or Cloudflare Pages with Cloudflare Access.

### Change the password

```bash
python -m pip install cryptography
python tools/trocar_senha.py
```

It asks for the current password and the new one, then rewrites the files in `data/`. Commit and push `data/` afterwards.

## Deploy to GitHub Pages

**Without the command line**

1. On GitHub, create a new **public** repository, for example `bando-de-dados`. Leave it empty (no README).
2. On the empty repo page, click **uploading an existing file**. Drag in everything in this folder: `index.html`, `README.md`, `.nojekyll`, `.gitignore`, and the `data` and `tools` folders. Click **Commit changes**. Never upload the dataset ZIP or CSV files.
3. Go to **Settings → Pages**. Under *Build and deployment*, set **Source: Deploy from a branch**, **Branch: `main`**, folder **`/ (root)`**, then click **Save**.
4. After about a minute the site is live at `https://<your-username>.github.io/bando-de-dados/`. The Pages settings screen shows the link.

**With git**

```bash
cd bando-de-dados
git init -b main
git add .
git commit -m "Bando de Dados"
git remote add origin https://github.com/<your-username>/bando-de-dados.git
git push -u origin main
```

Then do step 3 above.

GitHub Pages on a private repository needs a paid GitHub plan. On a free account, the repository must be public.

## Preview locally

The page loads its data with `fetch`, so opening `index.html` straight from disk won't work. Serve the folder instead:

```bash
python -m http.server 8000 --bind 127.0.0.1
# open http://localhost:8000
```

Decryption uses the browser's Web Crypto API, which only runs on `https://` sites or on `localhost`, so test through `localhost` as above.

## Updating the data

The files in `data/` are generated, already encrypted, from the dataset ZIP (`jogos.csv`, `escalacoes.csv`, `gols.csv`, `cartoes.csv`, `conferencia.csv`):

```bash
python -m pip install cryptography
python tools/build_data.py path/to/dataset_corinthians_1910-2026.zip
```

It asks for the site password (or reads it from the `BANDO_SENHA` environment variable) and never writes unencrypted files. Then commit and push `data/`. Keep the dataset ZIP outside the repository; `.gitignore` blocks ZIP and CSV files as a safeguard.

## Next match and schedule (`data/calendario.csv`)

The "Próximo jogo" section between the header and the tabs reads `data/calendario.csv`. The site shows the first match dated today or later, plus head-to-head stats against that opponent: wins/draws/losses, goals for and against, the last 10 meetings, top scorers among this season's squad, and other numbers. The buttons under the title switch to later fixtures.

This file is **not encrypted**. A match schedule is public information. Edit it in any text editor or in Excel, then upload it again to the repository.

| Column | Example | Notes |
|---|---|---|
| `data` | `2026-10-19` | Keep the `AAAA-MM-DD` format. `dd/mm/aaaa` also works. |
| `hora` | `20:00` | Brasília time. Leave blank if not yet set. |
| `competicao`, `rodada` | `Brasileirão 2026`, `31ª rodada` | |
| `mandante`, `visitante` | `Corinthians`, `Vitória` | Write `Corinthians` exactly, so the site knows home from away. |
| `adversario` | `Vitória` | Must match the opponent's name in the data (as in the Confrontos tab), e.g. `Vasco da Gama`, `Atlético-MG`. |
| `estadio`, `cidade` | `Neo Química Arena`, `São Paulo/SP` | |
| `onde_assistir` | `SporTV, Premiere` | |
| `confirmado` | `sim` / `não` | `não` shows an "a confirmar" tag. |
| `observacoes` | | Optional, shown under the title. |

If you save from Excel, choose **CSV UTF-8**. Comma or semicolon separators both work. "Elenco atual" means every player who appeared in the latest season in the data.

## Links into the site

- `#visao`, `#confrontos`, `#jogadores`, `#jogos` open a tab
- `#jogo-<id>` opens one match, e.g. `#jogo-5997` (Santos 2 x 3 Corinthians, 1947).

## Notes on the data

Coverage notes:
- 14 matches between 1910 and 1916 have no known score.
- Yellow cards are recorded systematically only from 2009. Earlier matches list sending-offs only.
- Attendance and revenue appear when they were recorded.
- Goal minutes exist for some matches from 2009 on. Assists are not recorded.
- *Aproveitamento* (points percentage) counts a win as 3 points in every era, so seasons can be compared.

This is an independent fan project with no affiliation with Sport Club Corinthians Paulista.
