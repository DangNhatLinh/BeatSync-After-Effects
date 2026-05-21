// BeatSync.jsx — standalone After Effects script.
//
// Workflow:
//   1. Generate a beats.json from the Python analyzer:
//        python -m beatsync.cli infer --audio song.wav --out beats.json
//   2. In AE: select the layer you want markers on (typically the audio layer),
//      then File > Scripts > Run Script File... and pick THIS file.
//   3. Pick the beats.json when prompted. Markers appear instantly.
//
// Tested on AE 2024 / 2025. Compatible back to AE CC 2018 (JSON support).

#target aftereffects

(function BeatSync() {
    var DIALOG_TITLE = "BeatSync";

    function readJSON(path) {
        var f = new File(path);
        if (!f.exists) throw new Error("File does not exist: " + path);
        f.encoding = "UTF-8";
        f.open("r");
        var text = f.read();
        f.close();
        // AE CC 2018+ ships modern ExtendScript with native JSON.
        return JSON.parse(text);
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

        // Fallback: first audio layer in the comp.
        for (var i = 1; i <= comp.numLayers; i++) {
            var L = comp.layer(i);
            if (L.hasAudio) return L;
        }
        alert("Select the layer you want markers on (usually the audio layer).", DIALOG_TITLE);
        return null;
    }

    function placeMarkers(layer, times, labelPrefix, colorIndex, compDuration) {
        var markerProp = layer.property("Marker");
        var placed = 0;
        for (var i = 0; i < times.length; i++) {
            var t = times[i];
            if (t < 0 || (compDuration && t > compDuration)) continue;
            var m = new MarkerValue(labelPrefix + " " + (i + 1));
            m.duration = 0;
            try { m.label = colorIndex; } catch (e) { /* older AE versions */ }
            markerProp.setValueAtTime(t, m);
            placed++;
        }
        return placed;
    }

    function showOptionsDialog(payload) {
        var w = new Window("dialog", DIALOG_TITLE);
        w.orientation = "column";
        w.alignChildren = "fill";

        var info = w.add("statictext", undefined,
            "Source: " + payload.source.split(/[\\/]/).pop() +
            "\nMethod: " + payload.method +
            "\nTempo: " + (payload.tempo ? payload.tempo.toFixed(1) + " BPM" : "n/a") +
            "\nBeats: " + payload.beats.length +
            "    Downbeats: " + payload.downbeats.length +
            "    Onsets: " + payload.onsets.length,
            { multiline: true });
        info.preferredSize.height = 80;

        var grp = w.add("panel", undefined, "Place markers for:");
        grp.orientation = "column";
        grp.alignChildren = "left";
        var cbBeats     = grp.add("checkbox", undefined, "Beats");          cbBeats.value = true;
        var cbDownbeats = grp.add("checkbox", undefined, "Downbeats");      cbDownbeats.value = false;
        var cbOnsets    = grp.add("checkbox", undefined, "Onsets");         cbOnsets.value = false;

        var offsetGrp = w.add("group");
        offsetGrp.add("statictext", undefined, "Time offset (sec):");
        var offsetField = offsetGrp.add("edittext", undefined, "0.0");
        offsetField.characters = 8;

        var btns = w.add("group");
        btns.alignment = "right";
        var cancel = btns.add("button", undefined, "Cancel", { name: "cancel" });
        var ok     = btns.add("button", undefined, "Place markers", { name: "ok" });

        var result = null;
        ok.onClick = function () {
            result = {
                beats: cbBeats.value,
                downbeats: cbDownbeats.value,
                onsets: cbOnsets.value,
                offset: parseFloat(offsetField.text) || 0
            };
            w.close(1);
        };
        cancel.onClick = function () { w.close(0); };

        w.show();
        return result;
    }

    function applyOffset(times, offset) {
        if (!offset) return times;
        var out = [];
        for (var i = 0; i < times.length; i++) out.push(times[i] + offset);
        return out;
    }

    // ---- main ----
    var comp = ensureActiveComp();
    if (!comp) return;

    var jsonFile = File.openDialog("Select beats.json from the BeatSync analyzer", "*.json");
    if (!jsonFile) return;

    var payload;
    try {
        payload = readJSON(jsonFile.fsName);
    } catch (e) {
        alert("Could not read beats.json:\n" + e.message, DIALOG_TITLE);
        return;
    }

    if (typeof payload.schema_version !== "number") {
        alert("That file doesn't look like a BeatSync beats.json.", DIALOG_TITLE);
        return;
    }

    var opts = showOptionsDialog(payload);
    if (!opts) return;
    if (!opts.beats && !opts.downbeats && !opts.onsets) {
        alert("Nothing selected to place.", DIALOG_TITLE); return;
    }

    var layer = pickTargetLayer(comp);
    if (!layer) return;

    app.beginUndoGroup("BeatSync: place markers");
    var total = 0;
    try {
        if (opts.downbeats) {
            total += placeMarkers(layer, applyOffset(payload.downbeats, opts.offset), "downbeat", 11, comp.duration);
        }
        if (opts.beats) {
            total += placeMarkers(layer, applyOffset(payload.beats, opts.offset), "beat", 9, comp.duration);
        }
        if (opts.onsets) {
            total += placeMarkers(layer, applyOffset(payload.onsets, opts.offset), "onset", 5, comp.duration);
        }
    } catch (e) {
        app.endUndoGroup();
        alert("Failed while placing markers:\n" + e.message, DIALOG_TITLE);
        return;
    }
    app.endUndoGroup();

    alert("Placed " + total + " markers on '" + layer.name + "'.", DIALOG_TITLE);
})();
