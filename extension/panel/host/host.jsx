// BeatSync host-side ExtendScript — runs in AE's JS engine, called from the panel.

var BeatSync = (function () {

    function readJSON(path) {
        var f = new File(path);
        if (!f.exists) throw new Error("File does not exist: " + path);
        f.encoding = "UTF-8";
        f.open("r");
        var text = f.read();
        f.close();
        return JSON.parse(text);
    }

    function getSelectedAudioPath() {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) return null;
        if (comp.selectedLayers.length === 0) return null;

        var L = comp.selectedLayers[0];
        if (!(L.source && L.source.file)) return null;
        return L.source.file.fsName;
    }

    function pickTargetLayer(comp) {
        if (comp.selectedLayers.length > 0) return comp.selectedLayers[0];
        for (var i = 1; i <= comp.numLayers; i++) {
            if (comp.layer(i).hasAudio) return comp.layer(i);
        }
        return null;
    }

    function placeOne(layer, times, prefix, colorIndex, offset, compDur) {
        var markerProp = layer.property("Marker");
        var placed = 0;
        for (var i = 0; i < times.length; i++) {
            var t = times[i] + (offset || 0);
            if (t < 0 || (compDur && t > compDur)) continue;
            var m = new MarkerValue(prefix + " " + (i + 1));
            m.duration = 0;
            try { m.label = colorIndex; } catch (e) {}
            markerProp.setValueAtTime(t, m);
            placed++;
        }
        return placed;
    }

    function placeMarkersFromJson(jsonPath, opts) {
        try {
            var comp = app.project.activeItem;
            if (!comp || !(comp instanceof CompItem)) return "ERR: open a comp first";

            var layer = pickTargetLayer(comp);
            if (!layer) return "ERR: select a layer (or have an audio layer in the comp)";

            var data = readJSON(jsonPath);
            if (typeof data.schema_version !== "number") return "ERR: not a BeatSync beats.json";

            app.beginUndoGroup("BeatSync: place markers");
            var total = 0;
            if (opts.downbeats) total += placeOne(layer, data.downbeats, "downbeat", 11, opts.offset, comp.duration);
            if (opts.beats)     total += placeOne(layer, data.beats,     "beat",      9, opts.offset, comp.duration);
            if (opts.onsets)    total += placeOne(layer, data.onsets,    "onset",     5, opts.offset, comp.duration);
            app.endUndoGroup();

            return "Placed " + total + " markers on '" + layer.name + "' (tempo " + (data.tempo || 0).toFixed(1) + " BPM)";
        } catch (e) {
            return "ERR: " + e.message;
        }
    }

    return {
        getSelectedAudioPath: getSelectedAudioPath,
        placeMarkersFromJson: placeMarkersFromJson
    };
})();
