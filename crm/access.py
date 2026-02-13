AUTOSALON_BLOCKED_GROUP = 'Автосалон: доступ запрещен'
AUTOSALON_HIDE_ATTORNEY_GROUP = 'Автосалон: скрыть вкладку доверенности'


def get_autosalon_access_flags(user):
    if not user.is_authenticated:
        return {'can_access_autosalon': False, 'can_view_attorney_tab': False}

    if user.is_superuser:
        return {'can_access_autosalon': True, 'can_view_attorney_tab': True}

    groups_qs = user.groups.values_list('name', flat=True)
    group_names = set(groups_qs)
    can_access_autosalon = AUTOSALON_BLOCKED_GROUP not in group_names
    can_view_attorney_tab = AUTOSALON_HIDE_ATTORNEY_GROUP not in group_names
    return {
        'can_access_autosalon': can_access_autosalon,
        'can_view_attorney_tab': can_view_attorney_tab,
    }
