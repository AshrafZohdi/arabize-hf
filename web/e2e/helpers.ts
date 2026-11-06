import { execSync } from 'node:child_process'

// Today's English answer, read from the server's own game code, so the win dialog can be captured.
export const todaysWord = () =>
  execSync(
    `.venv/bin/python -c "from pathlib import Path; from server.glossary import load_glossary; from server.game import Game, qatar_today; print(Game(load_glossary(Path('content')), Path('content'), b'x').puzzle('en', qatar_today()).word)"`,
    { cwd: '..' },
  )
    .toString()
    .trim()
