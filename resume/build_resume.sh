python3 build_and_compile.py
latexmk -pdf -interaction=nonstopmode -halt-on-error -jobname=output/generated_resume main.tex
python3 cv_sync_google.py