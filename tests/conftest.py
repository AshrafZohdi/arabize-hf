import os

# Tests never load the full term bank from the Hub: the app keeps our own glossary.
os.environ.setdefault("DARBY_TERMBANK", "off")
