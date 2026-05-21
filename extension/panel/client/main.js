// BeatSync CEP panel — client side.
//
// Responsibilities:
//   1. Collect inputs from the user.
//   2. Either get an audio path from the currently selected AE layer (via host.jsx)
//      or let them browse.
//   3. Spawn the Python analyzer with window.cep.process and wait for exit.
//   4. Ask host.jsx to read the resulting beats.json and place markers.
//
// Requires --enable-nodejs and --mixed-context in the manifest (already set).

(function () {
    var cs = new CSInterface();
    var log = document.getElementById("log");

    function logLine(msg, cls) {
        var span = document.createElement("span");
        if (cls) span.className = cls;
        span.textContent = msg + "\n";
        log.appendChild(span);
        log.scrollTop = log.scrollHeight;
    }

    function setBusy(busy) {
        document.getElementById("btnAnalyze").disabled = busy;
    }

    // --- audio file picking ---

    document.getElementById("btnPickAudio").addEventListener("click", function () {
        var result = window.cep.fs.showOpenDialogEx(false, false, "Pick audio file", "", ["wav", "mp3", "flac", "aac", "m4a", "ogg"]);
        if (result && result.data && result.data.length) {
            document.getElementById("audioPath").value = result.data[0];
        }
    });

    document.getElementById("btnUseSelected").addEventListener("click", function () {
        cs.evalScript("BeatSync.getSelectedAudioPath()", function (res) {
            if (!res || res === "EvalScript error." || res === "undefined" || res === "null") {
                logLine("Select an audio layer in AE first.", "err");
                return;
            }
            document.getElementById("audioPath").value = res;
        });
    });

    // --- main action ---

    document.getElementById("btnAnalyze").addEventListener("click", function () {
        var audio = document.getElementById("audioPath").value.trim();
        if (!audio) { logLine("Pick an audio file first.", "err"); return; }

        var method = document.getElementById("method").value;
        var opts = {
            beats:     document.getElementById("cbBeats").checked,
            downbeats: document.getElementById("cbDownbeats").checked,
            onsets:    document.getElementById("cbOnsets").checked,
            offset:    parseFloat(document.getElementById("offset").value) || 0
        };
        if (!opts.beats && !opts.downbeats && !opts.onsets) {
            logLine("Nothing selected to place.", "err"); return;
        }

        setBusy(true);
        log.innerHTML = "";
        logLine("Analyzing with " + method + "…");

        var extRoot = cs.getSystemPath(SystemPath.EXTENSION);
        // Repo layout: extension/panel/ is the CEP root, so the analyzer lives two
        // levels up. When ZXP-packaged for end users we'll bundle a frozen analyzer
        // inside the extension; for now this works in dev with PlayerDebugMode on.
        var pythonScript = extRoot + "/../../analyzer";
        var outJson = extRoot + "/tmp_beats.json";

        runPython(pythonScript, audio, method, outJson, function (err) {
            if (err) {
                logLine("Analyzer failed: " + err, "err");
                setBusy(false);
                return;
            }
            logLine("Got beats.json, placing markers…", "ok");
            var call = "BeatSync.placeMarkersFromJson("
                + JSON.stringify(outJson) + ", "
                + JSON.stringify(opts) + ")";
            cs.evalScript(call, function (res) {
                if (res && res.indexOf("ERR:") === 0) {
                    logLine(res, "err");
                } else {
                    logLine(res || "Done.", "ok");
                }
                setBusy(false);
            });
        });
    });

    // --- spawn python ---

    function runPython(analyzerDir, audioPath, method, outJson, done) {
        // We rely on `python3` being on PATH. For a real release, ship a frozen
        // binary (pyinstaller) inside the extension and point at that instead.
        var args = [
            "-m", "beatsync.cli", "infer",
            "--audio", audioPath,
            "--out", outJson,
            "--method", method,
            "--quiet"
        ];

        // window.cep.process is CEP's child_process. Argument signature is
        // (executable, arg1, arg2, ...). We push args one by one.
        var processCall = ["python3"].concat(args);

        var spawn;
        try {
            spawn = window.cep.process.createProcess.apply(window.cep.process, processCall);
        } catch (e) {
            done(String(e));
            return;
        }
        if (!spawn || spawn.err !== 0) {
            done("Failed to spawn python3. Is it installed and on PATH?");
            return;
        }
        var pid = spawn.data;

        // CEP doesn't deliver stdout in a stream we can `await`; we just poll exit.
        // To pass PYTHONPATH so the package is found, we use an env wrapper:
        // (createProcess doesn't expose env directly; we re-spawn via /bin/sh -c on
        //  unix or cmd.exe on windows.)
        // Cleaner: call the launcher shell script instead.
        // The naive spawn above will only work if `beatsync` is pip-installed.
        // For dev, run `pip install -e analyzer/` once and you're set.

        var poll = setInterval(function () {
            var running = window.cep.process.isRunning(pid);
            if (running && running.data === true) return;
            clearInterval(poll);
            var exit = window.cep.process.getExitCode(pid);
            if (exit && exit.data === 0) {
                done(null);
            } else {
                done("python3 exited with code " + (exit ? exit.data : "?"));
            }
        }, 300);
    }
})();
