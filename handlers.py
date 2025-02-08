from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton,FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form,FoodLog
from config import API_KEY
import matplotlib.pyplot as plt
import os
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

user={}
user_today={}
router = Router()

def reset_dictionary():
    global user_today
    for user_id in user_today.keys():
        user_today[user_id]["calories_today"] = [0]
        user_today[user_id]["water_today"] = [0]
        user_today[user_id]["burned_today"] = [0]
        user_today[user_id]["water_goal"] = user[user_id]["water_goal"]

    print("Словарь сброшен")

scheduler = AsyncIOScheduler()
scheduler.add_job(reset_dictionary, CronTrigger(hour=0, minute=0))


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:  # Проверяем, есть ли найденные продукты
            first_product = products[0]
            return first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
        return None
    print(f"Ошибка: {response.status_code}")
    return None

def curr_temp(city):
    response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric")
    if response.status_code == 200:
        answer = response.json()
        return answer['main']['temp']
    else:
        raise Exception(f"Не удалось получить данные для города {city}. Код ответа - {response.status_code}")


def get_calories(usr):
    cn = usr["weight"] * 10 + usr["height"] * 6.25 - usr["age"] * 5 + usr["activity"]
    usr["calorie_goal"] = cn
    return cn

def get_water(usr, tmp):
    wn = usr["weight"] * 30 +  (usr["activity"] // 30) * 500 - (tmp > 25) * 500
    usr["water_goal"] = wn
    return wn

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать! Я ваш бот для подсчета калорий.\nВведите /help для списка команд.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля\n"
        "/log_water - Логирование воды\n"
        "/log_food - Логирование еды\n"
        "/log_workout - Логирование тренировок\n"
        "/check_progress - Прогресс по воде и калориям\n"
        "/check_progress_graph - Прогресс по воде и калориям в виде графика\n"
    )
@router.message(Command("set_profile"))
async def start_set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг)")
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.reply("Введите ваш рост (в см)")
    await state.set_state(Form.height)

@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.reply("Введите ваш возраст")
    await state.set_state(Form.age)

@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)

@router.message(Form.activity)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await message.reply("В каком городе вы находитесь?")
    await state.set_state(Form.city)


@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    data = await state.get_data()

    user_id = str(message.from_user.id)
    if user_id not in user.keys():
        user[user_id] = {}
        user_today[user_id] = {}

    user[user_id]["weight"] = int(data.get("weight"))
    user[user_id]["height"] = int(data.get("height"))
    user[user_id]["age"] = int(data.get("age"))
    user[user_id]["activity"] = int(data.get("activity"))
    user[user_id]["city"] = message.text

    try:
        temp_city =  curr_temp(user[user_id]["city"])
    except:
        await message.reply("Не удалось получить информацию о температуре. Пожалуйста, введите корректное название города.")
        return

    calories_norm = get_calories(user[user_id])
    water_norm = get_water(user[user_id], temp_city)

    user_today[user_id]["calories_today"]=[0]
    user_today[user_id]["water_today"]=[0]
    user_today[user_id]["burned_today"] = [0]
    user_today[user_id]["water_goal"] = user[user_id]["water_goal"]


    # print('user_today: ', user_today)
    await message.reply(f"Ваша дневная норма калорий: {calories_norm} ккал\nВаша дневная норма воды: {water_norm} мл")
    await state.clear()


@router.message(Command("log_water"))
async def log_water(message: Message):
    args = message.text.split()

    if len(args) < 2:
        await message.reply("Вызов логирования воды: /log_water <количество>")
        return
    user_id = str(message.from_user.id)
    if user_id not in user.keys():
        await message.reply("Ваша дневная норма воды неизвестна, выполните команду /set_profile")
        return

    water = int(args[1])

    user_today[user_id]["water_today"].append(water)
    # print('user_today: ', user_today)
    await message.reply(f"Вы выпили {water} мл воды.\nДо нормы осталось {user_today[user_id]['water_goal'] - sum(user_today[user_id]['water_today'])} мл.")



@router.message(Command("log_workout"))
async def log_workout(message: Message):
    args = message.text.split()

    if len(args) < 3:
        await message.reply("Вызов логирования тренировок: /log_workout <тип тренировки> <время (мин)>")
        return

    user_id = str(message.from_user.id)
    if user_id not in user.keys():
        await message.reply("Ваша дневная норма калорий неизвестна, выполните команду /set_profile")
        return

    time = int(args[2])
    type_of_train = args[1]
    burned_calories = time * 15
    need_water = time*10

    user_today[user_id]['water_goal'] += need_water

    user_today[user_id]["burned_today"].append(burned_calories)
    # print('user_today: ', user_today)
    await message.reply(f"{type_of_train} {time} минут - {burned_calories} ккал сожжено.\n Дополнительно: выпейте {need_water} мл воды")



@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in user.keys():
        await message.reply("Ваша дневная норма воды и калорий неизвестна, выполните команду /set_profile")
        return

    water_goal = user_today[user_id]['water_goal']
    drinked_water=sum(user_today[user_id]['water_today'])
    calories_goal = user[user_id]['calorie_goal']
    calories_eaten = sum(user_today[user_id]['calories_today'])
    calories_burned = sum(user_today[user_id]['burned_today'])
    await message.answer(
        "ПРОГРЕСС:\n"
        "Вода:\n"
        f"Выпито: {drinked_water} мл из {water_goal} мл.\n"
        f"Осталось: {water_goal-drinked_water}\n"
        "\nКалории\n"
        f"Потреблено: {calories_eaten} ккал из {calories_goal} ккал.\n"
        f"Сожжено: {calories_burned} ккал. \n"
        f"Осталось: {calories_burned + calories_goal -  calories_eaten} ккал. \n"
    )

@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    args = message.text.split()

    if len(args) < 2:
        await message.answer("Вызов логирования еды: /log_food <название продукта>")
        return
    user_id = str(message.from_user.id)
    if user_id not in user.keys():
        await message.reply("Ваша дневная норма калорий неизвестна, выполните команду /set_profile")
        return
    product_name = args[1]
    calories = get_food_info(product_name)

    if calories is None:
        await message.answer(f"Не удалось найти информацию о продукте '{product_name}'. Попробуйте другой запрос.")
        return

    await state.update_data(calories=calories)
    await state.set_state(FoodLog.calories)
    await message.answer(f"{product_name} — {calories} ккал на 100 г. Сколько граммов вы съели?")

@router.message(FoodLog.calories)
async def process_grams(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число граммов.")
        return

    grams = int(message.text)
    data = await state.get_data()


    calories_per_100g = data["calories"]
    total_calories = (calories_per_100g * grams) / 100
    user_id = str(message.from_user.id)
    user_today[user_id]["calories_today"].append(total_calories)
    await message.reply(f"Записано: {total_calories} ккал.")
    await state.clear()



@router.message(Command("check_progress_graph"))
async def check_progress_graph(message: Message):

    user_id = str(message.from_user.id)

    if user_id not in user:
        await message.answer("Нет данных для построения графика. Начните логировать воду и еду.")
        return

    water_values = user_today[user_id]["water_today"]
    calorie_values = user_today[user_id]["calories_today"]

    water_idx = [index for index, value in enumerate(water_values)]
    cal_idx = [index for index, value in enumerate(calorie_values)]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    ax1.set_xlabel("Порядок логирования")
    ax1.set_ylabel("Вода (мл)", color="blue")
    ax1.plot(water_idx, water_values, marker="o", linestyle="-", color="blue", label="Вода")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax2 = ax1.twinx()
    ax2.set_ylabel("Калории (ккал)", color="red")
    ax2.plot(cal_idx, calorie_values, marker="s", linestyle="--", color="red", label="Калории")
    ax2.tick_params(axis="y", labelcolor="red")

    fig.autofmt_xdate()
    plt.title("Прогресс по воде и калориям")

    image_path = os.path.join('imgs', 'plot.png')
    plt.savefig(image_path)
    plt.close()

    photo = FSInputFile(image_path)
    await message.answer_photo(photo, caption="Ваш прогресс по воде и калориям ")