# Developer Notes

Short developer notes to get started

## Setting up

### Devloping on the Raspberry Pi

First create a python virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then build the webapp (see `naturewatch_camera_server/static/client/README.md`
for more information)

```bash
./build_node_app.sh
```

You can run the application with

```bash
python -m naturewatch_camera_server -p 8080
```

### Developing on an x86

The server and frontend can run on an x86 development machine with
the camera and GPIO code stubbed out.

## Getting Started x86

If you want to work on an x86 machine instead of the Raspberry Pi, first configure a
vitual environment and install x86 requirements. From the root of the repository run

```bash
python -m venv venv
source venv/bin/activate
pip install -r x86-requirements.txt
```

Then as above build the web app.

```bash
./build_node_app.sh
```

You can then launch the server with

```bash
python -m naturewatch_camera_server -p 8080
```
