# VoiceSheet

Speech becomes values: a waveform while the mic is held, the transcript word by word, then each understood phrase flies down and becomes a chip.

Phases: `listening`, `transcript` (matched phrases highlighted), `mapped` (highlights become `ValueChip`s with a mic mark). "Type instead" is always there. `Waveform` is the bars alone.

**You provide:** `phase`, `transcript`, `mapped` (`[{id, phrase, label}]` from the parser), `onTypeInstead`.
