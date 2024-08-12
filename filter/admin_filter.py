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
    :param role: ['personal', 'dispatcher', 'manager']
    :return:
    """
    logging.info(f'check_personal: tg_id: {tg_id}, role: {role}')
    info_user = await rq.get_user_tg_id(tg_id=tg_id)
    # если пользователь не пользователь
    if role == "personal":
        if info_user.is_admin or info_user.is_dispatcher or info_user.is_manager:
            return True
        else:
            return False
    # если пользователь диспетчер или админ
    elif role == rq.UserRole.dispatcher:
        if info_user.is_admin or info_user.is_dispatcher:
            return True
        else:
            return False
    # если пользователь менеджер или админ
    elif role == rq.UserRole.manager:
        if info_user.is_admin or info_user.is_manager:
            return True
        else:
            return False

