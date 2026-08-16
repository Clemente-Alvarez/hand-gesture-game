# hand-gesture-game
A small game that uses gestures to move and scale a piece of an image to fit on a hole. It uses mediapipe hands to detect your hands and SDL3 to display de images and piece you need to move.

# How to run

make sure to create a Python virtual enviroment following *requirements.txt*

if you don't have it installed first:
```bash
    pip install virtualenv
```

then create the virtual enviroment form the *repository directory*

```bash
    virtualenv venv
```

then enter the virtual enviroment:

Linux:
```bash
    source venv/bin/activate
```

Windows:
```
    venv/bin/activate
```

then install the requirements on the enviroment

```bash
    pip install -r requirements.txt
```

then execute the python script with:

```bash
    python main.py
```
or

```bash
    python3 main.py
```