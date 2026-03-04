# VHS demo recording for uitag README
#
# Setup (run once before recording):
#   1. Stage screenshots from the benchmarking directory:
#        mkdir -p /tmp/uitag-demo/screenshots
#        cp docs/screenshots-benchmarking/png/compressed/screenshot-1-vscode-filetree-script-settings-1920x1080-comp.png \
#           /tmp/uitag-demo/screenshot.png
#        cp docs/screenshots-benchmarking/png/compressed/screenshot-1-vscode-filetree-script-settings-1920x1080-comp.png \
#           /tmp/uitag-demo/screenshots/vscode.png
#        cp docs/screenshots-benchmarking/png/compressed/screenshot-2-lmstudio-local-server-1920x1080-comp.png \
#           /tmp/uitag-demo/screenshots/lmstudio.png
#        cp docs/screenshots-benchmarking/png/compressed/screenshot-3-gmail-iterm-system-settings-1920x1080-comp.png \
#           /tmp/uitag-demo/screenshots/desktop.png
#   2. Ensure Florence-2 model is downloaded (run uitag once first)
#
# Record:
#   vhs docs/assets/demo.tape

Output docs/assets/demo.gif

Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20

# Move to staging directory
Hide
Type "cd /tmp/uitag-demo"
Enter
Sleep 500ms
Show

# Scene 1: Tag a single screenshot (VS Code, dark mode)
Type "uitag screenshot.png -o out/"
Sleep 500ms
Enter

# Wait for pipeline to complete (~3-4s)
Sleep 5s

# Pause so viewer can read the results
Sleep 3s

# Scene 2: Batch process all three 1080p screenshots
Type "uitag batch screenshots/ -o out/"
Sleep 500ms
Enter

# Wait for batch processing (~8-10s for 3 images)
Sleep 12s

# Pause so viewer can read the summary
Sleep 4s
