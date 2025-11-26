# QUICK START - Just Run It!

## The Absolute Simplest Way (No Install Needed!)

```bash
# 1. Make sure you have dependencies
pip install PyQt5 numpy matplotlib scipy h5py

# 2. Run it!
python run.py
```

That's it! The app should open.

---

## If You Want to Install Properly

```bash
# Install dependencies
pip install PyQt5 numpy matplotlib scipy h5py

# Install arpest in editable mode (optional)
pip install -e .

# Run it
python run.py
```

---

## Troubleshooting

### "No module named 'arpest'"
**Solution:** Use `python run.py` instead of `python app.py`

### "No module named PyQt5"
**Solution:** 
```bash
pip install PyQt5
```

### "ERROR: File setup.py not found"
**Solution:** I've added setup.py now. Try again with:
```bash
pip install -e .
```

Or just skip the install and use `python run.py` directly!

---

## What run.py Does

The `run.py` script:
1. Automatically adds the project to Python's path
2. Detects whether you have PyQt5 or PyQt6
3. Launches the application

You don't need to install anything if you just run `python run.py`!

---

## Next Steps After It Runs

Once you see the window open:
1. Try File → Open (it will show a file dialog)
2. Start implementing visualization (see START_HERE.md)
