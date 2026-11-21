ITOps Command v1.9.1

=== RUN WITHOUT BLACK CMD ===

Option A (recommended while developing):
  Double-click:  run_gui.vbs
  Or:            run_gui.bat

Option B:
  pythonw gui.py

Do NOT use plain:  python gui.py
(that always opens a console because python.exe is a console app)

=== INSTALL ===
  pip install -r requirements.txt

=== BUILD EXE (no console) ===
  build_exe.bat
  -> dist\ITOps-Assistant.exe  (--windowed --noconsole)

All ipconfig/ping/powershell calls use CREATE_NO_WINDOW via modules\win_silent.py
