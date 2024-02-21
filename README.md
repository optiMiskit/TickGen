# TickGen - A (wip) RHRE to Tickflow converter

Please note that this early on, the code relies on some setup specific to my workflow.
I will work on making the code use more general workflows/conventions.

## Things to improve right now
* Currently, rests use integers (eww)
* Subtitles are exclusively used for game switching.
* Cues are simply replaced with metronome ticks, work need to be done to built a database of game tickflow subs

## Help
* To game swap, put a subtitle VFX in rhre3 with the name of the game you are switching to
* You'll need: 
  - A sub named "defaultGameSetup" and "swapEngine" to do those things
  - Variables "quarter" and "half"
  - Variables for engine IDs in the naming convention "engID_gamename"
  - (optional): sub named metronome
