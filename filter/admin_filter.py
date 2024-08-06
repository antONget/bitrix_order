from config_data.config import load_config, Config
import database.requests as rq
import logging

config: Config = load_config()


def check_super_admin(telegram_id: int) -> bool:
    """
    Проверка на администратора
    :param telegram_id: id пользователя телеграм
    :return: true если пользователь администратор, false в противном случае
    """
    logging.info('cheсk_manager')
    list_super_admin = config.tg_bot.admin_ids.split(',')
    return str(telegram_id) in list_super_admin


async def check_personal(tg_id: int, role: str = 'personal') -> bool:
    """
    Проверка роли пользователя
    :param tg_id:
    :param role:
    :return:
    """
    logging.info(f'check_personal: tg_id: {tg_id}, role: {role}')
    info_user = await rq.get_user_tg_id(tg_id=tg_id)
    if role == "personal":
        if info_user.role not in [rq.UserRole.user]:
            return True
        else:
            return False
    else:
        if info_user.role == role or info_user.role == rq.UserRole.admin:
            return True
        else:
            return False

