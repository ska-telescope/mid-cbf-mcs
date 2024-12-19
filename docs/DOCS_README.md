# Notes on Auto-Generated Documentation 

Document directory structure:
```
ska-mid-cbf-tdc-mcs/
   docs/
      build
      src/
         _static/
         _templates/
         api/
         diagrams/
         guide/
         conf.py
         index.rst
  DOCS_README.md
  Makefile
  requirements.txt
```

1. Run `make html` to generate the documentation.
1. `index.rst` references other `.rst` files in the `docs/src/` folder, which reference the Python code.
1. `autodoc_mock_imports` in `conf.py` may need to be updated when adding new imports in the Python code.
1. `MCS-diagrams.vsdx` contains diagrams in Visio format, and is the source of 
`.png` images in the `diagrams` folder.
