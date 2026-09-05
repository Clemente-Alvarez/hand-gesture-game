# hand-gesture-game
A small game that uses gestures to move and scale a piece of an image to fit on a hole. It uses mediapipe hands to detect your hands and SDL3 to display the images and piece you need to move.

# How to run

make sure to create a Python virtual environment following *requirements.txt*

if you don't have it installed first:
```bash
    pip install virtualenv
```

then create the virtual environment on the *repository directory*

```bash
    cd hand-gesture-game
    python -m venv .venv
```

then enter the virtual environment:

Linux:
```bash
    source .venv/bin/activate
```

Windows:
```
    .venv/Scripts/activate
```

then install the requirements on the environment

```bash
    python -m pip install --upgrade pip
    python -m  pip install -r requirements.txt
```

then execute the python script with:

```bash
    python main.py
```
or

```bash
    python3 main.py
```

# How to use

- you can grab doing a pinch gesture with *one* hand and move your hand to displace the grabbed piece

- You can do a pinch gesture with *two* hands and move them closer or apart to scale the piece