from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn
import random
import string
from typing import List
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="web/templates")

statuses = ["Ошибка", "Активен", "Пауза", "Окончен", "Настройка"]

class Instrument(BaseModel):
    name: str

class Parameter(BaseModel):
    name: str

class ExperimentState(BaseModel):
    status: str
    time_left: int 
    image_url: str


experiment_state = ExperimentState(status=random.choice(statuses), time_left=600, image_url="path/to/image.jpg")


def random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_instruments() -> List[Instrument]:
    count = random.randint(1, 5)
    return [Instrument(name=random_string(5)) for _ in range(count)]

def generate_random_parameters() -> List[Parameter]:
    count = random.randint(1, 5)
    return [Parameter(name=random_string(7)) for _ in range(count)]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("test1.html", {"request": request})

@app.get("/instruments/")
async def get_instruments():
    return generate_random_instruments()

@app.get("/parameters/")
async def get_parameters():
    return generate_random_parameters()

@app.get("/experiment_state/")
async def get_experiment_state():
    global experiment_state
    return experiment_state

@app.post("/experiment/start/")
async def start_experiment():
    global experiment_state
    experiment_state.status = "Активен"
    experiment_state.time_left = 600
    return experiment_state

@app.post("/experiment/pause/")
async def pause_experiment():
    global experiment_state
    experiment_state.status = "Пауза"
    return experiment_state

@app.post("/experiment/stop/")
async def stop_experiment():
    global experiment_state
    experiment_state.status = "Окончен"
    return experiment_state

@app.post("/experiment/error/")
async def set_error():
    global experiment_state
    experiment_state.status = "Ошибка"
    return experiment_state

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)


