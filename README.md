# discord-badge-unlocker

Tracks which Discord profile badges are unlocked across my accounts. I got tired of checking each alt manually in the client, so this dumps everything to a table.

## install

pip install -r requirements.txt

## usage

python unlocker.py --token Mzgw... --token Nzky...
python unlocker.py --token-file ~/.config/discord/tokens

Add `--json` if you want to pipe it somewhere else.

<!-- updated: 2026-10-08 -->
