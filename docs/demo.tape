# VHS tape: regenerate with `vhs docs/demo.tape` from the repo root.
# Outputs docs/demo.gif (~35s).
# Uses absolute paths because VHS spawns its own shell without the project venv active.

Output docs/demo.gif

Env PATH "/Users/nathan/Desktop/CLOAK/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
Env PS1 "$ "

Set Shell "bash"
Set FontSize 16
Set Width 1180
Set Height 680
Set Theme "Catppuccin Mocha"
Set TypingSpeed 40ms
Set PlaybackSpeed 1.0

# Set up a clean working copy of the example so the demo is deterministic.
Hide
Type "rm -rf /tmp/cloak-demo && cp -R /Users/nathan/Desktop/CLOAK/examples/python-pricing-engine /tmp/cloak-demo && cd /tmp/cloak-demo && export PS1='$ ' && clear"
Enter
Sleep 800ms
Show

Type "# CLOAK — local CLI for safer LLM workflows"
Sleep 800ms
Enter
Type "# 1. Find secrets before they leave your laptop."
Sleep 600ms
Enter
Type "cloak scan ."
Sleep 300ms
Enter
Sleep 2200ms

Type "clear"
Enter
Sleep 200ms

Type "# 2. About to ask Claude or ChatGPT? Preview what gets redacted first."
Sleep 800ms
Enter
Type "cloak diff-context ."
Sleep 300ms
Enter
Sleep 3500ms

Type "clear"
Enter
Sleep 200ms

Type "# 3. Generate the redacted view and copy to clipboard."
Sleep 800ms
Enter
Type "cloak context pricing.py --out safe.md && head -20 safe.md"
Sleep 300ms
Enter
Sleep 3500ms

Type "clear"
Enter
Sleep 200ms

Type "# 4. Sharing with a contractor? Obfuscate AND verify against your tests."
Sleep 800ms
Enter
Type "cloak obfuscate . --out /tmp/cloaked --verify 'pytest -q'"
Sleep 300ms
Enter
Sleep 5000ms

Type "# Tests passed against the renamed copy. The transform is safe to ship."
Sleep 1500ms
Enter

Type "# pip install cloak-cli"
Sleep 2500ms
