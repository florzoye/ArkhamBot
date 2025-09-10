from loguru import logger
import aiohttp
import asyncio

from data import config

class TwoCaptcha:
    def __init__(self, session: aiohttp.ClientSession, api_key: str | None = None):
        self.api_key = api_key 
        self.session = session

    async def captcha_data(self, action: str | None = None, task_id: str | None = None):
        if action == "CREATE":
            return {
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": config.SITE_KEY,
                "pageurl": config.PAGE_URL,
                "json": 1,
            }
        else:
            return {
                "key": self.api_key,
                "action": "get",
                "id": task_id,
                "json": 1,
            }

    async def create_task(self):
        data = await self.captcha_data(action="CREATE")
        async with self.session.post(config.CREATE_URL, data=data) as resp:
            answer = await resp.json()
            logger.info(f"Ответ при создании задачи: {answer}")
            if answer.get("status") == 1:
                return answer["request"]  
            return None

    async def check_complete_task(self, task_id: str):
        params = await self.captcha_data(task_id=task_id)
        for attempt in range(config.NUMBER_ATTEMPTS_REQUESTS):
            async with self.session.get(config.RES_URL, params=params) as resp:
                answer = await resp.json()
                if answer.get("status") == 1:
                    logger.success("Капча решена!")
                    return answer["request"]  #
                if answer.get("request") == "CAPCHA_NOT_READY":
                    logger.info(f"Попытка {attempt+1}: капча ещё не готова, ждём...")
                    await asyncio.sleep(5)
                    continue
                logger.warning(f"Ошибка при решении капчи: {answer}")
                return None
        logger.error("Превышено количество попыток проверки капчи")
        return None

    async def solve_turnstile(self):
        task_id = await self.create_task()
        if not task_id:
            logger.error("Не удалось создать задачу")
            return None
        logger.info(f"Задача создана: {task_id}, ждём решения...")
        token = await self.check_complete_task(task_id)
        return token
    



