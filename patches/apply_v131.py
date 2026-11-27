import pathlib, re, sys

root = pathlib.Path(sys.argv[1])
files = list(root.rglob("MainActivity.kt"))
if not files:
    raise SystemExit("MainActivity.kt not found in extracted archive")
p = files[0]
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly one matching source block, found {n}")
    s = s.replace(old, new, 1)
    print("Applied:", label)

once(
    '    val customReminders: List<CustomAutoReminder> = emptyList()\n',
    '    val customReminders: List<CustomAutoReminder> = emptyList(),\n    val gameBestScore: Int = 0\n',
    "persist best score in state"
)
once(
    '                customReminders = customReminders\n',
    '                customReminders = customReminders,\n                gameBestScore = obj.optInt("gameBestScore", 0).coerceAtLeast(0)\n',
    "load saved best score"
)
once(
    '            put("customReminders", remindersArr)\n',
    '            put("customReminders", remindersArr)\n            put("gameBestScore", state.gameBestScore.coerceAtLeast(0))\n',
    "save best score"
)
once(
    '            StarCatcherMiniGameDialog(\n',
    '            StarCatcherMiniGameDialog(\n                savedBestScore = state.gameBestScore,\n                onSaveBestScore = { newBest ->\n                    if (newBest > state.gameBestScore) {\n                        updateAndSave { it.copy(gameBestScore = newBest) }\n                    }\n                },\n',
    "pass score persistence callback"
)
once(
    '                    while (i < s.length && s[i].isLetter()) i++\n',
    '                    while (i < s.length && s[i].isLetter()) i++\n                    // Поддержка имён функций с цифрами (log10, log2), если следом идёт \'(\'\n                    val digitStart = i\n                    while (i < s.length && s[i].isDigit()) i++\n                    if (i > digitStart && (i >= s.length || s[i] != \'(\')) {\n                        i = digitStart\n                    }\n',
    "recognize log2 and log10 tokens"
)
once(
    'private fun StarCatcherMiniGameDialog(\n    smoothAnimations: Boolean,\n',
    'private fun StarCatcherMiniGameDialog(\n    savedBestScore: Int,\n    onSaveBestScore: (Int) -> Unit,\n    smoothAnimations: Boolean,\n',
    "add game dialog parameters"
)
once(
    '    var playerX by remember { mutableFloatStateOf(0.5f) } // 0.1..0.9\n    var moveDir by remember { mutableIntStateOf(0) } // -1 влево, 0 стоп, +1 вправо\n    var score by remember { mutableIntStateOf(0) }\n    var bestScore by remember { mutableIntStateOf(0) }\n',
    '    var playerX by remember { mutableFloatStateOf(0.5f) } // 0.1..0.9\n    var score by remember { mutableIntStateOf(0) }\n    var bestScore by remember(savedBestScore) { mutableIntStateOf(max(savedBestScore, 0)) }\n',
    "initialize persisted game best score"
)
once(
    '        playerX = 0.5f\n        moveDir = 0\n        score = 0\n',
    '        playerX = 0.5f\n        score = 0\n',
    "reset game without moveDir"
)
once(
    '            if (moveDir != 0) {\n                playerX = (playerX + moveDir * dt * 0.85f).coerceIn(0.10f, 0.90f)\n            }\n\n',
    '',
    "remove old continuous directional movement"
)
once(
    '                if (score > bestScore) bestScore = score\n',
    '                if (score > bestScore) {\n                    bestScore = score\n                    onSaveBestScore(score)\n                }\n',
    "save new record immediately"
)

# Replace the old two-button movement row with a direct position slider.
start = s.find('        Row(\n', s.find('text = "◄ Влево"') - 2500)
if start < 0:
    start = s.rfind('        Row(\n', 0, s.find('text = "◄ Влево"'))
end_anchor = '                text = "Вправо ►"'
right = s.find(end_anchor)
if start < 0 or right < 0:
    raise SystemExit("Could not locate old left/right controls")
# Find the Row's matching closing brace by tracking braces from the opening Row.
i = start
depth = 0
in_string = False
escaped = False
found_end = None
while i < len(s):
    c = s[i]
    if in_string:
        if escaped:
            escaped = False
        elif c == "\\\\":
            escaped = True
        elif c == '"':
            in_string = False
    else:
        if c == '"':
            in_string = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                found_end = i + 1
                break
    i += 1
if found_end is None or start > right or found_end <= right:
    raise SystemExit("Could not find matching end of movement Row")
slider = '''        // Управление корабликом перетаскиванием ползунка
        Slider(
            value = playerX,
            onValueChange = { newX ->
                if (!gameOver) {
                    playerX = newX.coerceIn(0.10f, 0.90f)
                }
            },
            valueRange = 0.10f..0.90f,
            modifier = Modifier.fillMaxWidth()
        )'''
s = s[:start] + slider + s[found_end:]
p.write_text(s, encoding="utf-8")
print("Applied: replace left/right buttons with slider")
print("Patched:", p)
