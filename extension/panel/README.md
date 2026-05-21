# BeatSync CEP Panel — install & dev guide

This is the After Effects panel half of BeatSync. It gives you a dockable panel
inside AE with an "Analyze & place markers" button that shells out to the
Python analyzer.

## Prerequisites

1. The Python analyzer must be importable as `beatsync`. From the repo root:
   ```bash
   cd analyzer
   pip install -e .          # or: pip install -r requirements.txt
   ```
   (For a quick check: `python -m beatsync.cli infer --audio song.wav --out beats.json` should work.)
2. `python3` must be on PATH (the panel spawns it directly).
3. `CSInterface.js` must be copied next to `client/main.js`. Grab the latest from
   [Adobe-CEP/CEP-Resources](https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_11.x/CSInterface.js).

## Dev install (unsigned, for development)

CEP requires unsigned panels to be enabled via "PlayerDebugMode".

**macOS:**
```bash
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
# (also write CSXS.10 / CSXS.12 if AE complains about the CSXS version)
```

**Windows (regedit):**
```
HKEY_CURRENT_USER\Software\Adobe\CSXS.11   →   PlayerDebugMode (string) = "1"
```

Then symlink (or copy) the panel into AE's extensions folder:

**macOS:**
```bash
ln -s "$PWD/extension/panel" \
      "$HOME/Library/Application Support/Adobe/CEP/extensions/com.beatsync.aftereffects"
```

**Windows:**
```
mklink /D "%APPDATA%\Adobe\CEP\extensions\com.beatsync.aftereffects" "<repo>\extension\panel"
```

Restart AE → `Window > Extensions > BeatSync`.

## Distribution (M4)

For end users you ship a signed `.zxp`:

```bash
# Get ZXPSignCmd from Adobe-CEP/CEP-Resources
ZXPSignCmd -selfSignedCert US CA "BeatSync" beatsync beatsync.p12
ZXPSignCmd -sign extension/panel BeatSync.zxp beatsync.p12 beatsync -tsa http://timestamp.digicert.com
```

Users install the `.zxp` with [ZXP Installer](https://aescripts.com/learn/zxp-installer/)
or Anastasiy's Extension Manager. The end-user version of the analyzer should
be a frozen binary (pyinstaller) bundled inside `extension/panel/bin/`, with
`main.js` updated to call that binary instead of `python3`.
