#target aftereffects

(function BeatSync() {
    var DIALOG_TITLE = "BeatSync";

    // ----- config -----------------------------------------------------------
    // Path to the Python that has the beatsync analyzer installed. Edit this if
    // your environment differs. The script also falls back to "python3" on PATH.
    var PYTHON_CANDIDATES = [
        "/opt/anaconda3/envs/beatsync/bin/python",
        "python3"
    ];

    // ----- helpers ----------------------------------------------------------
    function readJSON(path) {
        var f = new File(path);
        if (!f.exists) throw new Error("File does not exist: " + path);
        f.encoding = "UTF-8";
        f.open("r");
        var text = f.read();
        f.close();
        return JSON.parse(text);
    }

    function basename(p) {
        var i1 = p.lastIndexOf("/");
        var i2 = p.lastIndexOf("\\");
        var i = (i1 > i2) ? i1 : i2;
        return (i >= 0) ? p.substring(i + 1) : p;
    }

    function quote(s) { return '"' + s + '"'; }

    // Locate the analyzer folder relative to this script:
    //   <repo>/extension/jsx/BeatSync.jsx  ->  <repo>/analyzer
    function findAnalyzerDir() {
        try {
            var self = new File($.fileName);
            var repo = self.parent.parent.parent;       // jsx -> extension -> repo
            var dir = new Folder(repo.fsName + "/analyzer");
            if (dir.exists) return dir.fsName;
        } catch (e) {}
        return null;
    }

    function resolvePython() {
        for (var i = 0; i < PYTHON_CANDIDATES.length; i++) {
            var c = PYTHON_CANDIDATES[i];
            if (c.indexOf("/") === -1) return c;        // bare "python3" — trust PATH
            if (new File(c).exists) return c;
        }
        return PYTHON_CANDIDATES[PYTHON_CANDIDATES.length - 1];
    }

    function ensureActiveComp() {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) {
            alert("Open a composition first.", DIALOG_TITLE);
            return null;
        }
        return comp;
    }

    function pickTargetLayer(comp) {
        if (comp.selectedLayers.length > 0) return comp.selectedLayers[0];
        for (var i = 1; i <= comp.numLayers; i++) {
            if (comp.layer(i).hasAudio) return comp.layer(i);
        }
        return null;
    }

    function selectedAudioPath(comp) {
        var L = comp.selectedLayers.length ? comp.selectedLayers[0] : null;
        if (L && L.source && L.source.file) return L.source.file.fsName;
        for (var i = 1; i <= comp.numLayers; i++) {
            var x = comp.layer(i);
            if (x.hasAudio && x.source && x.source.file) return x.source.file.fsName;
        }
        return "";
    }

    function runAnalyzer(analyzerDir, python, audioPath, method, outPath) {
        var existing = new File(outPath);
        if (existing.exists) existing.remove();

        var cmd = "cd " + quote(analyzerDir) + " && " +
                  quote(python) + " -m beatsync.cli infer" +
                  " --audio " + quote(audioPath) +
                  " --out " + quote(outPath) +
                  " --method " + method;
        if (method === "tcn") cmd += " --device mps";
        cmd += " --quiet 2>&1";

        var output = system.callSystem(cmd);
        var produced = new File(outPath);
        return { ok: produced.exists, log: String(output), out: outPath };
    }

    function placeMarkers(layer, times, labelPrefix, offset) {
        var markerProp = layer.property("Marker");
        var placed = 0;
        for (var i = 0; i < times.length; i++) {
            var t = times[i] + (offset || 0);
            if (t < 0) continue;
            var m = new MarkerValue(labelPrefix + " " + (i + 1));
            markerProp.setValueAtTime(t, m);
            placed++;
            if (placed % 25 === 0) $.sleep(1);
        }
        return placed;
    }

    // ----- UI ---------------------------------------------------------------
    function showDialog(defaultAudio, hasCheckpoint) {
        var w = new Window("dialog", DIALOG_TITLE);
        w.orientation = "column";
        w.alignChildren = "fill";
        w.spacing = 8;

        var audioPanel = w.add("panel", undefined, "Audio file");
        audioPanel.orientation = "row";
        audioPanel.alignChildren = "center";
        var audioField = audioPanel.add("edittext", undefined, defaultAudio || "");
        audioField.characters = 28;
        var browse = audioPanel.add("button", undefined, "Browse…");
        browse.onClick = function () {
            var f = File.openDialog("Select an audio file");
            if (f) audioField.text = f.fsName;
        };

        var mPanel = w.add("panel", undefined, "Model method");
        mPanel.alignChildren = "fill";
        var method = mPanel.add("dropdownlist", undefined, [
            "TCN",
            "librosa",
            "Beat This!"
        ]);
        method.selection = hasCheckpoint ? 0 : 1;

        var typePanel = w.add("panel", undefined, "Place markers for");
        typePanel.orientation = "row";
        var cbBeats = typePanel.add("checkbox", undefined, "Beats");          cbBeats.value = true;
        var cbDown  = typePanel.add("checkbox", undefined, "Downbeats");      cbDown.value = false;
        var cbOnset = typePanel.add("checkbox", undefined, "Onsets");         cbOnset.value = false;

        var offGrp = w.add("group");
        offGrp.add("statictext", undefined, "Time offset (sec):");
        var offField = offGrp.add("edittext", undefined, "0.0");
        offField.characters = 6;

        var note = w.add("statictext", undefined,
            "Analyzing runs the model and may take a few seconds.", { multiline: true });
        try {
            note.graphics.foregroundColor =
                note.graphics.newPen(note.graphics.PenType.SOLID_COLOR, [0.6, 0.6, 0.6], 1);
        } catch (e) {}

        var btns = w.add("group");
        btns.alignment = "right";
        btns.add("button", undefined, "Cancel", { name: "cancel" });
        var ok = btns.add("button", undefined, "Analyze & place", { name: "ok" });

        var result = null;
        ok.onClick = function () {
            var methodMap = ["tcn", "librosa", "beat_this"];
            result = {
                audio: audioField.text,
                method: methodMap[method.selection.index],
                beats: cbBeats.value,
                downbeats: cbDown.value,
                onsets: cbOnset.value,
                offset: parseFloat(offField.text) || 0
            };
            w.close(1);
        };
        w.show();
        return result;
    }

    // ----- main -------------------------------------------------------------
    var comp = ensureActiveComp();
    if (!comp) return;

    var analyzerDir = findAnalyzerDir();
    if (!analyzerDir) {
        alert("Could not locate the 'analyzer' folder next to this script.\n" +
              "Keep BeatSync.jsx inside extension/jsx/ in the repo.", DIALOG_TITLE);
        return;
    }
    var python = resolvePython();
    var hasCheckpoint = new File(analyzerDir + "/checkpoints/best.pt").exists;

    var opts = showDialog(selectedAudioPath(comp), hasCheckpoint);
    if (!opts) return;
    if (!opts.audio) { alert("Pick an audio file first.", DIALOG_TITLE); return; }
    if (!opts.beats && !opts.downbeats && !opts.onsets) {
        alert("Select at least one marker type.", DIALOG_TITLE); return;
    }
    if (opts.method === "tcn" && !hasCheckpoint) {
        alert("No trained model found at analyzer/checkpoints/best.pt.\n" +
              "Pick 'librosa' instead, or train a model first.", DIALOG_TITLE);
        return;
    }

    var layer = pickTargetLayer(comp);
    if (!layer) { alert("Select the layer to receive markers.", DIALOG_TITLE); return; }

    var outPath = Folder.temp.fsName + "/beatsync_out.json";
    var run = runAnalyzer(analyzerDir, python, opts.audio, opts.method, outPath);
    if (!run.ok) {
        alert("Analysis failed.\n\nCommand output:\n" + run.log.substring(0, 1500), DIALOG_TITLE);
        return;
    }

    var payload;
    try {
        payload = readJSON(run.out);
    } catch (e) {
        alert("Analyzer ran but output was unreadable:\n" + e.message, DIALOG_TITLE);
        return;
    }

    app.beginUndoGroup("BeatSync: analyze & place markers");
    var total = 0;
    try {
        if (opts.downbeats) total += placeMarkers(layer, payload.downbeats, "downbeat", opts.offset);
        if (opts.beats)     total += placeMarkers(layer, payload.beats,     "beat",     opts.offset);
        if (opts.onsets)    total += placeMarkers(layer, payload.onsets,    "onset",    opts.offset);
    } catch (e) {
        app.endUndoGroup();
        alert("Failed while placing markers:\n" + e.message, DIALOG_TITLE);
        return;
    }
    app.endUndoGroup();

    alert("Placed " + total + " markers on '" + layer.name + "'.\n" +
          "Tempo ≈ " + (payload.tempo ? payload.tempo.toFixed(1) : "?") + " BPM   " +
          "(" + opts.method + ")", DIALOG_TITLE);
})();
